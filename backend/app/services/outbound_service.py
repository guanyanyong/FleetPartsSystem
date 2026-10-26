"""出库单业务逻辑：新建、编辑草稿、提交审核、作废、分页查询、详情与审核出库。

约定：
- 单号规则 `OUT + yyyyMMdd + 6 位流水`，复用 `app.services.code_generator` 取号；
  并发下依赖 `uk_order_no` 唯一索引，冲突时自动重新取号并重试。
- 明细是否按件追踪以配件主数据 `part.track_by_item` 为准，前端传入值不采信。
  按件追踪的配件在提交审核时必须指定 `inventory_item_id`，且一条明细只对应
  一个库存件（数量 1），避免审核时 `inventory.item_count` 扣减与实例不匹配。
- 指定 `inventory_item_id` 时，库位 / 批次 / 单位成本优先取库存件实例上的值，
  保证出库扣减的是实例实际所在的库存行，避免扣错仓库库位。
- 状态流转：1 草稿 → 2 待审 → 3 已出库；草稿 / 待审 → 4 作废。
- 审核通过（2 → 3）在一个事务内完成：锁定单据与明细 → 校验库存件在库并回填
  出库信息 → 扣减库存数量与在库实例数 → 写库存流水 → 关联工单领料，
  任意一步失败全部回滚。
- 单据与明细均逻辑删除；created_by / updated_by 取当前登录用户。
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    OutboundOrder,
    OutboundOrderItem,
    Part,
    SysUser,
    Vehicle,
    Warehouse,
    WarehouseLocation,
    WorkOrder,
    WorkOrderPart,
)
from app.models.enums import (
    BizType,
    CommonStatus,
    InventoryItemStatus,
    OrderStatus,
    OutboundType,
    RefType,
    ScanType,
)
from app.schemas.common import PageResult
from app.schemas.outbound import (
    OutboundOrderCreate,
    OutboundOrderDetailVO,
    OutboundOrderItemCreate,
    OutboundOrderItemVO,
    OutboundOrderQuery,
    OutboundOrderUpdate,
    OutboundOrderVO,
)
from app.services.code_generator import (
    OUTBOUND_SEQUENCE,
    SequenceExhausted,
    generate_outbound_no,
    next_sequence,
)

__all__ = [
    "approve_outbound_order",
    "cancel_outbound_order",
    "create_outbound_order",
    "get_outbound_order",
    "list_outbound_orders",
    "submit_outbound_order",
    "update_outbound_order",
]

# 业务错误码（见 docs/backend-requirements.md 错误码约定）
ORDER_STATUS_NOT_ALLOWED: int = 3001
INSUFFICIENT_STOCK: int = 2001
ITEM_NOT_IN_STOCK: int = 2002
ITEM_ALREADY_OUT: int = 2003
ITEM_LOCKED: int = 2004

# 单号并发重试次数
ORDER_NO_MAX_RETRY: int = 5

# 金额统一保留两位小数（四舍五入）
AMOUNT_QUANT: Decimal = Decimal("0.01")

# 允许的出库类型
OUTBOUND_TYPES: frozenset[str] = frozenset(
    {
        OutboundType.REPAIR,
        OutboundType.SALE,
        OutboundType.RETURN,
        OutboundType.TRANSFER,
        OutboundType.SCRAP,
    }
)

# 允许的扫码类型
SCAN_TYPES: frozenset[str] = frozenset(
    {ScanType.BARCODE, ScanType.QRCODE, ScanType.MANUAL}
)

# 占用库存件的有效单据状态：草稿 / 待审单据中的库存件视为已占用，
# 防止同一件被多张未完成单据重复出库
RESERVING_ORDER_STATUSES: tuple[int, ...] = (OrderStatus.DRAFT, OrderStatus.PENDING)


# ---------------------------------------------------------------- 内部工具
async def _get_warehouse_or_404(db: AsyncSession, warehouse_id: int) -> Warehouse:
    """取启用中的仓库，不存在抛 404，已停用抛 400。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message="仓库不存在")
    if warehouse.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"仓库 {warehouse.name} 已停用")
    return warehouse


