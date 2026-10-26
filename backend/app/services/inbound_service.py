"""入库单业务逻辑：新建、编辑草稿、提交审核、作废、分页查询与详情。

约定：
- 单号规则 `IN + yyyyMMdd + 6 位流水`，取当日最大单号 +1 生成；
  并发下依赖 `uk_order_no` 唯一索引，冲突时自动重新取号并重试。
- 明细的 `track_by_item` 一律以配件主数据 `part.track_by_item` 为准，
  前端传入值不采信，避免审核时生成库存件的规则错乱。
- 状态流转：1 草稿 → 2 待审 → 3 已入库；草稿 / 待审 → 4 作废。
- 审核通过（2 → 3）在一个事务内完成：加库存行锁 → 更新库存汇总
  （数量 / 在库实例数 / 移动加权平均成本）→ 逐件追踪配件生成库存件实例与二维码
  → 写库存流水，任意一步失败全部回滚，并清理已落盘的二维码图片。
- 单据与明细均逻辑删除；created_by / updated_by 取当前登录用户。
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import (
    InboundOrder,
    InboundOrderItem,
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    Supplier,
    SysUser,
    Warehouse,
    WarehouseLocation,
)
from app.models.enums import (
    BizType,
    CommonStatus,
    InboundType,
    InventoryItemStatus,
    OrderStatus,
    RefType,
)
from app.schemas.common import PageResult
from app.schemas.inbound import (
    InboundOrderCreate,
    InboundOrderDetailVO,
    InboundOrderItemCreate,
    InboundOrderItemVO,
    InboundOrderQuery,
    InboundOrderUpdate,
    InboundOrderVO,
)
from app.services.code_generator import (
    ITEM_CODE_SEQUENCE,
    SequenceExhausted,
    generate_item_code,
    next_sequences,
)
from app.services.qrcode_service import generate_qrcode, qrcode_file_path

__all__ = [
    "approve_inbound_order",
    "cancel_inbound_order",
    "create_inbound_order",
    "get_inbound_order",
    "list_inbound_orders",
    "submit_inbound_order",
    "update_inbound_order",
]

# 业务错误码：单据状态不允许操作（见 docs/backend-requirements.md 错误码约定）
ORDER_STATUS_NOT_ALLOWED: int = 3001

# 单号前缀与并发重试次数
ORDER_NO_PREFIX: str = "IN"
ORDER_NO_MAX_RETRY: int = 5
# 当日流水上限：6 位
ORDER_NO_MAX_SEQ: int = 999999

# 金额统一保留两位小数（四舍五入）
AMOUNT_QUANT: Decimal = Decimal("0.01")
# 成本统一保留四位小数（四舍五入）
COST_QUANT: Decimal = Decimal("0.0001")
# 审核入库并发冲突（库存行/库存件编码唯一索引）最大重试次数
APPROVE_MAX_RETRY: int = 3
# 唯一索引名（用于识别可重试的并发冲突）
INVENTORY_UNIQUE_KEY: str = "uk_part_warehouse_location"
ITEM_CODE_UNIQUE_KEY: str = "uk_item_code"

# 允许的入库类型
INBOUND_TYPES: frozenset[str] = frozenset(
    {
        InboundType.PURCHASE,
        InboundType.RETURN,
        InboundType.TRANSFER,
        InboundType.ADJUST,
    }
)


# ---------------------------------------------------------------- 内部工具
async def _get_warehouse_or_404(db: AsyncSession, warehouse_id: int) -> Warehouse:
    """取启用中的仓库，不存在抛 404，已停用抛 400。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message="仓库不存在")
    if warehouse.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"仓库 {warehouse.name} 已停用")
    return warehouse


async def _ensure_supplier_exists(db: AsyncSession, supplier_id: int | None) -> None:
    """校验供应商存在（未传表示无供应商）。"""
    if supplier_id is None:
        return
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None or supplier.is_deleted:
        raise BizException(code=404, message="供应商不存在")


