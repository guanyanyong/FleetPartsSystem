"""调拨单业务逻辑：创建、确认调出、确认调入、作废与查询。

约定：
- 单号规则 `TR + yyyyMMdd + 6 位流水`，复用 `app.services.code_generator` 取号；
  并发下依赖 `uk_order_no` 唯一索引，冲突时自动重新取号重试。
- 状态流转：
  * 1 草稿 --确认调出--> 3 已调出 --确认调入--> 4 已调入；
  * 1 草稿 / 2 待审 --作废--> 5 作废（不调整库存）。
  已调出的单据必须完成调入，避免在途库存丢失；需要退回时按反向调拨处理。
- 确认调出（1/2 → 3）在一个事务内完成：按 `配件 + 调出仓库 + 库位` 加行锁并扣减
  `inventory.quantity`，写 TRANSFER_OUT 流水；逐件追踪配件同时扣减
  `inventory.item_count`，实例状态置为 2 锁定（在途），避免在途期间被扫码出库 /
  盘点重复统计。
- 确认调入（3 → 4）在一个事务内完成：按 `配件 + 调入仓库 + 库位` 加行锁（不存在
  则创建）并增加 `inventory.quantity`，按调出时记录的成本重算移动加权平均成本，
  写 TRANSFER_IN 流水；逐件追踪实例回填 `warehouse_id` / `location_id`、状态恢复
  为 1 在库，同时增加 `inventory.item_count`。
- 调拨成本取确认调出时写入 `inventory_transaction.unit_cost` 的值（逐件追踪优先
  取实例成本），保证调出 / 调入两侧金额一致。
- 单据与明细均逻辑删除；created_by / updated_by 取当前登录用户。
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.exceptions import BizException
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    SysUser,
    TransferOrder,
    TransferOrderItem,
    Warehouse,
    WarehouseLocation,
)
from app.models.enums import (
    BizType,
    CommonStatus,
    InventoryItemStatus,
    RefType,
    TransferStatus,
    UserStatus,
)
from app.schemas.common import PageResult
from app.schemas.transfer import (
    TransferOrderCreate,
    TransferOrderDetailVO,
    TransferOrderItemCreate,
    TransferOrderItemVO,
    TransferOrderQuery,
    TransferOrderVO,
)
from app.services.code_generator import (
    TRANSFER_SEQUENCE,
    SequenceExhausted,
    generate_transfer_no,
    next_sequence,
)

__all__ = [
    "cancel_transfer_order",
    "create_transfer_order",
    "get_transfer_order",
    "list_transfer_orders",
    "transfer_in",
    "transfer_out",
]

# 业务错误码（见 docs/backend-requirements.md 错误码约定）
ORDER_STATUS_NOT_ALLOWED: int = 3001
INSUFFICIENT_STOCK: int = 2001
ITEM_NOT_IN_STOCK: int = 2002
ITEM_ALREADY_OUT: int = 2003
ITEM_LOCKED: int = 2004

# 单号并发重试次数
ORDER_NO_MAX_RETRY: int = 5

# 数量保留两位小数、成本保留四位小数
QTY_QUANT: Decimal = Decimal("0.01")
COST_QUANT: Decimal = Decimal("0.0001")
ZERO_QTY: Decimal = Decimal("0.00")
ZERO_COST: Decimal = Decimal("0.0000")
ONE_QTY: Decimal = Decimal("1.00")

# 唯一索引名（用于识别可重试的并发冲突）
INVENTORY_UNIQUE_KEY: str = "uk_part_warehouse_location"

# 调出仓库 / 调入仓库的展示名称别名
FromWarehouse = aliased(Warehouse)
ToWarehouse = aliased(Warehouse)
FromLocation = aliased(WarehouseLocation)
ToLocation = aliased(WarehouseLocation)


# ---------------------------------------------------------------- 内部工具
def _qty(value: Decimal | int | None) -> Decimal:
    """数量统一保留两位小数（四舍五入），None 视为 0。"""
    if value is None:
        return ZERO_QTY
    return Decimal(value).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def _calc_avg_cost(
    before_qty: Decimal,
    before_avg: Decimal,
    in_qty: Decimal,
    in_price: Decimal,
) -> Decimal:
    """移动加权平均成本：(原数量×原均价 + 调入数量×调入成本) ÷ 调入后总数量。"""
    total_qty = before_qty + in_qty
    if total_qty <= 0:
        return ZERO_COST
    return ((before_qty * before_avg + in_qty * in_price) / total_qty).quantize(
        COST_QUANT, rounding=ROUND_HALF_UP
    )


def _ensure_item_available(item: InventoryItem) -> None:
    """校验库存件是否可调出，不可调出时抛对应业务错误码。"""
    if item.status == InventoryItemStatus.OUT:
        raise BizException(
            code=ITEM_ALREADY_OUT,
            message=f"库存件 {item.item_code} 已出库，不能调拨",
        )
    if item.status == InventoryItemStatus.LOCKED:
        raise BizException(
            code=ITEM_LOCKED,
            message=f"库存件 {item.item_code} 已被锁定或在途，不能调拨",
        )
    if item.status == InventoryItemStatus.SCRAPPED:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 已报废，不能调拨",
        )
    if item.status == InventoryItemStatus.LOST:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 已盘亏，不能调拨",
        )
    if item.status != InventoryItemStatus.IN_STOCK:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 不在库，不能调拨",
        )


async def _get_warehouse_or_404(
    db: AsyncSession,
    warehouse_id: int,
    label: str,
) -> Warehouse:
    """取启用中的仓库，不存在抛 404，已停用抛 400。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message=f"{label}仓库不存在")
    if warehouse.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"{label}仓库 {warehouse.name} 已停用")
    return warehouse