async def _ensure_user_exists(
    db: AsyncSession,
    user_id: int | None,
    label: str = "用户",
) -> None:
    """校验用户存在且启用（未传表示不设置该人员）。"""
    if user_id is None:
        return
    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message=f"{label}不存在")
    if user.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"{label}已停用")


async def _ensure_vehicle_exists(db: AsyncSession, vehicle_id: int | None) -> None:
    """校验关联车辆存在（未传表示不关联车辆）。"""
    if vehicle_id is None:
        return
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.is_deleted:
        raise BizException(code=404, message="车辆不存在")


async def _ensure_work_order_exists(
    db: AsyncSession,
    work_order_id: int | None,
) -> None:
    """校验关联维修工单存在（未传表示不关联工单）。"""
    if work_order_id is None:
        return
    work_order = await db.get(WorkOrder, work_order_id)
    if work_order is None or work_order.is_deleted:
        raise BizException(code=404, message="维修工单不存在")


def _ensure_outbound_type(outbound_type: str) -> None:
    """校验出库类型取值。"""
    if outbound_type not in OUTBOUND_TYPES:
        raise BizException(
            code=400,
            message="出库类型不正确，可选 REPAIR/SALE/RETURN/TRANSFER/SCRAP",
        )


def _ensure_scan_type(scan_type: str | None) -> None:
    """校验扫码类型取值。"""
    if scan_type is not None and scan_type not in SCAN_TYPES:
        raise BizException(
            code=400,
            message="扫码类型不正确，可选 BARCODE/QRCODE/MANUAL",
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
        raise BizException(
            code=400,
            message=f"库位 {location.location_code} 已停用",
        )


async def _load_parts(
    db: AsyncSession,
    part_ids: list[int],
    *,
    require_enabled: bool = True,
) -> dict[int, Part]:
    """批量加载配件：不存在 404；`require_enabled` 时已停用 400。

    审核出库时传 `require_enabled=False`：草稿提交后配件被停用不应阻塞已
    审批的出库，配件是否追踪仍以主数据为准。
    """
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

    if not require_enabled:
        return parts

    disabled = sorted(
        part.id for part in parts.values() if part.status != CommonStatus.ENABLED
    )
    if disabled:
        raise BizException(
            code=400,
            message=f"配件已停用: {parts[disabled[0]].part_name}",
        )
    return parts


def _ensure_item_available(item: InventoryItem) -> None:
    """校验库存件是否可出库，不可出库时抛对应业务错误码。"""
    if item.status == InventoryItemStatus.OUT:
        raise BizException(
            code=ITEM_ALREADY_OUT,
            message=f"库存件 {item.item_code} 已出库，不能重复出库",
        )
    if item.status == InventoryItemStatus.LOCKED:
        raise BizException(
            code=ITEM_LOCKED,
            message=f"库存件 {item.item_code} 已被锁定，不能出库",
        )
    if item.status == InventoryItemStatus.SCRAPPED:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 已报废，不能出库",
        )
    if item.status == InventoryItemStatus.LOST:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 已盘亏，不能出库",
        )
    if item.status != InventoryItemStatus.IN_STOCK:
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"库存件 {item.item_code} 不在库，不能出库",
        )


def _line_amount(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """明细金额：数量 × 单位成本，保留两位小数。"""
    return (quantity * unit_cost).quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP)


def _sum_amount(rows: list[dict[str, Any]]) -> Decimal:
    """汇总明细金额（无明细时为 0.00）。"""
    total = sum((row["amount"] for row in rows), Decimal(0))
    return total.quantize(AMOUNT_QUANT, rounding=ROUND_HALF_UP)