async def _ensure_user_exists(db: AsyncSession, user_id: int) -> None:
    """校验经办人存在且启用。"""
    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message="经办人不存在")
    if user.status != CommonStatus.ENABLED:
        raise BizException(code=400, message="经办人已停用")


def _ensure_inbound_type(inbound_type: str) -> None:
    """校验入库类型取值。"""
    if inbound_type not in INBOUND_TYPES:
        raise BizException(
            code=400,
            message="入库类型不正确，可选 PURCHASE/RETURN/TRANSFER/ADJUST",
        )


async def _ensure_locations(
    db: AsyncSession,
    warehouse_id: int,
    location_ids: list[int | None],
) -> None:
    """校验库位存在且属于所选仓库（未指定库位表示放在仓库级）。"""
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
        raise BizException(
            code=400,
            message=f"库位 {location.location_code} 已停用",
        )


async def _ensure_order_locations(
    db: AsyncSession,
    order_id: int,
    warehouse_id: int,
) -> None:
    """编辑草稿变更仓库但未重提明细时，校验原明细库位属于新仓库。"""
    location_ids = (
        (
            await db.execute(
                select(InboundOrderItem.location_id)
                .where(
                    InboundOrderItem.order_id == order_id,
                    InboundOrderItem.is_deleted == 0,
                    InboundOrderItem.location_id.is_not(None),
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    if not location_ids:
        return

    try:
        await _ensure_locations(db, warehouse_id, list(location_ids))
    except BizException as exc:
        if exc.code == 400 and "不属于" in exc.message:
            raise BizException(
                code=400,
                message="仓库已变更，原明细库位不属于新仓库，请同时提交明细",
            ) from exc
        raise


async def _load_parts(
    db: AsyncSession,
    part_ids: list[int],
) -> dict[int, Part]:
    """批量加载配件并校验：不存在 404、已停用 400。"""
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

    disabled = sorted(
        part.id for part in parts.values() if part.status != CommonStatus.ENABLED
    )
    if disabled:
        raise BizException(
            code=400,
            message=f"配件已停用: {parts[disabled[0]].part_name}",
        )
    return parts


async def _build_item_rows(
    db: AsyncSession,
    items: list[InboundOrderItemCreate],
    warehouse_id: int,
) -> list[dict[str, Any]]:
    """把提交的明细转换为入库明细行字段，并补齐配件主数据。"""
    if not items:
        return []

    parts = await _load_parts(db, [item.part_id for item in items])
    await _ensure_locations(db, warehouse_id, [item.location_id for item in items])

    rows: list[dict[str, Any]] = []
    for item in items:
        part = parts[item.part_id]

        # 逐件追踪的配件必须按整数件入库，否则无法生成库存件实例
        if (
            part.track_by_item == 1
            and item.quantity != item.quantity.to_integral_value()
        ):
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，数量必须为整数",
            )
        if (
            item.production_date is not None
            and item.expire_date is not None
            and item.expire_date < item.production_date
        ):
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 到期日期不能早于生产日期",
            )

        amount = item.amount
        if amount is None:
            amount = (item.quantity * item.unit_price).quantize(
                AMOUNT_QUANT, rounding=ROUND_HALF_UP
            )

        rows.append(
            {
                "part_id": part.id,
                "quantity": item.quantity,
                "unit": item.unit or part.unit,
                "unit_price": item.unit_price,
                "amount": amount,
                # 是否逐件追踪以配件主数据为准
                "track_by_item": part.track_by_item,
                "batch_no": item.batch_no,
                "production_date": item.production_date,
                "expire_date": item.expire_date,
                "location_id": item.location_id,
                "scan_code": item.scan_code,
                "remark": item.remark,
            }
        )
    return rows


def _sum_amount(rows: list[dict[str, Any]]) -> Decimal:
    """汇总明细金额（无明细时为 0.00）。"""
    total = sum((row["amount"] for row in rows), Decimal(0))
    return total.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP)


def _today_prefix() -> str:
    """当日单号前缀：IN + yyyyMMdd。"""
    return f"{ORDER_NO_PREFIX}{datetime.now():%Y%m%d}"


async def _next_order_no(db: AsyncSession) -> str:
    """按当日最大单号 +1 生成单号（含已作废/已删除单据，避免复用）。"""
    prefix = _today_prefix()
    max_no = (
        await db.execute(
            select(func.max(InboundOrder.order_no)).where(
                InboundOrder.order_no.like(f"{prefix}%")
            )
        )
    ).scalar_one_or_none()

    seq = 1
    if max_no:
        tail = max_no[len(prefix) :]
        if tail.isdigit():
            seq = int(tail) + 1
    if seq > ORDER_NO_MAX_SEQ:
        raise BizException(code=409, message="当日入库单号已用尽，请联系管理员")
    return f"{prefix}{seq:06d}"


async def _get_order_or_404(
    db: AsyncSession,
    order_id: int,
    *,
    for_update: bool = False,
) -> InboundOrder:
    """取入库单；状态流转类操作加行锁，避免并发重复提交/作废。"""
    stmt = select(InboundOrder).where(
        InboundOrder.id == order_id,
        InboundOrder.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise BizException(code=404, message="入库单不存在")
    return order


def _to_item_vo(item: InboundOrderItem, part: Part | None = None) -> InboundOrderItemVO:
    """明细 ORM 转 VO，补齐配件编码/名称/规格。"""
    vo = InboundOrderItemVO.model_validate(item)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
    return vo


async def _list_items(
    db: AsyncSession,
    order_id: int,
) -> list[InboundOrderItemVO]:
    """入库单明细（含配件编码/名称/规格）。"""
    stmt = (
        select(InboundOrderItem, Part)
        .outerjoin(Part, Part.id == InboundOrderItem.part_id)
        .where(
            InboundOrderItem.order_id == order_id,
            InboundOrderItem.is_deleted == 0,
        )
        .order_by(InboundOrderItem.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [_to_item_vo(item, part) for item, part in rows]


# ---------------------------------------------------------------- 查询
async def list_inbound_orders(
    db: AsyncSession,
    query: InboundOrderQuery,
) -> PageResult[InboundOrderVO]:
    """入库单分页查询（关键字、供应商、仓库、类型、状态、经办人、创建时间）。"""
    conditions = [InboundOrder.is_deleted == 0]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                InboundOrder.order_no.like(keyword),
                InboundOrder.remark.like(keyword),
            )
        )
    if query.order_no:
        conditions.append(InboundOrder.order_no.like(f"%{query.order_no.strip()}%"))
    if query.supplier_id is not None:
        conditions.append(InboundOrder.supplier_id == query.supplier_id)
    if query.warehouse_id is not None:
        conditions.append(InboundOrder.warehouse_id == query.warehouse_id)
    if query.inbound_type:
        conditions.append(InboundOrder.inbound_type == query.inbound_type)
    if query.status is not None:
        conditions.append(InboundOrder.status == query.status)
    if query.operator_id is not None:
        conditions.append(InboundOrder.operator_id == query.operator_id)
    if query.start_time is not None:
        conditions.append(InboundOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(InboundOrder.created_at <= query.end_time)

    total = (
        await db.execute(
            select(func.count()).select_from(InboundOrder).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(InboundOrder, Warehouse.name, Supplier.name)
        .outerjoin(Warehouse, Warehouse.id == InboundOrder.warehouse_id)
        .outerjoin(Supplier, Supplier.id == InboundOrder.supplier_id)
        .where(*conditions)
        .order_by(InboundOrder.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    result: list[InboundOrderVO] = []
    for order, warehouse_name, supplier_name in rows:
        vo = InboundOrderVO.model_validate(order)
        vo.warehouse_name = warehouse_name
        vo.supplier_name = supplier_name
        result.append(vo)

    return PageResult[InboundOrderVO](
        list=result,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_inbound_order(
    db: AsyncSession,
    order_id: int,
) -> InboundOrderDetailVO:
    """入库单详情（含明细、仓库名、供应商名）。"""
    stmt = (
        select(InboundOrder, Warehouse.name, Supplier.name)
        .outerjoin(Warehouse, Warehouse.id == InboundOrder.warehouse_id)
        .outerjoin(Supplier, Supplier.id == InboundOrder.supplier_id)
        .where(
            InboundOrder.id == order_id,
            InboundOrder.is_deleted == 0,
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="入库单不存在")

    order, warehouse_name, supplier_name = row
    detail = InboundOrderDetailVO.model_validate(order)
    detail.warehouse_name = warehouse_name
    detail.supplier_name = supplier_name
    detail.items = await _list_items(db, order.id)
    return detail


# ---------------------------------------------------------------- 写操作
async def _insert_order_with_retry(
    db: AsyncSession,
    payload: InboundOrderCreate,
    rows: list[dict[str, Any]],
    total_amount: Decimal,
    operator_id: int,
    current_user_id: int,
) -> InboundOrder:
    """插入主单与明细；单号冲突时重新取号重试（唯一索引兜底保证并发安全）。"""
    for attempt in range(1, ORDER_NO_MAX_RETRY + 1):
        order = InboundOrder(
            order_no=await _next_order_no(db),
            supplier_id=payload.supplier_id,
            warehouse_id=payload.warehouse_id,
            inbound_type=payload.inbound_type,
            total_amount=total_amount,
            status=OrderStatus.DRAFT,
            operator_id=operator_id,
            remark=payload.remark,
            created_by=current_user_id,
        )
        db.add(order)
        try:
            await db.flush()
            for row in rows:
                db.add(
                    InboundOrderItem(
                        order_id=order.id,
                        created_by=current_user_id,
                        **row,
                    )
                )
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # 仅单号重复可重试，其它完整性错误直接暴露
            if attempt < ORDER_NO_MAX_RETRY and "uk_order_no" in str(exc.orig):
                continue
            raise BizException(code=409, message="入库单号生成冲突，请重试") from exc
        return order

    raise BizException(code=409, message="入库单号生成冲突，请重试")


async def create_inbound_order(
    db: AsyncSession,
    payload: InboundOrderCreate,
    current_user_id: int,
) -> InboundOrderDetailVO:
    """新建入库单（草稿）：单号自动生成，明细 `track_by_item` 取配件主数据。"""
    _ensure_inbound_type(payload.inbound_type)
    await _get_warehouse_or_404(db, payload.warehouse_id)
    await _ensure_supplier_exists(db, payload.supplier_id)

    operator_id = payload.operator_id or current_user_id
    if operator_id != current_user_id:
        await _ensure_user_exists(db, operator_id)

    rows = await _build_item_rows(db, payload.items, payload.warehouse_id)
    order = await _insert_order_with_retry(
        db,
        payload,
        rows,
        _sum_amount(rows),
        operator_id,
        current_user_id,
    )
    return await get_inbound_order(db, order.id)


async def update_inbound_order(
    db: AsyncSession,
    order_id: int,
    payload: InboundOrderUpdate,
    current_user_id: int,
) -> InboundOrderDetailVO:
    """编辑草稿；传 items 时整体替换原明细（旧明细逻辑删除）并重算总金额。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.DRAFT:
        raise BizException(code=ORDER_STATUS_NOT_ALLOWED, message="仅草稿状态可编辑")

    data = payload.model_dump(exclude_unset=True, exclude={"items"})

    if data.get("inbound_type") is not None:
        _ensure_inbound_type(data["inbound_type"])
    if data.get("warehouse_id") is not None:
        await _get_warehouse_or_404(db, data["warehouse_id"])
    if data.get("supplier_id") is not None:
        await _ensure_supplier_exists(db, data["supplier_id"])
    operator_id = data.get("operator_id")
    if operator_id is not None and operator_id != current_user_id:
        await _ensure_user_exists(db, operator_id)

    new_warehouse_id = data.get("warehouse_id")
    warehouse_changed = (
        new_warehouse_id is not None and new_warehouse_id != order.warehouse_id
    )

    # warehouse_id / inbound_type 为非空列，显式传 null 时忽略
    for field, value in data.items():
        if value is None and field in {"warehouse_id", "inbound_type"}:
            continue
        setattr(order, field, value)
    order.updated_by = current_user_id

    if payload.items is not None:
        rows = await _build_item_rows(db, payload.items, order.warehouse_id)
        await db.execute(
            update(InboundOrderItem)
            .where(
                InboundOrderItem.order_id == order.id,
                InboundOrderItem.is_deleted == 0,
            )
            .values(is_deleted=1, updated_by=current_user_id)
        )
        for row in rows:
            db.add(
                InboundOrderItem(
                    order_id=order.id,
                    created_by=current_user_id,
                    **row,
                )
            )
        order.total_amount = _sum_amount(rows)
    elif warehouse_changed:
        # 未重提明细时原明细库位可能属于旧仓库，提前拦截避免审核写错库存
        await _ensure_order_locations(db, order.id, new_warehouse_id)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="入库单更新失败，请重试") from exc
    return await get_inbound_order(db, order.id)


async def submit_inbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> InboundOrderDetailVO:
    """提交审核：1 草稿 → 2 待审；提交前校验明细非空且配件仍然有效。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.DRAFT:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿状态可提交审核",
        )

    items = (
        (
            await db.execute(
                select(InboundOrderItem).where(
                    InboundOrderItem.order_id == order.id,
                    InboundOrderItem.is_deleted == 0,
                )
            )
        )
        .scalars()
        .all()
    )
    if not items:
        raise BizException(code=400, message="入库单明细不能为空，无法提交")

    # 草稿期间配件可能被删除/停用，提交前再校验一次
    parts = await _load_parts(db, [item.part_id for item in items])
    for item in items:
        track_by_item = parts[item.part_id].track_by_item
        if item.track_by_item != track_by_item:
            item.track_by_item = track_by_item
            item.updated_by = current_user_id

    order.status = OrderStatus.PENDING
    order.operator_id = order.operator_id or current_user_id
    order.updated_by = current_user_id
    await db.commit()
    return await get_inbound_order(db, order.id)


async def cancel_inbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> InboundOrderDetailVO:
    """作废入库单：草稿 / 待审 → 4 作废；已入库单据不允许作废。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status not in {OrderStatus.DRAFT, OrderStatus.PENDING}:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="当前状态不允许作废",
        )

    order.status = OrderStatus.CANCELLED
    order.updated_by = current_user_id
    await db.commit()
    return await get_inbound_order(db, order.id)


# ---------------------------------------------------------------- 审核通过（入库）
def _calc_avg_cost(
    before_qty: Decimal,
    before_avg: Decimal,
    in_qty: Decimal,
    in_price: Decimal,
) -> Decimal:
    """移动加权平均成本：(原数量×原均价 + 入库数量×入库单价) ÷ 入库后总数量。"""
    total_qty = before_qty + in_qty
    if total_qty <= 0:
        return Decimal(0).quantize(COST_QUANT)
    return ((before_qty * before_avg + in_qty * in_price) / total_qty).quantize(
        COST_QUANT, rounding=ROUND_HALF_UP
    )


async def _lock_inventory(
    db: AsyncSession,
    cache: dict[tuple[int, int, int | None], Inventory],
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
    current_user_id: int,
) -> Inventory:
    """取 配件+仓库+库位 的库存行并加 `FOR UPDATE` 行锁，不存在则创建。

    - 行锁保证并发审核时库存数量/成本不会被覆盖写；
    - 同一事务内多条明细命中同一库存行时复用缓存，避免重复创建；
    - 并发创建同一库存行由调用方的配件行锁串行化（MySQL 唯一索引不约束
      NULL 库位）；库存件编码冲突由 `uk_item_code` 兜底并触发外层重试。
    """
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
            quantity=Decimal("0.00"),
            item_count=0,
            locked_qty=Decimal("0.00"),
            avg_cost=Decimal("0.0000"),
            created_by=current_user_id,
        )
        db.add(inventory)
        # 立即 flush：让本事务后续明细可查到该行，同时尽早暴露唯一索引冲突
        await db.flush()
    elif inventory.is_deleted:
        # 历史逻辑删除的库存行直接复用，避免与唯一索引冲突
        inventory.is_deleted = 0
        inventory.quantity = Decimal("0.00")
        inventory.item_count = 0
        inventory.locked_qty = Decimal("0.00")
        inventory.avg_cost = Decimal("0.0000")
        inventory.updated_by = current_user_id

    cache[key] = inventory
    return inventory


async def _load_items_for_update(
    db: AsyncSession,
    order_id: int,
) -> list[InboundOrderItem]:
    """加载入库明细并加行锁（审核期间不允许并发修改明细）。"""
    stmt = (
        select(InboundOrderItem)
        .where(
            InboundOrderItem.order_id == order_id,
            InboundOrderItem.is_deleted == 0,
        )
        .order_by(InboundOrderItem.id.asc())
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


def _remove_qrcode_files(paths: list[Path]) -> None:
    """事务回滚后清理已落盘的二维码图片，避免产生孤儿文件。"""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # 清理失败不影响主流程，最多留下无用图片
            continue


async def _apply_inbound_items(
    db: AsyncSession,
    order: InboundOrder,
    items: list[InboundOrderItem],
    parts: dict[int, Part],
    current_user_id: int,
    now: datetime,
    qr_files: list[Path],
) -> None:
    """逐条明细落库：库存汇总、库存件实例、二维码、库存流水。

    生成成功的二维码路径会追加到 `qr_files`，由调用方在回滚时清理。
    """
    inventory_cache: dict[tuple[int, int, int | None], Inventory] = {}

    # 统一加锁顺序：先按 part_id 升序锁配件行，再按 配件/库位/明细 顺序处理明细。
    # 1) MySQL 唯一索引不对 `location_id IS NULL` 去重，并发审核可能同时创建出
    #    两条「仓库级」库存行，需靠配件行锁串行化创建动作；
    # 2) 多配件入库统一加锁顺序，避免并发审核互相等待造成死锁。
    part_ids = sorted({item.part_id for item in items})
    await db.execute(
        select(Part.id)
        .where(Part.id.in_(part_ids))
        .order_by(Part.id.asc())
        .with_for_update()
    )
    locked_items = sorted(
        items,
        key=lambda detail: (detail.part_id, detail.location_id or 0, detail.id),
    )

    for item in locked_items:
        part = parts[item.part_id]
        if item.quantity <= 0:
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 入库数量必须大于 0",
            )

        # 是否逐件追踪以配件主数据为准（提交后主数据仍可能被修改）
        track_by_item = 1 if part.track_by_item == 1 else 0
        if track_by_item and item.quantity != item.quantity.to_integral_value():
            raise BizException(
                code=400,
                message=f"配件 {part.part_name} 按件追踪，数量必须为整数",
            )
        if item.track_by_item != track_by_item:
            item.track_by_item = track_by_item

        # 库存汇总行：不存在则创建，存在则加行锁
        inventory = await _lock_inventory(
            db,
            inventory_cache,
            part_id=item.part_id,
            warehouse_id=order.warehouse_id,
            location_id=item.location_id,
            current_user_id=current_user_id,
        )

        unit_price = item.unit_price or Decimal(0)

        # 逐件追踪：按数量生成 N 条库存件实例，每条一个唯一编码 + 二维码
        if track_by_item:
            qty = int(item.quantity)
            try:
                sequences = await next_sequences(db, ITEM_CODE_SEQUENCE, qty, at=now)
            except SequenceExhausted as exc:
                raise BizException(
                    code=409,
                    message="当日库存件编码已用尽，请联系管理员",
                ) from exc

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
                        batch_no=item.batch_no,
                        production_date=item.production_date,
                        expire_date=item.expire_date,
                        unit_cost=unit_price,
                        status=InventoryItemStatus.IN_STOCK,
                        inbound_item_id=item.id,
                        in_at=now,
                        created_by=current_user_id,
                    )
                )

            item.generate_item_qty = qty
            item.generated = 1
            inventory.item_count = (inventory.item_count or 0) + qty
            # 让同批次后续明细取号时能看到已生成编码，避免流水号重复
            await db.flush()
        else:
            # 非逐件追踪：不生成实例，明细标记与实际保持一致
            item.generate_item_qty = 0
            item.generated = 0

        # 更新库存数量与移动加权平均成本
        before_qty = inventory.quantity or Decimal(0)
        inventory.quantity = before_qty + item.quantity
        inventory.avg_cost = _calc_avg_cost(
            before_qty,
            inventory.avg_cost or Decimal(0),
            item.quantity,
            unit_price,
        )
        inventory.last_in_at = now
        inventory.updated_by = current_user_id
        item.updated_by = current_user_id

        # 写库存流水（按明细一条，库存件实例通过 inbound_item_id 关联）
        db.add(
            InventoryTransaction(
                part_id=item.part_id,
                inventory_item_id=None,
                warehouse_id=order.warehouse_id,
                location_id=item.location_id,
                biz_type=BizType.IN,
                change_qty=item.quantity,
                before_qty=before_qty,
                after_qty=inventory.quantity,
                unit_cost=unit_price,
                ref_type=RefType.INBOUND,
                ref_id=order.id,
                ref_no=order.order_no,
                batch_no=item.batch_no,
                scan_code=item.scan_code,
                operator_id=current_user_id,
                created_by=current_user_id,
            )
        )


def _is_retryable_conflict(exc: IntegrityError) -> bool:
    """唯一索引冲突（并发取到相同编码 / 同时创建库存行）可以重试。"""
    message = str(getattr(exc, "orig", exc))
    return "Duplicate entry" in message or any(
        key in message for key in (INVENTORY_UNIQUE_KEY, ITEM_CODE_UNIQUE_KEY)
    )


async def _approve_once(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> None:
    """单次审核入库（一整个事务）：成功提交，失败回滚并清理二维码文件。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.PENDING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅待审状态可审核入库",
        )

    items = await _load_items_for_update(db, order.id)
    if not items:
        raise BizException(code=400, message="入库单明细为空，无法审核")

    parts = await _load_parts(db, [item.part_id for item in items])

    now = datetime.now()
    qr_files: list[Path] = []
    try:
        await _apply_inbound_items(
            db, order, items, parts, current_user_id, now, qr_files
        )

        order.status = OrderStatus.COMPLETED
        order.audit_user_id = current_user_id
        order.audit_at = now
        order.inbound_at = now
        order.updated_by = current_user_id

        await db.commit()
    except Exception:
        await db.rollback()
        _remove_qrcode_files(qr_files)
        raise


async def approve_inbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> InboundOrderDetailVO:
    """审核通过入库单：2 待审 → 3 已入库。

    整个审核过程在一个事务内完成：库存汇总、库存件实例、二维码、库存流水、
    单据状态任一失败全部回滚；库存行加 `FOR UPDATE` 行锁避免并发覆盖。
    并发取号/建库存行遇到唯一索引冲突时自动重试（最多 3 次）。
    """
    for attempt in range(1, APPROVE_MAX_RETRY + 1):
        try:
            await _approve_once(db, order_id, current_user_id)
            break
        except IntegrityError as exc:
            # _approve_once 已回滚并清理二维码文件，重新取号 / 重新创建库存行
            if attempt < APPROVE_MAX_RETRY and _is_retryable_conflict(exc):
                continue
            raise BizException(code=409, message="入库处理冲突，请重试") from exc

    return await get_inbound_order(db, order_id)