async def _ensure_user_exists(
    db: AsyncSession,
    user_id: int | None,
    label: str,
) -> None:
    """校验用户存在且启用（未指定时跳过）。"""
    if user_id is None:
        return
    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message=f"{label}不存在")
    if user.status != UserStatus.ENABLED:
        raise BizException(
            code=400,
            message=f"{label} {user.real_name or user.username} 已停用",
        )


async def _ensure_locations(
    db: AsyncSession,
    warehouse_id: int,
    location_ids: list[int | None],
    label: str,
) -> None:
    """校验库位存在且属于所选仓库（未指定库位表示仓库级）。"""
    ids = {location_id for location_id in location_ids if location_id is not None}
    if not ids:
        return

    rows = (
        (
            await db.execute(
                select(WarehouseLocation).where(
                    WarehouseLocation.id.in_(ids),
                    WarehouseLocation.is_deleted == 0,
                )
            )
        )
        .scalars()
        .all()
    )
    found = {row.id: row for row in rows}
    missing = sorted(ids - found.keys())
    if missing:
        raise BizException(code=404, message=f"{label}库位不存在: {missing[0]}")

    wrong = sorted(row.id for row in rows if row.warehouse_id != warehouse_id)
    if wrong:
        raise BizException(
            code=400,
            message=f"{label}库位 {wrong[0]} 不属于{label}仓库",
        )

    disabled = sorted(row.id for row in rows if row.status != CommonStatus.ENABLED)
    if disabled:
        location = found[disabled[0]]
        raise BizException(
            code=400,
            message=f"{label}库位 {location.location_code} 已停用",
        )


async def _load_parts(
    db: AsyncSession,
    part_ids: list[int],
    *,
    require_enabled: bool = True,
) -> dict[int, Part]:
    """批量加载配件；执行阶段允许已停用配件，避免历史单据卡住。"""
    ids = set(part_ids)
    if not ids:
        return {}

    rows = (
        (await db.execute(select(Part).where(Part.id.in_(ids), Part.is_deleted == 0)))
        .scalars()
        .all()
    )
    parts = {row.id: row for row in rows}

    missing = sorted(ids - parts.keys())
    if missing:
        raise BizException(code=404, message=f"配件不存在: {missing[0]}")

    if require_enabled:
        disabled = sorted(
            part.id for part in parts.values() if part.status != CommonStatus.ENABLED
        )
        if disabled:
            raise BizException(
                code=400,
                message=f"配件已停用: {parts[disabled[0]].part_name}",
            )
    return parts


def _normalize_quantity(
    part: Part,
    quantity: Decimal,
    *,
    inventory_item_id: int | None,
) -> Decimal:
    """校验调拨数量：逐件追踪必须绑定实例且一条明细只能一件。"""
    qty = _qty(quantity)
    if qty <= 0:
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 调拨数量必须大于 0",
        )
    if part.track_by_item == 1:
        if inventory_item_id is None:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，明细必须指定库存件",
            )
        if qty != ONE_QTY:
            raise BizException(
                code=400,
                message=(
                    f"配件 {part.part_name} 按件追踪，"
                    f"一条明细只能调拨一个库存件（数量必须为 1）"
                ),
            )
    elif inventory_item_id is not None:
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 不按件追踪，明细不能指定库存件",
        )
    return qty