async def _ensure_items_not_reserved(
    db: AsyncSession,
    item_ids: list[int],
    exclude_order_id: int | None = None,
) -> None:
    """校验库存件未被其它草稿/待审出库单占用。

    数据库对 `outbound_order_item.inventory_item_id` 没有唯一约束（允许一条
    明细多次改绑），这里用查询兜底，避免同一件被两张未完成单据重复领用。
    """
    if not item_ids:
        return

    stmt = (
        select(InventoryItem.item_code, OutboundOrder.order_no)
        .join(
            OutboundOrderItem,
            OutboundOrderItem.inventory_item_id == InventoryItem.id,
        )
        .join(OutboundOrder, OutboundOrder.id == OutboundOrderItem.order_id)
        .where(
            InventoryItem.id.in_(item_ids),
            OutboundOrderItem.is_deleted == 0,
            OutboundOrder.is_deleted == 0,
            OutboundOrder.status.in_(RESERVING_ORDER_STATUSES),
        )
        .limit(1)
    )
    if exclude_order_id is not None:
        stmt = stmt.where(OutboundOrder.id != exclude_order_id)

    row = (await db.execute(stmt)).first()
    if row is not None:
        raise BizException(
            code=ITEM_LOCKED,
            message=f"库存件 {row[0]} 已被出库单 {row[1]} 占用，不能重复出库",
        )


async def _load_inventory_items(
    db: AsyncSession,
    items: Sequence[OutboundOrderItemCreate | OutboundOrderItem],
    warehouse_id: int,
    parts: dict[int, Part],
    exclude_order_id: int | None = None,
    *,
    for_update: bool = False,
) -> dict[int, InventoryItem]:
    """批量加载并校验明细中的库存件实例。

    校验项：实例存在、配件一致、属于出库仓库、状态可出库、同一件不重复、
    按件追踪配件一条明细只能出库一件、未被其它未完成单据占用。
    `for_update=True` 时按主键升序加行锁（审核出库使用，保证锁顺序一致）。
    """
    item_ids = [
        item.inventory_item_id for item in items if item.inventory_item_id is not None
    ]
    if not item_ids:
        return {}

    if len(set(item_ids)) != len(item_ids):
        raise BizException(code=400, message="同一库存件不能重复添加到出库明细")

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
        if part.track_by_item != 1:
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
                message=f"库存件 {inventory_item.item_code} 不在出库仓库",
            )
        if item.quantity != Decimal(1):
            raise BizException(
                code=400,
                message=(
                    f"配件 {part.part_name} 按件追踪，"
                    f"一条明细只能出库一个库存件（数量必须为 1）"
                ),
            )
        _ensure_item_available(inventory_item)

    await _ensure_items_not_reserved(db, item_ids, exclude_order_id)
    return found


async def _build_item_rows(
    db: AsyncSession,
    items: list[OutboundOrderItemCreate],
    warehouse_id: int,
    exclude_order_id: int | None = None,
) -> list[dict[str, Any]]:
    """把提交的明细转换为出库明细行字段，并补齐配件与库存件主数据。"""
    if not items:
        return []

    parts = await _load_parts(db, [item.part_id for item in items])
    inventory_items = await _load_inventory_items(
        db, items, warehouse_id, parts, exclude_order_id
    )

    # 指定库存件时以实例所在库位为准，除此之外仍校验库位合法性
    location_ids: list[int | None] = [item.location_id for item in items]
    location_ids.extend(
        inventory_item.location_id for inventory_item in inventory_items.values()
    )
    await _ensure_locations(db, warehouse_id, location_ids)

    rows: list[dict[str, Any]] = []
    for item in items:
        part = parts[item.part_id]
        _ensure_scan_type(item.scan_type)

        inventory_item = (
            inventory_items.get(item.inventory_item_id)
            if item.inventory_item_id is not None
            else None
        )
        if inventory_item is not None:
            # 按件追踪：成本 / 批次 / 库位 / 扫码内容取实例上的实际值
            unit_cost = item.unit_cost or inventory_item.unit_cost or Decimal(0)
            batch_no = item.batch_no or inventory_item.batch_no
            location_id = inventory_item.location_id
            scan_code: str | None = item.scan_code or inventory_item.item_code
        else:
            unit_cost = item.unit_cost or Decimal(0)
            batch_no = item.batch_no
            location_id = item.location_id
            scan_code = item.scan_code

        amount = item.amount
        if amount is None:
            amount = _line_amount(item.quantity, unit_cost)

        rows.append(
            {
                "part_id": part.id,
                "inventory_item_id": item.inventory_item_id,
                "quantity": item.quantity,
                "unit": item.unit or part.unit,
                "unit_cost": unit_cost,
                "amount": amount,
                "batch_no": batch_no,
                "location_id": location_id,
                "scan_code": scan_code,
                "scan_type": item.scan_type,
                "scan_at": item.scan_at,
                "remark": item.remark,
            }
        )
    return rows


