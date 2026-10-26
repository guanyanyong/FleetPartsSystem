"""盘点单业务逻辑：创建（冻结账面）、开始盘点、扫码 / 手工录入、完成、作废与查询。

约定：
- 单号规则 `ST + yyyyMMdd + 6 位流水`，复用 `app.services.code_generator` 取号；
  并发下依赖 `uk_order_no` 唯一索引，冲突时自动重新取号重试。
- 创建盘点单即冻结账面（book_qty），前端传入的 `book_qty` 不采信：
  * 未提交明细时按仓库自动快照：非逐件追踪配件按「配件 + 仓库 + 库位」库存行
    生成明细，`book_qty = inventory.quantity`，`actual_qty` 预填为账面数，
    库管只改差异；逐件追踪配件按在库实例逐个生成明细，`book_qty = 1`、
    `actual_qty = 0`，扫码（或手工标记）一件即 `actual_qty = 1`，未扫到的实例
    在完成盘点时按盘亏处理。
  * 提交明细时同样以库存 / 库存件为准冻结账面；明细未指定
    `inventory_item_id` 且配件按件追踪时视为「盘盈行」（`book_qty = 0`），
    完成盘点时按实盘数量补建带二维码的库存件实例。
- 状态流转：1 草稿 → 2 盘点中 → 3 已完成；草稿 / 盘点中 → 4 作废。
- 完成盘点（2 → 3）在一个事务内完成：逐行计算 `diff_qty`（盘盈为正、盘亏为负），
  盘盈 `inventory.quantity += diff` 并写 ADJUST_IN 流水，盘亏
  `inventory.quantity += diff`（diff 为负）并写 ADJUST_OUT 流水；逐件追踪的
  盘亏实例 `inventory_item.status = 5`（已盘亏）并同步 `item_count`，
  盘盈行补建实例并同步 `item_count`。任意一步失败全部回滚，并清理已落盘的二维码。
- 单据与明细均逻辑删除；created_by / updated_by 取当前登录用户。
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    StocktakeOrder,
    StocktakeOrderItem,
    SysUser,
    Warehouse,
    WarehouseLocation,
)
from app.models.enums import (
    BizType,
    CommonStatus,
    InventoryItemStatus,
    RefType,
    StocktakeStatus,
    UserStatus,
)
from app.schemas.common import PageResult
from app.schemas.stocktake import (
    StocktakeOrderCreate,
    StocktakeOrderDetailVO,
    StocktakeOrderItemCreate,
    StocktakeOrderItemUpdate,
    StocktakeOrderItemVO,
    StocktakeOrderQuery,
    StocktakeOrderVO,
    StocktakeScanRequest,
)
from app.services.code_generator import (
    ITEM_CODE_SEQUENCE,
    STOCKTAKE_SEQUENCE,
    SequenceExhausted,
    generate_item_code,
    generate_stocktake_no,
    next_sequence,
    next_sequences,
)
from app.services.inventory_item_service import normalize_scan_code
from app.services.qrcode_service import generate_qrcode, qrcode_file_path

__all__ = [
    "cancel_stocktake_order",
    "create_stocktake_order",
    "finish_stocktake_order",
    "get_stocktake_order",
    "list_stocktake_orders",
    "scan_stocktake_item",
    "start_stocktake_order",
    "update_stocktake_item",
]

# 业务错误码（见 docs/backend-requirements.md 错误码约定）
ORDER_STATUS_NOT_ALLOWED: int = 3001
SCAN_CODE_UNRECOGNIZED: int = 4001
ITEM_NOT_IN_STOCK: int = 2002

# 单号 / 库存件编码并发重试次数
ORDER_NO_MAX_RETRY: int = 5
FINISH_MAX_RETRY: int = 3

# 数量保留两位小数、成本保留四位小数
QTY_QUANT: Decimal = Decimal("0.01")
COST_QUANT: Decimal = Decimal("0.0001")
ZERO_QTY: Decimal = Decimal("0.00")
ONE_QTY: Decimal = Decimal("1.00")

# 唯一索引名（用于识别可重试的并发冲突）
INVENTORY_UNIQUE_KEY: str = "uk_part_warehouse_location"
ITEM_CODE_UNIQUE_KEY: str = "uk_item_code"


# ---------------------------------------------------------------- 内部工具
def _qty(value: Decimal | int | None) -> Decimal:
    """数量统一保留两位小数（四舍五入），None 视为 0。"""
    if value is None:
        return ZERO_QTY
    return Decimal(value).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def _calc_diff(
    actual_qty: Decimal | int | None,
    book_qty: Decimal | int | None,
) -> Decimal:
    """差异数量：盘盈为正、盘亏为负。"""
    return _qty(actual_qty) - _qty(book_qty)


def _normalize_actual_qty(
    part: Part,
    actual_qty: Decimal,
    *,
    inventory_item_id: int | None = None,
) -> Decimal:
    """校验并归一化实盘数量。

    - 绑定库存件实例的明细只能是 0（盘亏）或 1（在库）；
    - 其它逐件追踪明细（盘盈行）必须是非负整数；
    - 非逐件追踪明细允许两位小数。
    """
    actual = _qty(actual_qty)
    if actual < 0:
        raise BizException(code=400, message="实盘数量不能为负数")

    if inventory_item_id is not None:
        if actual > ONE_QTY:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，单个库存件实盘数量只能为 0 或 1",
            )
        return actual

    if part.track_by_item == 1 and actual != actual.to_integral_value():
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 按件追踪，实盘数量必须为整数",
        )
    return actual


async def _get_warehouse_or_404(db: AsyncSession, warehouse_id: int) -> Warehouse:
    """取启用中的仓库，不存在抛 404，已停用抛 400。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message="仓库不存在")
    if warehouse.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"仓库 {warehouse.name} 已停用")
    return warehouse