async def _ensure_items_not_reserved(
    db: AsyncSession,
    item_ids: list[int],
    exclude_order_id: int | None = None,
) -> None:
    """校验库存件未被其它草稿 / 待审调拨单占用。

    数据库对 `transfer_order_item.inventory_item_id` 没有唯一约束，这里用查询兜底，
    避免同一件被两张未完成调拨单重复引用（真正扣减仍以确认调出时的行锁为准）。
    """
    if not item_ids:
        return

    stmt = (
        select(InventoryItem.item_code, TransferOrder.order_no)
        .join(
            TransferOrderItem,
            TransferOrderItem.inventory_item_id == InventoryItem.id,
        )
        .join(TransferOrder, TransferOrder.id == TransferOrderItem.order_id)
        .where(
            InventoryItem.id.in_(item_ids),
            TransferOrderItem.is_deleted == 0,
            TransferOrder.is_deleted == 0,
            TransferOrder.status.in_((TransferStatus.DRAFT, TransferStatus.PENDING)),
        )
        .limit(1)
    )
    if exclude_order_id is not None:
        stmt = stmt.where(TransferOrder.id != exclude_order_id)

    row = (await db.execute(stmt)).first()
    if row is not None:
        raise BizException(
            code=ITEM_LOCKED,
            message=f"库存件 {row[0]} 已被调拨单 {row[1]} 占用，不能重复调拨",
        )


async def _load_inventory_items(
    db: AsyncSession,
    items: Sequence[TransferOrderItem | TransferOrderItemCreate],
    warehouse_id: int,
    parts: dict[int, Part],
    *,
    exclude_order_id: int | None = None,
    for_update: bool = False,
    expected_status: int = InventoryItemStatus.IN_STOCK,
    allow_untracked_instance: bool = False,
) -> dict[int, InventoryItem]:
    """批量加载并校验明细中的库存件实例。

    校验项：实例存在、配件一致、属于调出仓库、状态符合预期、同一件不重复、
    按件追踪一条明细只能一件、未被其它未完成调拨单占用。
    `for_update=True` 时按主键升序加行锁（确认调出 / 调入使用，保证锁顺序一致）。
    """
    item_ids = [
        item.inventory_item_id for item in items if item.inventory_item_id is not None
    ]
    if not item_ids:
        return {}

    if len(set(item_ids)) != len(item_ids):
        raise BizException(code=400, message="同一库存件不能重复添加到调拨明细")

    stmt = select(InventoryItem).where(
        InventoryItem.id.in_(item_ids),
        InventoryItem.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.order_by(InventoryItem.id.asc()).with_for_update()

    rows = (await db.execute(stmt)).scalars().all()
    found = {row.id: row for row in rows}

    for item in items:
        if item.inventory_item_id is None:
            continue

        part = parts[item.part_id]
        inventory_item = found.get(item.inventory_item_id)
        if inventory_item is None:
            raise BizException(
                code=ITEM_NOT_IN_STOCK,
                message=f"库存件不存在或已删除: {item.inventory_item_id}",
            )
        if part.track_by_item != 1 and not allow_untracked_instance:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 不按件追踪，明细不能指定库存件",
            )
        if inventory_item.part_id != item.part_id:
            raise BizException(
                code=400,
                message=f"库存件 {inventory_item.item_code} 与明细配件不一致",
            )
        if inventory_item.warehouse_id != warehouse_id:
            raise BizException(
                code=400,
                message=f"库存件 {inventory_item.item_code} 不在调出仓库",
            )
        if part.track_by_item == 1 and _qty(item.quantity) != ONE_QTY:
            raise BizException(
                code=400,
                message=(
                    f"配件 {part.part_name} 按件追踪，"
                    f"一条明细只能调拨一个库存件（数量必须为 1）"
                ),
            )
        if inventory_item.status != expected_status:
            if expected_status == InventoryItemStatus.LOCKED:
                raise BizException(
                    code=409,
                    message=(
                        f"库存件 {inventory_item.item_code} 不处于调拨在途状态，"
                        f"无法确认调入"
                    ),
                )
            _ensure_item_available(inventory_item)

    if expected_status == InventoryItemStatus.IN_STOCK:
        await _ensure_items_not_reserved(db, item_ids, exclude_order_id)
    return found