async def _ensure_existing_items_in_warehouse(
    db: AsyncSession,
    order_id: int,
    warehouse_id: int,
) -> None:
    """编辑草稿变更仓库但未重提明细时，校验原明细库位/库存件属于新仓库。"""
    rows = (
        await db.execute(
            select(OutboundOrderItem, InventoryItem)
            .outerjoin(
                InventoryItem,
                InventoryItem.id == OutboundOrderItem.inventory_item_id,
            )
            .where(
                OutboundOrderItem.order_id == order_id,
                OutboundOrderItem.is_deleted == 0,
            )
        )
    ).all()
    if not rows:
        return

    for detail, inventory_item in rows:
        if inventory_item is not None and inventory_item.warehouse_id != warehouse_id:
            raise BizException(
                code=400,
                message=(
                    f"仓库已变更，明细中的库存件 {inventory_item.item_code} "
                    f"不在新仓库，请同时提交明细"
                ),
            )

    try:
        await _ensure_locations(
            db, warehouse_id, [detail.location_id for detail, _ in rows]
        )
    except BizException as exc:
        if exc.code == 400 and "不属于" in exc.message:
            raise BizException(
                code=400,
                message="仓库已变更，原明细库位不属于新仓库，请同时提交明细",
            ) from exc
        raise


# ---------------------------------------------------------------- VO 转换
def _to_item_vo(
    item: OutboundOrderItem,
    part: Part | None = None,
    inventory_item: InventoryItem | None = None,
) -> OutboundOrderItemVO:
    """明细 ORM 转 VO，补齐配件编码/名称/规格与库存件编码。"""
    vo = OutboundOrderItemVO.model_validate(item)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
    if inventory_item is not None:
        vo.item_code = inventory_item.item_code
    return vo