async def _ensure_user_exists(db: AsyncSession, user_id: int) -> None:
    """校验盘点人存在且启用。"""
    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message="盘点人不存在")
    if user.status != UserStatus.ENABLED:
        raise BizException(
            code=400,
            message=f"盘点人 {user.real_name or user.username} 已停用",
        )


async def _ensure_locations(
    db: AsyncSession,
    warehouse_id: int,
    location_ids: list[int | None],
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
        raise BizException(code=404, message=f"库位不存在: {missing[0]}")

    wrong = sorted(row.id for row in rows if row.warehouse_id != warehouse_id)
    if wrong:
        raise BizException(code=400, message=f"库位 {wrong[0]} 不属于所选仓库")

    disabled = sorted(row.id for row in rows if row.status != CommonStatus.ENABLED)
    if disabled:
        location = found[disabled[0]]
        raise BizException(code=400, message=f"库位 {location.location_code} 已停用")


async def _load_parts(db: AsyncSession, part_ids: list[int]) -> dict[int, Part]:
    """批量加载配件（含已停用配件：历史库存仍需要盘点）。"""
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
    return parts


async def _book_qty(
    db: AsyncSession,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
) -> Decimal:
    """读取指定 配件 + 仓库 + 库位 的账面数量，无库存行为 0。"""
    stmt = select(Inventory.quantity).where(
        Inventory.part_id == part_id,
        Inventory.warehouse_id == warehouse_id,
        Inventory.is_deleted == 0,
    )
    if location_id is None:
        stmt = stmt.where(Inventory.location_id.is_(None))
    else:
        stmt = stmt.where(Inventory.location_id == location_id)
    return _qty((await db.execute(stmt)).scalar_one_or_none())


async def _build_payload_rows(
    db: AsyncSession,
    items: list[StocktakeOrderItemCreate],
    warehouse_id: int,
) -> list[dict[str, Any]]:
    """把提交的明细转换为盘点明细行，并按库存冻结账面数量。"""
    parts = await _load_parts(db, [item.part_id for item in items])
    await _ensure_locations(
        db,
        warehouse_id,
        [item.location_id for item in items if item.inventory_item_id is None],
    )

    item_ids = {
        item.inventory_item_id for item in items if item.inventory_item_id is not None
    }
    inventory_items: dict[int, InventoryItem] = {}
    if item_ids:
        rows = (
            (
                await db.execute(
                    select(InventoryItem).where(
                        InventoryItem.id.in_(item_ids),
                        InventoryItem.is_deleted == 0,
                    )
                )
            )
            .scalars()
            .all()
        )
        inventory_items = {row.id: row for row in rows}
        missing = sorted(item_ids - inventory_items.keys())
        if missing:
            raise BizException(code=404, message=f"库存件不存在: {missing[0]}")

    result: list[dict[str, Any]] = []
    seen_items: set[int] = set()
    seen_rows: set[tuple[int, int | None]] = set()

    for item in items:
        part = parts[item.part_id]
        actual_supplied = "actual_qty" in item.model_fields_set
        location_id = item.location_id

        if item.inventory_item_id is not None:
            inventory_item = inventory_items[item.inventory_item_id]
            if inventory_item.part_id != part.id:
                raise BizException(code=400, message="库存件与配件不匹配")
            if inventory_item.warehouse_id != warehouse_id:
                raise BizException(
                    code=400,
                    message=f"库存件 {inventory_item.item_code} 不属于所选仓库",
                )
            if inventory_item.status != InventoryItemStatus.IN_STOCK:
                raise BizException(
                    code=400,
                    message=f"库存件 {inventory_item.item_code} 不在库，无法盘点",
                )
            if part.track_by_item != 1:
                raise BizException(
                    code=400,
                    message=f"配件 {part.part_name} 未按件追踪，不能指定库存件",
                )
            if inventory_item.id in seen_items:
                raise BizException(
                    code=400,
                    message=f"库存件 {inventory_item.item_code} 重复提交",
                )
            seen_items.add(inventory_item.id)

            # 逐件追踪的实例默认按盘亏（0）盘点，扫码 / 手工确认后改为 1
            actual_qty = _normalize_actual_qty(
                part,
                item.actual_qty if actual_supplied else ZERO_QTY,
                inventory_item_id=inventory_item.id,
            )
            book_qty = ONE_QTY
            location_id = inventory_item.location_id
        elif part.track_by_item == 1:
            # 未指定实例的逐件追踪明细按盘盈行处理，完成盘点时补建实例
            actual_qty = _normalize_actual_qty(part, item.actual_qty)
            book_qty = ZERO_QTY
        else:
            key = (part.id, item.location_id)
            if key in seen_rows:
                raise BizException(
                    code=400,
                    message=f"配件 {part.part_name} 在同一库位重复提交",
                )
            seen_rows.add(key)

            book_qty = await _book_qty(db, part.id, warehouse_id, item.location_id)
            actual_qty = _qty(item.actual_qty) if actual_supplied else book_qty
            if actual_qty < 0:
                raise BizException(code=400, message="实盘数量不能为负数")

        result.append(
            {
                "part_id": part.id,
                "inventory_item_id": item.inventory_item_id,
                "location_id": location_id,
                "book_qty": book_qty,
                "actual_qty": actual_qty,
                "diff_qty": _calc_diff(actual_qty, book_qty),
                "scan_code": None,
                "remark": item.remark,
            }
        )
    return result


async def _build_snapshot_rows(
    db: AsyncSession,
    warehouse_id: int,
) -> list[dict[str, Any]]:
    """按仓库现有库存生成盘点明细快照。"""
    rows: list[dict[str, Any]] = []

    inventory_rows = (
        await db.execute(
            select(Inventory, Part)
            .join(Part, Part.id == Inventory.part_id)
            .where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.is_deleted == 0,
                Part.is_deleted == 0,
                Part.track_by_item != 1,
            )
            .order_by(Inventory.part_id.asc(), Inventory.location_id.asc())
        )
    ).all()
    for inventory, _part in inventory_rows:
        book_qty = _qty(inventory.quantity)
        if book_qty <= 0:
            continue
        rows.append(
            {
                "part_id": inventory.part_id,
                "inventory_item_id": None,
                "location_id": inventory.location_id,
                "book_qty": book_qty,
                "actual_qty": book_qty,
                "diff_qty": ZERO_QTY,
                "scan_code": None,
                "remark": None,
            }
        )

    item_rows = (
        (
            await db.execute(
                select(InventoryItem)
                .join(Part, Part.id == InventoryItem.part_id)
                .where(
                    InventoryItem.warehouse_id == warehouse_id,
                    InventoryItem.is_deleted == 0,
                    InventoryItem.status == InventoryItemStatus.IN_STOCK,
                    Part.is_deleted == 0,
                    Part.track_by_item == 1,
                )
                .order_by(
                    InventoryItem.part_id.asc(),
                    InventoryItem.location_id.asc(),
                    InventoryItem.id.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    for inventory_item in item_rows:
        rows.append(
            {
                "part_id": inventory_item.part_id,
                "inventory_item_id": inventory_item.id,
                "location_id": inventory_item.location_id,
                "book_qty": ONE_QTY,
                "actual_qty": ZERO_QTY,
                "diff_qty": -ONE_QTY,
                "scan_code": None,
                "remark": None,
            }
        )

    rows.sort(
        key=lambda row: (
            row["part_id"],
            row["location_id"] or 0,
            row["inventory_item_id"] or 0,
        )
    )
    return rows


async def _insert_order_with_retry(
    db: AsyncSession,
    payload: StocktakeOrderCreate,
    rows: list[dict[str, Any]],
    operator_id: int,
    current_user_id: int,
) -> StocktakeOrder:
    """插入盘点单主表与明细，单号冲突（并发）时重新取号。"""
    for attempt in range(1, ORDER_NO_MAX_RETRY + 1):
        try:
            seq = await next_sequence(db, STOCKTAKE_SEQUENCE)
        except SequenceExhausted as exc:
            raise BizException(
                code=409,
                message="当日盘点单号已用尽，请联系管理员",
            ) from exc

        order = StocktakeOrder(
            order_no=generate_stocktake_no(seq),
            warehouse_id=payload.warehouse_id,
            status=StocktakeStatus.DRAFT,
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
                    StocktakeOrderItem(
                        order_id=order.id,
                        created_by=current_user_id,
                        updated_by=current_user_id,
                        **row,
                    )
                )
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            if attempt < ORDER_NO_MAX_RETRY and "uk_order_no" in str(exc.orig):
                continue
            raise BizException(
                code=409,
                message="盘点单号生成冲突，请重试",
            ) from exc
        return order

    raise BizException(code=409, message="盘点单号生成冲突，请重试")


async def create_stocktake_order(
    db: AsyncSession,
    payload: StocktakeOrderCreate,
    current_user_id: int,
) -> StocktakeOrderDetailVO:
    """创建盘点单（草稿）。"""
    await _get_warehouse_or_404(db, payload.warehouse_id)

    operator_id = payload.operator_id or current_user_id
    if payload.operator_id is not None and payload.operator_id != current_user_id:
        await _ensure_user_exists(db, payload.operator_id)

    if payload.items:
        rows = await _build_payload_rows(db, payload.items, payload.warehouse_id)
    else:
        rows = await _build_snapshot_rows(db, payload.warehouse_id)

    order = await _insert_order_with_retry(
        db, payload, rows, operator_id, current_user_id
    )
    return await get_stocktake_order(db, order.id)


async def _get_order_or_404(
    db: AsyncSession,
    order_id: int,
    *,
    for_update: bool = False,
) -> StocktakeOrder:
    """按主键取未删除的盘点单，不存在抛 404。"""
    stmt = select(StocktakeOrder).where(
        StocktakeOrder.id == order_id,
        StocktakeOrder.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise BizException(code=404, message="盘点单不存在")
    return order


def _to_order_vo(
    order: StocktakeOrder,
    warehouse_name: str | None = None,
) -> StocktakeOrderVO:
    """主表实体转 VO，并补充仓库名称。"""
    vo = StocktakeOrderVO.model_validate(order)
    vo.warehouse_name = warehouse_name
    return vo


def _to_item_vo(
    item: StocktakeOrderItem,
    part: Part | None = None,
    inventory_item: InventoryItem | None = None,
    location: WarehouseLocation | None = None,
) -> StocktakeOrderItemVO:
    """明细实体转 VO，并补充配件 / 库存件 / 库位展示字段。"""
    vo = StocktakeOrderItemVO.model_validate(item)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
        vo.unit = part.unit
    if inventory_item is not None:
        vo.item_code = inventory_item.item_code
    if location is not None:
        vo.location_code = location.location_code
    return vo


def _item_query() -> Any:
    """盘点明细查询骨架：带配件、库存件、库位展示字段。"""
    return (
        select(
            StocktakeOrderItem,
            Part,
            InventoryItem,
            WarehouseLocation,
        )
        .outerjoin(Part, Part.id == StocktakeOrderItem.part_id)
        .outerjoin(
            InventoryItem,
            InventoryItem.id == StocktakeOrderItem.inventory_item_id,
        )
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == StocktakeOrderItem.location_id,
        )
    )


async def _fetch_item_vo(
    db: AsyncSession,
    order_id: int,
    item_id: int,
) -> StocktakeOrderItemVO:
    """取单条盘点明细 VO，不存在抛 404。"""
    stmt = _item_query().where(
        StocktakeOrderItem.id == item_id,
        StocktakeOrderItem.order_id == order_id,
        StocktakeOrderItem.is_deleted == 0,
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="盘点明细不存在")
    return _to_item_vo(*row)


async def list_stocktake_orders(
    db: AsyncSession,
    query: StocktakeOrderQuery,
) -> PageResult[StocktakeOrderVO]:
    """盘点单分页查询（关键字、仓库、状态、盘点人、创建时间）。"""
    conditions = [StocktakeOrder.is_deleted == 0]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                StocktakeOrder.order_no.like(keyword),
                StocktakeOrder.remark.like(keyword),
            )
        )
    if query.order_no:
        conditions.append(StocktakeOrder.order_no.like(f"%{query.order_no.strip()}%"))
    if query.warehouse_id is not None:
        conditions.append(StocktakeOrder.warehouse_id == query.warehouse_id)
    if query.status is not None:
        conditions.append(StocktakeOrder.status == query.status)
    if query.operator_id is not None:
        conditions.append(StocktakeOrder.operator_id == query.operator_id)
    if query.start_time is not None:
        conditions.append(StocktakeOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(StocktakeOrder.created_at <= query.end_time)

    total = (
        await db.execute(
            select(func.count()).select_from(StocktakeOrder).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(StocktakeOrder, Warehouse.name)
        .outerjoin(Warehouse, Warehouse.id == StocktakeOrder.warehouse_id)
        .where(*conditions)
        .order_by(StocktakeOrder.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()
    result = [_to_order_vo(order, warehouse_name) for order, warehouse_name in rows]

    return PageResult[StocktakeOrderVO](
        list=result,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_stocktake_order(
    db: AsyncSession,
    order_id: int,
) -> StocktakeOrderDetailVO:
    """盘点单详情（主表 + 明细）。"""
    stmt = (
        select(StocktakeOrder, Warehouse.name)
        .outerjoin(Warehouse, Warehouse.id == StocktakeOrder.warehouse_id)
        .where(
            StocktakeOrder.id == order_id,
            StocktakeOrder.is_deleted == 0,
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="盘点单不存在")
    order, warehouse_name = row

    item_stmt = (
        _item_query()
        .where(
            StocktakeOrderItem.order_id == order.id,
            StocktakeOrderItem.is_deleted == 0,
        )
        .order_by(StocktakeOrderItem.id.asc())
    )
    item_rows = (await db.execute(item_stmt)).all()

    detail = StocktakeOrderDetailVO(**_to_order_vo(order, warehouse_name).model_dump())
    detail.items = [_to_item_vo(*item_row) for item_row in item_rows]
    return detail


async def start_stocktake_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> StocktakeOrderDetailVO:
    """开始盘点：1 草稿 → 2 盘点中。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != StocktakeStatus.DRAFT:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿状态的盘点单可开始盘点",
        )

    item_count = (
        await db.execute(
            select(func.count())
            .select_from(StocktakeOrderItem)
            .where(
                StocktakeOrderItem.order_id == order.id,
                StocktakeOrderItem.is_deleted == 0,
            )
        )
    ).scalar_one()
    if not item_count:
        raise BizException(code=400, message="盘点单明细为空，无法开始盘点")

    order.status = StocktakeStatus.COUNTING
    if order.operator_id is None:
        order.operator_id = current_user_id
    order.updated_by = current_user_id
    await db.commit()
    return await get_stocktake_order(db, order.id)


async def scan_stocktake_item(
    db: AsyncSession,
    order_id: int,
    payload: StocktakeScanRequest,
    current_user_id: int,
) -> StocktakeOrderItemVO:
    """扫码盘点：按二维码 / 库存件编码找到实例并标记为已盘（实盘 1 件）。

    支持扫到创建快照之后才入库的库存件：自动补充一条 `book_qty = 1`、
    `actual_qty = 1` 的明细（账面已包含该件，差异为 0），避免重复计数。
    """
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != StocktakeStatus.COUNTING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅盘点中状态的盘点单可扫码盘点",
        )

    code = normalize_scan_code(payload.code)
    if not code:
        raise BizException(code=SCAN_CODE_UNRECOGNIZED, message="扫码内容为空")

    inventory_item = (
        await db.execute(
            select(InventoryItem).where(
                or_(InventoryItem.qrcode == code, InventoryItem.item_code == code),
                InventoryItem.is_deleted == 0,
            )
        )
    ).scalar_one_or_none()
    if inventory_item is None:
        raise BizException(
            code=SCAN_CODE_UNRECOGNIZED,
            message=f"扫码内容无法识别: {payload.code}",
        )
    if inventory_item.warehouse_id != order.warehouse_id:
        raise BizException(code=400, message="该库存件不属于盘点仓库")
    if inventory_item.status != InventoryItemStatus.IN_STOCK:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {inventory_item.item_code} 不在库，无法盘点",
        )
    if payload.location_id is not None:
        await _ensure_locations(db, order.warehouse_id, [payload.location_id])

    parts = await _load_parts(db, [inventory_item.part_id])
    part = parts[inventory_item.part_id]
    if part.track_by_item != 1:
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 未按件追踪，请按明细录入实盘数量",
        )

    line = (
        await db.execute(
            select(StocktakeOrderItem)
            .where(
                StocktakeOrderItem.order_id == order.id,
                StocktakeOrderItem.inventory_item_id == inventory_item.id,
                StocktakeOrderItem.is_deleted == 0,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    if line is None:
        line = StocktakeOrderItem(
            order_id=order.id,
            part_id=inventory_item.part_id,
            inventory_item_id=inventory_item.id,
            location_id=inventory_item.location_id,
            book_qty=ONE_QTY,
            actual_qty=ONE_QTY,
            diff_qty=ZERO_QTY,
            scan_code=code,
            remark=None,
            created_by=current_user_id,
            updated_by=current_user_id,
        )
        db.add(line)
    else:
        book_qty = _qty(line.book_qty)
        if book_qty > 0 and _qty(line.actual_qty) >= book_qty:
            raise BizException(
                code=409,
                message=f"库存件 {inventory_item.item_code} 已盘点，请勿重复扫描",
            )
        line.actual_qty = book_qty if book_qty > 0 else ONE_QTY
        line.diff_qty = _calc_diff(line.actual_qty, book_qty)
        line.scan_code = code
        line.updated_by = current_user_id

    order.updated_by = current_user_id
    await db.commit()
    return await _fetch_item_vo(db, order.id, line.id)


async def update_stocktake_item(
    db: AsyncSession,
    order_id: int,
    item_id: int,
    payload: StocktakeOrderItemUpdate,
    current_user_id: int,
) -> StocktakeOrderItemVO:
    """录入单条明细的实盘数量（手工盘点 / 修正扫码结果）。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != StocktakeStatus.COUNTING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅盘点中状态的盘点单可录入实盘数量",
        )

    line = (
        await db.execute(
            select(StocktakeOrderItem)
            .where(
                StocktakeOrderItem.id == item_id,
                StocktakeOrderItem.order_id == order.id,
                StocktakeOrderItem.is_deleted == 0,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if line is None:
        raise BizException(code=404, message="盘点明细不存在")

    parts = await _load_parts(db, [line.part_id])
    part = parts[line.part_id]
    actual_qty = _normalize_actual_qty(
        part,
        payload.actual_qty,
        inventory_item_id=line.inventory_item_id,
    )

    line.actual_qty = actual_qty
    line.diff_qty = _calc_diff(actual_qty, line.book_qty)
    if payload.remark is not None:
        line.remark = payload.remark
    line.updated_by = current_user_id
    order.updated_by = current_user_id
    await db.commit()
    return await _fetch_item_vo(db, order.id, line.id)


async def _lock_inventory(
    db: AsyncSession,
    cache: dict[tuple[int, int, int | None], Inventory],
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
    current_user_id: int,
) -> Inventory:
    """取 配件+仓库+库位 的库存行并加 `FOR UPDATE` 行锁，不存在则创建。"""
    key = (part_id, warehouse_id, location_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    stmt = select(Inventory).where(
        Inventory.part_id == part_id,
        Inventory.warehouse_id == warehouse_id,
    )
    if location_id is None:
        stmt = stmt.where(Inventory.location_id.is_(None))
    else:
        stmt = stmt.where(Inventory.location_id == location_id)

    inventory = (await db.execute(stmt.with_for_update())).scalar_one_or_none()
    if inventory is None:
        inventory = Inventory(
            part_id=part_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=ZERO_QTY,
            item_count=0,
            locked_qty=ZERO_QTY,
            avg_cost=Decimal("0.0000"),
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
        inventory.avg_cost = Decimal("0.0000")
        inventory.updated_by = current_user_id

    cache[key] = inventory
    return inventory


async def _load_items_for_update(
    db: AsyncSession,
    order_id: int,
) -> list[StocktakeOrderItem]:
    """加载盘点明细并加行锁（完成盘点期间不允许并发修改明细）。"""
    stmt = (
        select(StocktakeOrderItem)
        .where(
            StocktakeOrderItem.order_id == order_id,
            StocktakeOrderItem.is_deleted == 0,
        )
        .order_by(StocktakeOrderItem.id.asc())
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load_inventory_items_for_update(
    db: AsyncSession,
    item_ids: list[int | None],
) -> dict[int, InventoryItem]:
    """批量加载库存件实例并加行锁。"""
    ids = {item_id for item_id in item_ids if item_id is not None}
    if not ids:
        return {}

    stmt = (
        select(InventoryItem)
        .where(InventoryItem.id.in_(ids))
        .order_by(InventoryItem.id.asc())
        .with_for_update()
    )
    return {row.id: row for row in (await db.execute(stmt)).scalars().all()}


def _remove_qrcode_files(paths: list[Path]) -> None:
    """事务回滚后清理已落盘的二维码图片，避免产生孤儿文件。"""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # 清理失败不影响主流程，最多留下无用图片
            continue


def _add_transaction(
    db: AsyncSession,
    order: StocktakeOrder,
    item: StocktakeOrderItem,
    *,
    biz_type: str,
    change_qty: Decimal,
    before_qty: Decimal,
    after_qty: Decimal,
    unit_cost: Decimal | None,
    current_user_id: int,
    inventory_item_id: int | None = None,
) -> None:
    """写一条盘点调整库存流水。"""
    db.add(
        InventoryTransaction(
            part_id=item.part_id,
            inventory_item_id=inventory_item_id,
            warehouse_id=order.warehouse_id,
            location_id=item.location_id,
            biz_type=biz_type,
            change_qty=change_qty,
            before_qty=before_qty,
            after_qty=after_qty,
            unit_cost=unit_cost or Decimal("0.0000"),
            ref_type=RefType.STOCKTAKE,
            ref_id=order.id,
            ref_no=order.order_no,
            scan_code=item.scan_code,
            operator_id=current_user_id,
            remark=item.remark,
            created_by=current_user_id,
        )
    )


def _apply_tracked_loss(
    db: AsyncSession,
    order: StocktakeOrder,
    item: StocktakeOrderItem,
    part: Part,
    inventory: Inventory,
    inventory_item: InventoryItem | None,
    before_qty: Decimal,
    after_qty: Decimal,
    current_user_id: int,
) -> None:
    """逐件追踪：盘亏一个库存件实例（status → 5）并扣减汇总数量。"""
    if item.diff_qty != -ONE_QTY:
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 按件追踪，库存件差异只能为 1 件",
        )
    if inventory_item is None or inventory_item.is_deleted:
        raise BizException(code=409, message="盘点明细关联的库存件不存在")
    if inventory_item.status != InventoryItemStatus.IN_STOCK:
        raise BizException(
            code=409,
            message=f"库存件 {inventory_item.item_code} 状态已变更，请重新盘点",
        )
    if (
        inventory_item.part_id != item.part_id
        or inventory_item.warehouse_id != order.warehouse_id
    ):
        raise BizException(
            code=409,
            message=f"库存件 {inventory_item.item_code} 已变更仓库，请重新盘点",
        )
    if (inventory.item_count or 0) < 1:
        raise BizException(
            code=409,
            message=f"配件 {part.part_name} 在库实例数不足，请检查库存数据",
        )

    inventory_item.status = InventoryItemStatus.LOST
    inventory_item.updated_by = current_user_id
    inventory.item_count = (inventory.item_count or 0) - 1
    inventory.quantity = after_qty
    inventory.updated_by = current_user_id
    _add_transaction(
        db,
        order,
        item,
        biz_type=BizType.ADJUST_OUT,
        change_qty=item.diff_qty,
        before_qty=before_qty,
        after_qty=after_qty,
        unit_cost=inventory_item.unit_cost,
        current_user_id=current_user_id,
        inventory_item_id=inventory_item.id,
    )


async def _apply_tracked_gain(
    db: AsyncSession,
    order: StocktakeOrder,
    item: StocktakeOrderItem,
    part: Part,
    inventory: Inventory,
    before_qty: Decimal,
    after_qty: Decimal,
    current_user_id: int,
    now: datetime,
    qr_files: list[Path],
) -> None:
    """逐件追踪：盘盈补建带二维码的库存件实例并增加汇总数量。"""
    gain_qty = int(item.diff_qty)
    if item.diff_qty != gain_qty or gain_qty <= 0:
        raise BizException(
            code=400,
            message=f"配件 {part.part_name} 按件追踪，盘盈数量必须为正整数",
        )

    try:
        sequences = await next_sequences(db, ITEM_CODE_SEQUENCE, gain_qty, at=now)
    except SequenceExhausted as exc:
        raise BizException(
            code=409,
            message="当日库存件编码已用尽，请联系管理员",
        ) from exc

    unit_cost = (inventory.avg_cost or Decimal(0)).quantize(
        COST_QUANT, rounding=ROUND_HALF_UP
    )
    for seq in sequences:
        item_code = generate_item_code(seq, at=now)
        qr_path = qrcode_file_path(item_code)
        qr_image = generate_qrcode(item_code, qr_path)
        qr_files.append(qr_path)
        db.add(
            InventoryItem(
                item_code=item_code,
                qrcode=item_code,
                qrcode_image=qr_image,
                part_id=item.part_id,
                warehouse_id=order.warehouse_id,
                location_id=item.location_id,
                unit_cost=unit_cost,
                status=InventoryItemStatus.IN_STOCK,
                in_at=now,
                remark=f"盘点盘盈 {order.order_no}",
                created_by=current_user_id,
                updated_by=current_user_id,
            )
        )

    inventory.quantity = after_qty
    inventory.item_count = (inventory.item_count or 0) + gain_qty
    inventory.updated_by = current_user_id
    _add_transaction(
        db,
        order,
        item,
        biz_type=BizType.ADJUST_IN,
        change_qty=item.diff_qty,
        before_qty=before_qty,
        after_qty=after_qty,
        unit_cost=unit_cost,
        current_user_id=current_user_id,
    )
    # 让同批次后续盘盈明细取号时能看到已生成编码，避免流水号重复
    await db.flush()


def _apply_untracked_diff(
    db: AsyncSession,
    order: StocktakeOrder,
    item: StocktakeOrderItem,
    inventory: Inventory,
    before_qty: Decimal,
    after_qty: Decimal,
    diff_qty: Decimal,
    current_user_id: int,
) -> None:
    """非逐件追踪：只调整库存汇总数量，库存件数不变。"""
    inventory.quantity = after_qty
    inventory.updated_by = current_user_id
    _add_transaction(
        db,
        order,
        item,
        biz_type=BizType.ADJUST_IN if diff_qty > 0 else BizType.ADJUST_OUT,
        change_qty=diff_qty,
        before_qty=before_qty,
        after_qty=after_qty,
        unit_cost=inventory.avg_cost,
        current_user_id=current_user_id,
    )


async def _apply_stocktake_items(
    db: AsyncSession,
    order: StocktakeOrder,
    items: list[StocktakeOrderItem],
    parts: dict[int, Part],
    current_user_id: int,
    now: datetime,
    qr_files: list[Path],
) -> None:
    """逐条明细应用盘点差异：库存汇总、库存件实例、二维码、库存流水。"""
    inventory_cache: dict[tuple[int, int, int | None], Inventory] = {}
    inventory_items = await _load_inventory_items_for_update(
        db, [item.inventory_item_id for item in items]
    )

    # 统一加锁顺序：先按 part_id 升序锁配件行（串行化库存行创建），
    # 再按 配件 / 库位 / 库存件 / 明细 顺序处理，避免并发盘点互相死锁。
    part_ids = sorted(parts.keys())
    await db.execute(
        select(Part.id)
        .where(Part.id.in_(part_ids))
        .order_by(Part.id.asc())
        .with_for_update()
    )
    locked_items = sorted(
        items,
        key=lambda detail: (
            detail.part_id,
            detail.location_id or 0,
            detail.inventory_item_id or 0,
            detail.id,
        ),
    )

    for item in locked_items:
        part = parts[item.part_id]
        book_qty = _qty(item.book_qty)
        actual_qty = _qty(item.actual_qty)
        diff_qty = _calc_diff(actual_qty, book_qty)

        # 统一回写归一化后的账面 / 实盘 / 差异，便于前端直接展示
        item.book_qty = book_qty
        item.actual_qty = actual_qty
        item.diff_qty = diff_qty
        item.updated_by = current_user_id

        if diff_qty == 0:
            continue

        inventory = await _lock_inventory(
            db,
            inventory_cache,
            part_id=item.part_id,
            warehouse_id=order.warehouse_id,
            location_id=item.location_id,
            current_user_id=current_user_id,
        )
        before_qty = _qty(inventory.quantity)
        after_qty = before_qty + diff_qty
        if after_qty < 0:
            raise BizException(
                code=409,
                message=f"配件 {part.part_name} 盘亏后库存为负数，请核对实盘数量",
            )

        if item.inventory_item_id is not None:
            # 逐件追踪的实例行：实盘 0 表示该件盘亏
            _apply_tracked_loss(
                db,
                order,
                item,
                part,
                inventory,
                inventory_items.get(item.inventory_item_id),
                before_qty,
                after_qty,
                current_user_id,
            )
        elif part.track_by_item == 1:
            # 逐件追踪的盘盈行：按实盘数量补建实例
            await _apply_tracked_gain(
                db,
                order,
                item,
                part,
                inventory,
                before_qty,
                after_qty,
                current_user_id,
                now,
                qr_files,
            )
        else:
            # 非逐件追踪：只调整库存汇总数量，库存件数不变
            _apply_untracked_diff(
                db,
                order,
                item,
                inventory,
                before_qty,
                after_qty,
                diff_qty,
                current_user_id,
            )


def _is_retryable_conflict(exc: IntegrityError) -> bool:
    """唯一索引冲突（并发取到相同编码 / 同时创建库存行）可以重试。"""
    message = str(getattr(exc, "orig", exc))
    return "Duplicate entry" in message or any(
        key in message for key in (INVENTORY_UNIQUE_KEY, ITEM_CODE_UNIQUE_KEY)
    )


async def _finish_once(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> None:
    """单次完成盘点（一整个事务）：成功提交，失败回滚并清理二维码文件。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != StocktakeStatus.COUNTING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅盘点中状态的盘点单可完成盘点",
        )

    items = await _load_items_for_update(db, order.id)
    if not items:
        raise BizException(code=400, message="盘点单明细为空，无法完成盘点")

    parts = await _load_parts(db, [item.part_id for item in items])

    now = datetime.now()
    qr_files: list[Path] = []
    try:
        await _apply_stocktake_items(
            db, order, items, parts, current_user_id, now, qr_files
        )

        order.status = StocktakeStatus.COMPLETED
        order.audit_user_id = current_user_id
        order.stocktake_at = now
        order.updated_by = current_user_id

        await db.commit()
    except Exception:
        await db.rollback()
        _remove_qrcode_files(qr_files)
        raise


async def finish_stocktake_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> StocktakeOrderDetailVO:
    """完成盘点：2 盘点中 → 3 已完成，并按差异调整库存。

    整个处理在一个事务内完成：库存汇总、库存件实例、二维码、库存流水、
    单据状态任一失败全部回滚；库存行加 `FOR UPDATE` 行锁避免并发覆盖。
    并发取号 / 建库存行遇到唯一索引冲突时自动重试（最多 3 次）。
    """
    for attempt in range(1, FINISH_MAX_RETRY + 1):
        try:
            await _finish_once(db, order_id, current_user_id)
            break
        except IntegrityError as exc:
            # _finish_once 已回滚并清理二维码文件，重新取号 / 重新创建库存行
            if attempt < FINISH_MAX_RETRY and _is_retryable_conflict(exc):
                continue
            raise BizException(code=409, message="盘点处理冲突，请重试") from exc

    return await get_stocktake_order(db, order_id)


async def cancel_stocktake_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> StocktakeOrderDetailVO:
    """作废盘点单：1 草稿 / 2 盘点中 → 4 已作废（不调整库存）。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status not in (StocktakeStatus.DRAFT, StocktakeStatus.COUNTING):
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿或盘点中状态的盘点单可作废",
        )

    order.status = StocktakeStatus.CANCELLED
    order.updated_by = current_user_id
    await db.commit()
    return await get_stocktake_order(db, order.id)