async def _build_item_rows(
    db: AsyncSession,
    items: list[TransferOrderItemCreate],
    from_warehouse_id: int,
    to_warehouse_id: int,
) -> list[dict[str, Any]]:
    """把提交的明细转换为调拨明细行字段，并补齐配件与库存件主数据。"""
    if not items:
        return []

    parts = await _load_parts(db, [item.part_id for item in items])
    inventory_items = await _load_inventory_items(db, items, from_warehouse_id, parts)

    from_location_ids: list[int | None] = [item.from_location_id for item in items]
    from_location_ids.extend(
        inventory_item.location_id for inventory_item in inventory_items.values()
    )
    await _ensure_locations(db, from_warehouse_id, from_location_ids, "调出")
    await _ensure_locations(
        db,
        to_warehouse_id,
        [item.to_location_id for item in items],
        "调入",
    )

    rows: list[dict[str, Any]] = []
    # 非逐件追踪按「配件 + 调出库位」扣同一库存行，重复提交会重复扣减
    seen_locations: set[tuple[int, int | None]] = set()
    for item in items:
        part = parts[item.part_id]
        quantity = _normalize_quantity(
            part, item.quantity, inventory_item_id=item.inventory_item_id
        )

        instance = (
            inventory_items.get(item.inventory_item_id)
            if item.inventory_item_id is not None
            else None
        )
        # 指定库存件时以实例所在库位 / 批次为准
        from_location_id = (
            instance.location_id if instance is not None else item.from_location_id
        )
        if instance is None:
            key = (item.part_id, from_location_id)
            if key in seen_locations:
                raise BizException(
                    code=400,
                    message=f"配件 {part.part_name} 在同一调出库位重复提交",
                )
            seen_locations.add(key)

        rows.append(
            {
                "part_id": part.id,
                "inventory_item_id": item.inventory_item_id,
                "quantity": quantity,
                "from_location_id": from_location_id,
                "to_location_id": item.to_location_id,
                "batch_no": item.batch_no
                or (instance.batch_no if instance is not None else None),
                "remark": item.remark,
            }
        )
    return rows


# ---------------------------------------------------------------- 创建 / 查询
async def _insert_order_with_retry(
    db: AsyncSession,
    payload: TransferOrderCreate,
    rows: list[dict[str, Any]],
    operator_id: int | None,
    current_user_id: int,
) -> TransferOrder:
    """插入调拨单主表与明细；单号冲突（并发）时重新取号。"""
    for attempt in range(1, ORDER_NO_MAX_RETRY + 1):
        try:
            seq = await next_sequence(db, TRANSFER_SEQUENCE)
        except SequenceExhausted as exc:
            raise BizException(
                code=409,
                message="当日调拨单号已用尽，请联系管理员",
            ) from exc

        order = TransferOrder(
            order_no=generate_transfer_no(seq),
            from_warehouse_id=payload.from_warehouse_id,
            to_warehouse_id=payload.to_warehouse_id,
            status=TransferStatus.DRAFT,
            operator_id=operator_id,
            remark=payload.remark,
            created_by=current_user_id,
            updated_by=current_user_id,
        )
        db.add(order)
        try:
            await db.flush()
            for row in rows:
                db.add(
                    TransferOrderItem(
                        order_id=order.id,
                        created_by=current_user_id,
                        **row,
                    )
                )
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # 仅单号重复可重试，其它完整性错误直接暴露
            if "uk_order_no" not in str(exc.orig):
                raise BizException(
                    code=409,
                    message="调拨单保存失败，请检查明细后重试",
                ) from exc
            if attempt < ORDER_NO_MAX_RETRY:
                continue
            raise BizException(code=409, message="调拨单号生成冲突，请重试") from exc
        return order

    raise BizException(code=409, message="调拨单号生成冲突，请重试")