async def _list_items(
    db: AsyncSession,
    order_id: int,
) -> list[OutboundOrderItemVO]:
    """出库单明细（含配件编码/名称/规格、库存件编码）。"""
    stmt = (
        select(OutboundOrderItem, Part, InventoryItem)
        .outerjoin(Part, Part.id == OutboundOrderItem.part_id)
        .outerjoin(
            InventoryItem,
            InventoryItem.id == OutboundOrderItem.inventory_item_id,
        )
        .where(
            OutboundOrderItem.order_id == order_id,
            OutboundOrderItem.is_deleted == 0,
        )
        .order_by(OutboundOrderItem.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        _to_item_vo(item, part, inventory_item) for item, part, inventory_item in rows
    ]


async def _get_order_or_404(
    db: AsyncSession,
    order_id: int,
    *,
    for_update: bool = False,
) -> OutboundOrder:
    """取出库单；状态流转类操作加行锁，避免并发重复提交/作废/审核。"""
    stmt = select(OutboundOrder).where(
        OutboundOrder.id == order_id,
        OutboundOrder.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise BizException(code=404, message="出库单不存在")
    return order


# ---------------------------------------------------------------- 查询
async def list_outbound_orders(
    db: AsyncSession,
    query: OutboundOrderQuery,
) -> PageResult[OutboundOrderVO]:
    """出库单分页查询（单号、仓库、类型、车辆、工单、领用人、状态、创建时间）。"""
    conditions = [OutboundOrder.is_deleted == 0]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                OutboundOrder.order_no.like(keyword),
                OutboundOrder.remark.like(keyword),
            )
        )
    if query.order_no:
        conditions.append(OutboundOrder.order_no.like(f"%{query.order_no.strip()}%"))
    if query.warehouse_id is not None:
        conditions.append(OutboundOrder.warehouse_id == query.warehouse_id)
    if query.outbound_type:
        conditions.append(OutboundOrder.outbound_type == query.outbound_type)
    if query.vehicle_id is not None:
        conditions.append(OutboundOrder.vehicle_id == query.vehicle_id)
    if query.work_order_id is not None:
        conditions.append(OutboundOrder.work_order_id == query.work_order_id)
    if query.receiver_id is not None:
        conditions.append(OutboundOrder.receiver_id == query.receiver_id)
    if query.status is not None:
        conditions.append(OutboundOrder.status == query.status)
    if query.scan_mode is not None:
        conditions.append(OutboundOrder.scan_mode == query.scan_mode)
    if query.start_time is not None:
        conditions.append(OutboundOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(OutboundOrder.created_at <= query.end_time)

    total = (
        await db.execute(
            select(func.count()).select_from(OutboundOrder).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(OutboundOrder, Warehouse.name, Vehicle.plate_no)
        .outerjoin(Warehouse, Warehouse.id == OutboundOrder.warehouse_id)
        .outerjoin(Vehicle, Vehicle.id == OutboundOrder.vehicle_id)
        .where(*conditions)
        .order_by(OutboundOrder.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    result: list[OutboundOrderVO] = []
    for order, warehouse_name, plate_no in rows:
        vo = OutboundOrderVO.model_validate(order)
        vo.warehouse_name = warehouse_name
        vo.vehicle_plate_no = plate_no
        result.append(vo)

    return PageResult[OutboundOrderVO](
        list=result,
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_outbound_order(
    db: AsyncSession,
    order_id: int,
) -> OutboundOrderDetailVO:
    """出库单详情（含明细、仓库名、车牌号）。"""
    stmt = (
        select(OutboundOrder, Warehouse.name, Vehicle.plate_no)
        .outerjoin(Warehouse, Warehouse.id == OutboundOrder.warehouse_id)
        .outerjoin(Vehicle, Vehicle.id == OutboundOrder.vehicle_id)
        .where(
            OutboundOrder.id == order_id,
            OutboundOrder.is_deleted == 0,
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="出库单不存在")

    order, warehouse_name, plate_no = row
    detail = OutboundOrderDetailVO.model_validate(order)
    detail.warehouse_name = warehouse_name
    detail.vehicle_plate_no = plate_no
    detail.items = await _list_items(db, order.id)
    return detail


# ---------------------------------------------------------------- 新建 / 编辑 / 状态流转
async def _insert_order_with_retry(
    db: AsyncSession,
    payload: OutboundOrderCreate,
    rows: list[dict[str, Any]],
    total_amount: Decimal,
    operator_id: int,
    scanner_id: int | None,
    current_user_id: int,
) -> OutboundOrder:
    """插入主单与明细；单号冲突时重新取号重试（唯一索引兜底保证并发安全）。"""
    for attempt in range(1, ORDER_NO_MAX_RETRY + 1):
        try:
            seq = await next_sequence(db, OUTBOUND_SEQUENCE)
            order_no = generate_outbound_no(seq)
        except SequenceExhausted as exc:
            raise BizException(
                code=409,
                message="出库单号当日流水号已用尽，请联系管理员",
            ) from exc

        order = OutboundOrder(
            order_no=order_no,
            warehouse_id=payload.warehouse_id,
            outbound_type=payload.outbound_type,
            vehicle_id=payload.vehicle_id,
            work_order_id=payload.work_order_id,
            receiver_id=payload.receiver_id,
            total_amount=total_amount,
            status=OrderStatus.DRAFT,
            scan_mode=payload.scan_mode,
            scanner_id=scanner_id,
            operator_id=operator_id,
            remark=payload.remark,
            created_by=current_user_id,
        )
        db.add(order)
        try:
            await db.flush()
            for row in rows:
                db.add(
                    OutboundOrderItem(
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
            raise BizException(code=409, message="出库单号生成冲突，请重试") from exc
        return order

    raise BizException(code=409, message="出库单号生成冲突，请重试")


async def create_outbound_order(
    db: AsyncSession,
    payload: OutboundOrderCreate,
    current_user_id: int,
) -> OutboundOrderDetailVO:
    """新建出库单（草稿）：单号自动生成，按件追踪的明细可指定库存件实例。"""
    _ensure_outbound_type(payload.outbound_type)
    await _get_warehouse_or_404(db, payload.warehouse_id)
    await _ensure_vehicle_exists(db, payload.vehicle_id)
    await _ensure_work_order_exists(db, payload.work_order_id)
    await _ensure_user_exists(db, payload.receiver_id, "领用人")
    await _ensure_user_exists(db, payload.scanner_id, "扫码操作人")

    operator_id = payload.operator_id or current_user_id
    if operator_id != current_user_id:
        await _ensure_user_exists(db, operator_id, "经办人")

    # 扫码模式未指定扫码人时默认当前用户，保证扫码记录可追溯
    scanner_id = payload.scanner_id
    if scanner_id is None and payload.scan_mode == 1:
        scanner_id = current_user_id

    rows = await _build_item_rows(db, payload.items, payload.warehouse_id)
    order = await _insert_order_with_retry(
        db,
        payload,
        rows,
        _sum_amount(rows),
        operator_id,
        scanner_id,
        current_user_id,
    )
    return await get_outbound_order(db, order.id)


async def update_outbound_order(
    db: AsyncSession,
    order_id: int,
    payload: OutboundOrderUpdate,
    current_user_id: int,
) -> OutboundOrderDetailVO:
    """编辑草稿；传 items 时整体替换原明细（旧明细逻辑删除）并重算总金额。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.DRAFT:
        raise BizException(code=ORDER_STATUS_NOT_ALLOWED, message="仅草稿状态可编辑")

    data = payload.model_dump(exclude_unset=True, exclude={"items"})

    if data.get("outbound_type") is not None:
        _ensure_outbound_type(data["outbound_type"])
    if data.get("warehouse_id") is not None:
        await _get_warehouse_or_404(db, data["warehouse_id"])
    if data.get("vehicle_id") is not None:
        await _ensure_vehicle_exists(db, data["vehicle_id"])
    if data.get("work_order_id") is not None:
        await _ensure_work_order_exists(db, data["work_order_id"])
    if data.get("receiver_id") is not None:
        await _ensure_user_exists(db, data["receiver_id"], "领用人")
    if data.get("scanner_id") is not None:
        await _ensure_user_exists(db, data["scanner_id"], "扫码操作人")
    operator_id = data.get("operator_id")
    if operator_id is not None and operator_id != current_user_id:
        await _ensure_user_exists(db, operator_id, "经办人")

    new_warehouse_id = data.get("warehouse_id")
    warehouse_changed = (
        new_warehouse_id is not None and new_warehouse_id != order.warehouse_id
    )

    # warehouse_id / outbound_type / scan_mode 为非空列，显式传 null 时忽略
    for field, value in data.items():
        if value is None and field in {"warehouse_id", "outbound_type", "scan_mode"}:
            continue
        setattr(order, field, value)
    order.updated_by = current_user_id

    # 扫码模式却无扫码人时补当前用户，避免出现无法追溯的扫码单
    if order.scan_mode == 1 and order.scanner_id is None:
        order.scanner_id = current_user_id

    if payload.items is not None:
        rows = await _build_item_rows(
            db,
            payload.items,
            order.warehouse_id,
            exclude_order_id=order.id,
        )
        await db.execute(
            update(OutboundOrderItem)
            .where(
                OutboundOrderItem.order_id == order.id,
                OutboundOrderItem.is_deleted == 0,
            )
            .values(is_deleted=1, updated_by=current_user_id)
        )
        for row in rows:
            db.add(
                OutboundOrderItem(
                    order_id=order.id,
                    created_by=current_user_id,
                    **row,
                )
            )
        order.total_amount = _sum_amount(rows)
    elif warehouse_changed:
        # 未重提明细时原明细库位/库存件可能属于旧仓库，提前拦截避免审核扣错库存
        await _ensure_existing_items_in_warehouse(db, order.id, order.warehouse_id)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="出库单更新失败，请重试") from exc
    return await get_outbound_order(db, order.id)


async def submit_outbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> OutboundOrderDetailVO:
    """提交审核：1 草稿 → 2 待审。

    提交前重新校验：明细非空、配件有效、库位仍合法；按件追踪的配件必须
    指定可用库存件实例，避免把不可出库的件带到审核环节。
    """
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.DRAFT:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅草稿状态可提交审核",
        )

    items = (
        (
            await db.execute(
                select(OutboundOrderItem)
                .where(
                    OutboundOrderItem.order_id == order.id,
                    OutboundOrderItem.is_deleted == 0,
                )
                .order_by(OutboundOrderItem.id.asc())
            )
        )
        .scalars()
        .all()
    )
    if not items:
        raise BizException(code=400, message="出库单明细不能为空，无法提交")

    parts = await _load_parts(db, [item.part_id for item in items])
    await _ensure_locations(
        db, order.warehouse_id, [item.location_id for item in items]
    )
    await _load_inventory_items(
        db,
        list(items),
        order.warehouse_id,
        parts,
        exclude_order_id=order.id,
    )

    for item in items:
        part = parts[item.part_id]
        if part.track_by_item == 1 and item.inventory_item_id is None:
            raise BizException(
                code=400,
                message=(
                    f"配件 {part.part_name} 按件追踪，请扫码指定库存件后再提交审核"
                ),
            )

    order.status = OrderStatus.PENDING
    order.operator_id = order.operator_id or current_user_id
    order.updated_by = current_user_id
    await db.commit()
    return await get_outbound_order(db, order.id)


async def cancel_outbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> OutboundOrderDetailVO:
    """作废出库单：草稿 / 待审 → 4 作废；已出库单据不允许作废。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status not in {OrderStatus.DRAFT, OrderStatus.PENDING}:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="当前状态不允许作废",
        )

    order.status = OrderStatus.CANCELLED
    order.updated_by = current_user_id
    await db.commit()
    return await get_outbound_order(db, order.id)


# ---------------------------------------------------------------- 审核通过（出库）
async def _load_items_for_update(
    db: AsyncSession,
    order_id: int,
) -> list[OutboundOrderItem]:
    """按主键升序锁定出库明细，避免同一单据并发审核时明细被改。"""
    stmt = (
        select(OutboundOrderItem)
        .where(
            OutboundOrderItem.order_id == order_id,
            OutboundOrderItem.is_deleted == 0,
        )
        .order_by(OutboundOrderItem.id.asc())
        .with_for_update()
    )
    return list((await db.execute(stmt)).scalars().all())


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


async def _apply_outbound_items(
    db: AsyncSession,
    order: OutboundOrder,
    items: list[OutboundOrderItem],
    parts: dict[int, Part],
    inventory_items: dict[int, InventoryItem],
    current_user_id: int,
    now: datetime,
) -> None:
    """逐条扣减库存并写出库流水 / 工单领料；调用前已完成全部校验与加锁。"""
    cache: dict[tuple[int, int, int | None], Inventory | None] = {}

    def _sort_key(detail: OutboundOrderItem) -> tuple[int, int, int]:
        """按 配件 + 库位 + 明细主键 排序，统一多张单据的加锁顺序。"""
        instance = (
            inventory_items.get(detail.inventory_item_id)
            if detail.inventory_item_id is not None
            else None
        )
        location_id = (
            instance.location_id if instance is not None else detail.location_id
        )
        return (detail.part_id, location_id or 0, detail.id)

    for item in sorted(items, key=_sort_key):
        part = parts[item.part_id]
        instance = (
            inventory_items.get(item.inventory_item_id)
            if item.inventory_item_id is not None
            else None
        )
        location_id = instance.location_id if instance is not None else item.location_id
        inventory = await _lock_inventory_row(
            db,
            cache,
            part_id=item.part_id,
            warehouse_id=order.warehouse_id,
            location_id=location_id,
        )
        if inventory is None:
            raise BizException(
                code=INSUFFICIENT_STOCK,
                message=f"配件 {part.part_name} 在出库仓库/库位无库存记录，无法出库",
            )

        before_qty = Decimal(inventory.quantity or 0)
        if before_qty < item.quantity:
            raise BizException(
                code=INSUFFICIENT_STOCK,
                message=(
                    f"配件 {part.part_name} 库存不足："
                    f"当前 {before_qty}，需出库 {item.quantity}"
                ),
            )

        if instance is not None:
            # 库存件实例回填出库信息，状态置为已出库，防止再次被扫码出库
            instance.status = InventoryItemStatus.OUT
            instance.outbound_item_id = item.id
            instance.vehicle_id = order.vehicle_id
            instance.work_order_id = order.work_order_id
            instance.out_at = now
            instance.updated_by = current_user_id
            # 库位以实例为准，保持明细与扣减行一致
            item.location_id = instance.location_id
            inventory.item_count = max(int(inventory.item_count or 0) - 1, 0)
            batch_no = item.batch_no or instance.batch_no
            scan_code: str | None = item.scan_code or instance.item_code
        else:
            if part.track_by_item == 1:
                # 提交审核已拦截，这里兜底避免汇总数量与在库实例数不一致
                raise BizException(
                    code=400,
                    message=f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法出库",
                )
            batch_no = item.batch_no
            scan_code = item.scan_code

        inventory.quantity = before_qty - item.quantity
        inventory.last_out_at = now
        inventory.updated_by = current_user_id

        unit_cost = Decimal(inventory.avg_cost or 0)
        if unit_cost == 0 and instance is not None:
            unit_cost = Decimal(instance.unit_cost or 0)

        db.add(
            InventoryTransaction(
                part_id=item.part_id,
                inventory_item_id=item.inventory_item_id,
                warehouse_id=order.warehouse_id,
                location_id=location_id,
                biz_type=BizType.OUT,
                change_qty=-item.quantity,
                before_qty=before_qty,
                after_qty=inventory.quantity,
                unit_cost=unit_cost,
                ref_type=RefType.OUTBOUND,
                ref_id=order.id,
                ref_no=order.order_no,
                batch_no=batch_no,
                scan_code=scan_code,
                operator_id=current_user_id,
                remark=item.remark,
                created_by=current_user_id,
            )
        )

        if order.work_order_id is not None:
            amount = item.amount
            if amount is None:
                amount = _line_amount(item.quantity, Decimal(item.unit_cost or 0))
            db.add(
                WorkOrderPart(
                    work_order_id=order.work_order_id,
                    outbound_item_id=item.id,
                    part_id=item.part_id,
                    quantity=item.quantity,
                    cost=amount,
                    created_by=current_user_id,
                )
            )


async def _approve_once(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> None:
    """单次审核出库（一整个事务）：成功提交，失败回滚。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != OrderStatus.PENDING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅待审状态可审核出库",
        )

    items = await _load_items_for_update(db, order.id)
    if not items:
        raise BizException(code=400, message="出库单明细为空，无法审核")

    # 审核阶段配件可能已停用，不阻塞已审批单据；是否追踪仍以主数据为准
    parts = await _load_parts(
        db, [item.part_id for item in items], require_enabled=False
    )

    now = datetime.now()
    try:
        inventory_items = await _load_inventory_items(
            db,
            items,
            order.warehouse_id,
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
                        f"配件 {part.part_name} 按件追踪，缺少库存件实例，无法出库"
                    ),
                )

        await _apply_outbound_items(
            db,
            order,
            items,
            parts,
            inventory_items,
            current_user_id,
            now,
        )

        order.status = OrderStatus.COMPLETED
        order.audit_user_id = current_user_id
        order.audit_at = now
        order.outbound_at = now
        order.updated_by = current_user_id

        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def approve_outbound_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> OutboundOrderDetailVO:
    """审核通过出库单：2 待审 → 3 已出库。

    整个审核过程在一个事务内完成：库存件状态与出库信息回填、库存汇总扣减、
    库存流水、工单领料、单据状态任一失败全部回滚。单据 / 明细 / 库存件 /
    库存行均加 `FOR UPDATE` 行锁，并按固定顺序加锁避免并发死锁；
    并发审核同一张单或同一件时，后到事务会因状态已变更而返回 3001 / 2003。
    """
    try:
        await _approve_once(db, order_id, current_user_id)
    except IntegrityError as exc:
        # _approve_once 已回滚
        raise BizException(code=409, message="出库处理冲突，请重试") from exc

    return await get_outbound_order(db, order_id)