async def _get_order_or_404(
    db: AsyncSession,
    order_id: int,
    *,
    for_update: bool = False,
) -> TransferOrder:
    """取调拨单；状态流转类操作加行锁，避免并发重复调出 / 调入 / 作废。"""
    stmt = select(TransferOrder).where(
        TransferOrder.id == order_id,
        TransferOrder.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise BizException(code=404, message="调拨单不存在")
    return order


def _to_order_vo(
    order: TransferOrder,
    from_warehouse_name: str | None = None,
    to_warehouse_name: str | None = None,
) -> TransferOrderVO:
    """主表实体转 VO，并补充调出 / 调入仓库名称。"""
    vo = TransferOrderVO.model_validate(order)
    vo.from_warehouse_name = from_warehouse_name
    vo.to_warehouse_name = to_warehouse_name
    return vo


def _to_item_vo(
    item: TransferOrderItem,
    part: Part | None = None,
    inventory_item: InventoryItem | None = None,
    from_location: WarehouseLocation | None = None,
    to_location: WarehouseLocation | None = None,
) -> TransferOrderItemVO:
    """明细实体转 VO，并补充配件 / 库存件 / 库位展示字段。"""
    vo = TransferOrderItemVO.model_validate(item)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
        vo.unit = part.unit
    if inventory_item is not None:
        vo.item_code = inventory_item.item_code
    if from_location is not None:
        vo.from_location_code = from_location.location_code
    if to_location is not None:
        vo.to_location_code = to_location.location_code
    return vo


def _item_query() -> Any:
    """调拨明细查询骨架：带配件、库存件、调出 / 调入库位展示字段。"""
    return (
        select(
            TransferOrderItem,
            Part,
            InventoryItem,
            FromLocation,
            ToLocation,
        )
        .outerjoin(Part, Part.id == TransferOrderItem.part_id)
        .outerjoin(
            InventoryItem,
            InventoryItem.id == TransferOrderItem.inventory_item_id,
        )
        .outerjoin(
            FromLocation,
            FromLocation.id == TransferOrderItem.from_location_id,
        )
        .outerjoin(ToLocation, ToLocation.id == TransferOrderItem.to_location_id)
    )


async def list_transfer_orders(
    db: AsyncSession,
    query: TransferOrderQuery,
) -> PageResult[TransferOrderVO]:
    """调拨单分页查询（关键字、调出 / 调入仓库、状态、经办人、创建时间）。"""
    conditions = [TransferOrder.is_deleted == 0]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                TransferOrder.order_no.like(keyword),
                TransferOrder.remark.like(keyword),
            )
        )
    if query.order_no:
        conditions.append(TransferOrder.order_no.like(f"%{query.order_no.strip()}%"))
    if query.from_warehouse_id is not None:
        conditions.append(TransferOrder.from_warehouse_id == query.from_warehouse_id)
    if query.to_warehouse_id is not None:
        conditions.append(TransferOrder.to_warehouse_id == query.to_warehouse_id)
    if query.status is not None:
        conditions.append(TransferOrder.status == query.status)
    if query.operator_id is not None:
        conditions.append(TransferOrder.operator_id == query.operator_id)
    if query.start_time is not None:
        conditions.append(TransferOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(TransferOrder.created_at <= query.end_time)

    total = (
        await db.execute(
            select(func.count()).select_from(TransferOrder).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(TransferOrder, FromWarehouse.name, ToWarehouse.name)
        .outerjoin(
            FromWarehouse,
            FromWarehouse.id == TransferOrder.from_warehouse_id,
        )
        .outerjoin(ToWarehouse, ToWarehouse.id == TransferOrder.to_warehouse_id)
        .where(*conditions)
        .order_by(TransferOrder.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()
    result = [
        _to_order_vo(order, from_name, to_name) for order, from_name, to_name in rows
    ]

    return PageResult[TransferOrderVO](
        list=result,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_transfer_order(
    db: AsyncSession,
    order_id: int,
) -> TransferOrderDetailVO:
    """调拨单详情（主表 + 明细）。"""
    stmt = (
        select(TransferOrder, FromWarehouse.name, ToWarehouse.name)
        .outerjoin(
            FromWarehouse,
            FromWarehouse.id == TransferOrder.from_warehouse_id,
        )
        .outerjoin(ToWarehouse, ToWarehouse.id == TransferOrder.to_warehouse_id)
        .where(
            TransferOrder.id == order_id,
            TransferOrder.is_deleted == 0,
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="调拨单不存在")
    order, from_name, to_name = row

    item_stmt = (
        _item_query()
        .where(
            TransferOrderItem.order_id == order.id,
            TransferOrderItem.is_deleted == 0,
        )
        .order_by(TransferOrderItem.id.asc())
    )
    item_rows = (await db.execute(item_stmt)).all()

    detail = TransferOrderDetailVO(
        **_to_order_vo(order, from_name, to_name).model_dump()
    )
    detail.items = [_to_item_vo(*item_row) for item_row in item_rows]
    return detail


async def create_transfer_order(
    db: AsyncSession,
    payload: TransferOrderCreate,
    current_user_id: int,
) -> TransferOrderDetailVO:
    """新建调拨单（草稿）：单号自动生成，逐件追踪明细可指定库存件实例。"""
    if payload.from_warehouse_id == payload.to_warehouse_id:
        raise BizException(code=400, message="调出仓库与调入仓库不能相同")

    await _get_warehouse_or_404(db, payload.from_warehouse_id, "调出")
    await _get_warehouse_or_404(db, payload.to_warehouse_id, "调入")
    await _ensure_user_exists(db, payload.operator_id, "经办人")

    operator_id = payload.operator_id or current_user_id
    rows = await _build_item_rows(
        db,
        payload.items,
        payload.from_warehouse_id,
        payload.to_warehouse_id,
    )
    order = await _insert_order_with_retry(
        db, payload, rows, operator_id, current_user_id
    )
    return await get_transfer_order(db, order.id)


# ---------------------------------------------------------------- 状态流转
async def _load_items_for_update(
    db: AsyncSession,
    order_id: int,
) -> list[TransferOrderItem]:
    """按主键升序锁定调拨明细，避免同一单据并发调出 / 调入时明细被改。"""
    stmt = (
        select(TransferOrderItem)
        .where(
            TransferOrderItem.order_id == order_id,
            TransferOrderItem.is_deleted == 0,
        )
        .order_by(TransferOrderItem.id.asc())
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


async def _lock_parts(db: AsyncSession, part_ids: list[int]) -> None:
    """按配件主键升序锁配件行，串行化调入时目标库存行的创建动作。"""
    ids = sorted(set(part_ids))
    if not ids:
        return
    await db.execute(
        select(Part.id)
        .where(Part.id.in_(ids))
        .order_by(Part.id.asc())
        .with_for_update()
    )


async def _lock_inventory_row(
    db: AsyncSession,
    cache: dict[tuple[int, int, int | None], Inventory | None],
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
) -> Inventory | None:
    """按 配件 + 仓库 + 库位 加行锁取库存行；同一事务内重复键复用缓存对象。"""
    key = (part_id, warehouse_id, location_id)
    if key in cache:
        return cache[key]

    location_cond = (
        Inventory.location_id.is_(None)
        if location_id is None
        else Inventory.location_id == location_id
    )
    stmt = (
        select(Inventory)
        .where(
            Inventory.part_id == part_id,
            Inventory.warehouse_id == warehouse_id,
            location_cond,
            Inventory.is_deleted == 0,
        )
        .with_for_update()
    )
    inventory = (await db.execute(stmt)).scalar_one_or_none()
    cache[key] = inventory
    return inventory


async def _lock_or_create_inventory(
    db: AsyncSession,
    cache: dict[tuple[int, int, int | None], Inventory],
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
    current_user_id: int,
) -> Inventory:
    """取 配件+仓库+库位 的库存行并加行锁，不存在则创建（调入使用）。"""
    key = (part_id, warehouse_id, location_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    location_cond = (
        Inventory.location_id.is_(None)
        if location_id is None
        else Inventory.location_id == location_id
    )
    stmt = select(Inventory).where(
        Inventory.part_id == part_id,
        Inventory.warehouse_id == warehouse_id,
        location_cond,
    )
    inventory = (await db.execute(stmt.with_for_update())).scalar_one_or_none()
    if inventory is None:
        inventory = Inventory(
            part_id=part_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=ZERO_QTY,
            item_count=0,
            locked_qty=ZERO_QTY,
            avg_cost=ZERO_COST,
            created_by=current_user_id,
        )
        db.add(inventory)
        # 立即 flush：让本事务后续明细可查到该行，同时尽早暴露唯一索引冲突
        await db.flush()
    elif inventory.is_deleted:
        # 历史逻辑删除的库存行直接复用，避免与唯一索引冲突
        inventory.is_deleted = 0
        inventory.quantity = ZERO_QTY
        inventory.item_count = 0
        inventory.locked_qty = ZERO_QTY
        inventory.avg_cost = ZERO_COST
        inventory.updated_by = current_user_id

    cache[key] = inventory
    return inventory


async def _load_transfer_out_costs(
    db: AsyncSession,
    order_id: int,
) -> dict[tuple[int, int | None, int | None], Decimal]:
    """读取确认调出时写入的成本，调入按同一成本入账。"""
    rows = (
        (
            await db.execute(
                select(InventoryTransaction).where(
                    InventoryTransaction.ref_type == RefType.TRANSFER,
                    InventoryTransaction.ref_id == order_id,
                    InventoryTransaction.biz_type == BizType.TRANSFER_OUT,
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        (row.part_id, row.location_id, row.inventory_item_id): Decimal(
            row.unit_cost or 0
        )
        for row in rows
    }


def _transfer_unit_cost(
    costs: dict[tuple[int, int | None, int | None], Decimal],
    item: TransferOrderItem,
    instance: InventoryItem | None,
) -> Decimal:
    """取明细对应的调出成本：优先精确匹配实例 / 库位，其次实例成本。"""
    cost = costs.get((item.part_id, item.from_location_id, item.inventory_item_id))
    if cost is None:
        cost = costs.get((item.part_id, item.from_location_id, None))
    if cost is None and instance is not None:
        cost = Decimal(instance.unit_cost or 0)
    return Decimal(cost or 0).quantize(COST_QUANT, rounding=ROUND_HALF_UP)


async def _apply_transfer_out(
    db: AsyncSession,
    order: TransferOrder,
    items: list[TransferOrderItem],
    parts: dict[int, Part],
    inventory_items: dict[int, InventoryItem],
    current_user_id: int,
    now: datetime,
) -> None:
    """逐条扣减调出仓库库存并写 TRANSFER_OUT 流水；调用前已完成校验与加锁。"""
    cache: dict[tuple[int, int, int | None], Inventory | None] = {}

    def _sort_key(detail: TransferOrderItem) -> tuple[int, int, int]:
        """按 配件 + 库位 + 明细主键 排序，统一多张单据的加锁顺序。"""
        instance = (
            inventory_items.get(detail.inventory_item_id)
            if detail.inventory_item_id is not None
            else None
        )
        location_id = (
            instance.location_id if instance is not None else detail.from_location_id
        )
        return (detail.part_id, location_id or 0, detail.id)

    for item in sorted(items, key=_sort_key):
        part = parts[item.part_id]
        instance = (
            inventory_items.get(item.inventory_item_id)
            if item.inventory_item_id is not None
            else None
        )
        if part.track_by_item == 1 and instance is None:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法调出",
            )

        location_id = (
            instance.location_id if instance is not None else item.from_location_id
        )
        inventory = await _lock_inventory_row(
            db,
            cache,
            part_id=item.part_id,
            warehouse_id=order.from_warehouse_id,
            location_id=location_id,
        )
        if inventory is None:
            raise BizException(
                code=INSUFFICIENT_STOCK,
                message=f"配件 {part.part_name} 在调出仓库/库位无库存记录，无法调出",
            )

        before_qty = _qty(inventory.quantity)
        quantity = _qty(item.quantity)
        if before_qty < quantity:
            raise BizException(
                code=INSUFFICIENT_STOCK,
                message=(
                    f"配件 {part.part_name} 库存不足："
                    f"当前 {before_qty}，需调出 {quantity}"
                ),
            )

        unit_cost = Decimal(inventory.avg_cost or 0)
        if unit_cost == 0 and instance is not None:
            unit_cost = Decimal(instance.unit_cost or 0)

        if instance is not None:
            # 实例状态置为锁定（在途），调入时再回填目标仓库 / 库位并恢复在库
            instance.status = InventoryItemStatus.LOCKED
            instance.updated_by = current_user_id
            inventory.item_count = max(int(inventory.item_count or 0) - 1, 0)
            item.from_location_id = location_id
            if item.batch_no is None:
                item.batch_no = instance.batch_no

        inventory.quantity = before_qty - quantity
        inventory.last_out_at = now
        inventory.updated_by = current_user_id
        item.updated_by = current_user_id

        db.add(
            InventoryTransaction(
                part_id=item.part_id,
                inventory_item_id=item.inventory_item_id,
                warehouse_id=order.from_warehouse_id,
                location_id=location_id,
                biz_type=BizType.TRANSFER_OUT,
                change_qty=-quantity,
                before_qty=before_qty,
                after_qty=inventory.quantity,
                unit_cost=unit_cost,
                ref_type=RefType.TRANSFER,
                ref_id=order.id,
                ref_no=order.order_no,
                batch_no=item.batch_no,
                scan_code=instance.item_code if instance is not None else None,
                operator_id=current_user_id,
                remark=item.remark,
                created_by=current_user_id,
            )
        )


async def _apply_transfer_in(
    db: AsyncSession,
    order: TransferOrder,
    items: list[TransferOrderItem],
    parts: dict[int, Part],
    inventory_items: dict[int, InventoryItem],
    costs: dict[tuple[int, int | None, int | None], Decimal],
    current_user_id: int,
    now: datetime,
) -> None:
    """逐条增加调入仓库库存并写 TRANSFER_IN 流水；调用前已完成校验与加锁。"""
    cache: dict[tuple[int, int, int | None], Inventory] = {}

    def _sort_key(detail: TransferOrderItem) -> tuple[int, int, int]:
        """按 配件 + 目标库位 + 明细主键 排序，统一多张单据的加锁顺序。"""
        return (detail.part_id, detail.to_location_id or 0, detail.id)

    for item in sorted(items, key=_sort_key):
        part = parts[item.part_id]
        instance = (
            inventory_items.get(item.inventory_item_id)
            if item.inventory_item_id is not None
            else None
        )
        if part.track_by_item == 1 and instance is None:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法调入",
            )

        location_id = item.to_location_id
        inventory = await _lock_or_create_inventory(
            db,
            cache,
            part_id=item.part_id,
            warehouse_id=order.to_warehouse_id,
            location_id=location_id,
            current_user_id=current_user_id,
        )

        before_qty = _qty(inventory.quantity)
        quantity = _qty(item.quantity)
        unit_cost = _transfer_unit_cost(costs, item, instance)

        inventory.quantity = before_qty + quantity
        if unit_cost > 0:
            inventory.avg_cost = _calc_avg_cost(
                before_qty,
                Decimal(inventory.avg_cost or 0),
                quantity,
                unit_cost,
            )
        inventory.last_in_at = now
        inventory.updated_by = current_user_id
        item.updated_by = current_user_id

        if instance is not None:
            # 在途实例回填目标仓库 / 库位并恢复在库
            instance.warehouse_id = order.to_warehouse_id
            instance.location_id = location_id
            instance.status = InventoryItemStatus.IN_STOCK
            instance.updated_by = current_user_id
            inventory.item_count = int(inventory.item_count or 0) + 1

        db.add(
            InventoryTransaction(
                part_id=item.part_id,
                inventory_item_id=item.inventory_item_id,
                warehouse_id=order.to_warehouse_id,
                location_id=location_id,
                biz_type=BizType.TRANSFER_IN,
                change_qty=quantity,
                before_qty=before_qty,
                after_qty=inventory.quantity,
                unit_cost=unit_cost,
                ref_type=RefType.TRANSFER,
                ref_id=order.id,
                ref_no=order.order_no,
                batch_no=item.batch_no,
                scan_code=instance.item_code if instance is not None else None,
                operator_id=current_user_id,
                remark=item.remark,
                created_by=current_user_id,
            )
        )


async def transfer_out(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> TransferOrderDetailVO:
    """确认调出：1 草稿 / 2 待审 → 3 已调出。

    扣减调出仓库库存并写 TRANSFER_OUT 流水；逐件追踪实例置为锁定（在途）。
    库存行不存在或数量不足返回 2001，实例状态不可调出返回 2002 / 2003 / 2004。
    """
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status not in (TransferStatus.DRAFT, TransferStatus.PENDING):
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿或待审状态的调拨单可确认调出",
        )

    items = await _load_items_for_update(db, order.id)
    if not items:
        raise BizException(code=400, message="调拨单明细为空，无法确认调出")

    # 执行阶段配件可能已停用，不阻塞在途单据；是否追踪仍以主数据为准
    parts = await _load_parts(
        db, [item.part_id for item in items], require_enabled=False
    )
    now = datetime.now()
    try:
        inventory_items = await _load_inventory_items(
            db,
            items,
            order.from_warehouse_id,
            parts,
            exclude_order_id=order.id,
            for_update=True,
        )

        # 锁内再校验一次：按件追踪必须绑定库存件实例
        for item in items:
            part = parts[item.part_id]
            if part.track_by_item == 1 and item.inventory_item_id is None:
                raise BizException(
                    code=400,
                    message=(
                        f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法调出"
                    ),
                )

        await _apply_transfer_out(
            db,
            order,
            items,
            parts,
            inventory_items,
            current_user_id,
            now,
        )

        order.status = TransferStatus.OUT_DONE
        order.audit_user_id = current_user_id
        order.transfer_at = now
        order.updated_by = current_user_id

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await get_transfer_order(db, order.id)


async def transfer_in(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> TransferOrderDetailVO:
    """确认调入：3 已调出 → 4 已调入。

    增加调入仓库库存并写 TRANSFER_IN 流水；逐件追踪实例回填目标仓库 / 库位并
    恢复为在库，同时同步 `inventory.item_count`。在途实例状态已变更返回 409。
    """
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != TransferStatus.OUT_DONE:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅已调出状态的调拨单可确认调入",
        )

    items = await _load_items_for_update(db, order.id)
    if not items:
        raise BizException(code=400, message="调拨单明细为空，无法确认调入")

    parts = await _load_parts(
        db, [item.part_id for item in items], require_enabled=False
    )
    now = datetime.now()
    try:
        # 先锁配件行再锁库存行：串行化调入库存行的创建，统一加锁顺序避免死锁
        await _lock_parts(db, [item.part_id for item in items])
        inventory_items = await _load_inventory_items(
            db,
            items,
            order.from_warehouse_id,
            parts,
            for_update=True,
            expected_status=InventoryItemStatus.LOCKED,
            allow_untracked_instance=True,
        )

        for item in items:
            part = parts[item.part_id]
            if part.track_by_item == 1 and item.inventory_item_id is None:
                raise BizException(
                    code=400,
                    message=(
                        f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法调入"
                    ),
                )

        costs = await _load_transfer_out_costs(db, order.id)
        await _apply_transfer_in(
            db,
            order,
            items,
            parts,
            inventory_items,
            costs,
            current_user_id,
            now,
        )

        order.status = TransferStatus.IN_DONE
        order.updated_by = current_user_id

        await db.commit()
    except IntegrityError as exc:
        # 并发调入同一 配件 + 仓库 + 库位 时可能同时新建库存行，唯一索引兜底
        await db.rollback()
        if INVENTORY_UNIQUE_KEY in str(exc.orig):
            raise BizException(
                code=409,
                message="调入库存行创建冲突，请重试",
            ) from exc
        raise
    except Exception:
        await db.rollback()
        raise

    return await get_transfer_order(db, order.id)


async def cancel_transfer_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> TransferOrderDetailVO:
    """作废调拨单：1 草稿 / 2 待审 → 5 作废（不调整库存）。

    已调出的单据库存已扣减，必须完成调入，不允许作废（返回 3001）。
    """
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status not in (TransferStatus.DRAFT, TransferStatus.PENDING):
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿或待审状态的调拨单可作废；已调出的请完成调入",
        )

    order.status = TransferStatus.CANCELLED
    order.updated_by = current_user_id
    await db.commit()
    return await get_transfer_order(db, order.id)
