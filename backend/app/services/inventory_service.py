"""库存查询业务逻辑：库存汇总、低库存预警、库存件查询 / 编辑与库存件流水。

约定：
- 查询（库存汇总、低库存预警、库存件、流水）只读，不做任何写操作；
- 唯一的写操作是「编辑库存件资料」：库存件编码 / 二维码 / 数量 / 状态由系统与
  业务单据维护，接口只允许改仓库 / 库位、批次、序列号、生产 / 到期日期、成本、
  备注；仓库 / 库位变更按「单件调拨」记账（同步 `inventory` 汇总 + 写
  TRANSFER_OUT / TRANSFER_IN 流水），避免库存件与汇总表脱钩；
- 库存汇总按「配件 + 仓库 + 库位」一行，join 配件 / 仓库 / 库位后直接返回
  展示所需的编码与名称，前端无需二次请求主数据；
- 低库存判定：配件维护了安全库存（`safety_stock > 0`）且可用数量
  （`quantity - locked_qty`）低于安全库存，与 `InventoryQuery.low_stock` 一致；
- 库存汇总与库存件列表过滤已逻辑删除的配件，避免展示已删除主数据；
- `inventory_transaction` 是只读流水表，没有 `is_deleted`，按创建时间倒序返回。
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    Warehouse,
    WarehouseLocation,
)
from app.models.enums import (
    INVENTORY_ITEM_STATUS_TEXT,
    BizType,
    CommonStatus,
    InventoryItemStatus,
    RefType,
)
from app.schemas.common import PageResult
from app.schemas.inventory import (
    InventoryDetailVO,
    InventoryQuery,
    InventoryTransactionQuery,
    InventoryTransactionVO,
)
from app.schemas.inventory_item import (
    InventoryItemDetailVO,
    InventoryItemQuery,
    InventoryItemUpdate,
)

__all__ = [
    "get_inventory_item",
    "list_inventory",
    "list_inventory_item_transactions",
    "list_inventory_items",
    "list_inventory_warnings",
    "update_inventory_item",
]

# 可用数量：当前数量 - 锁定数量（均为非空列，可直接参与 SQL 运算）
AVAILABLE_QTY = Inventory.quantity - Inventory.locked_qty
# 缺口数量：安全库存 - 可用数量，用于库存预警按紧急程度排序
SHORTAGE_QTY = Part.safety_stock - AVAILABLE_QTY

# 业务错误码（见 docs/backend-requirements.md 错误码约定）
INSUFFICIENT_STOCK: int = 2001
ITEM_NOT_IN_STOCK: int = 2002
ITEM_ALREADY_OUT: int = 2003
ITEM_LOCKED: int = 2004

# 数量保留两位小数、成本保留四位小数
QTY_QUANT: Decimal = Decimal("0.01")
COST_QUANT: Decimal = Decimal("0.0001")
ZERO_QTY: Decimal = Decimal("0.00")
ZERO_COST: Decimal = Decimal("0.0000")
ONE_QTY: Decimal = Decimal("1.00")

# 编辑接口不可修改的字段（系统生成 / 状态机维护 / 按件恒为 1 的数量）
LOCKED_EDIT_FIELDS: tuple[str, ...] = ("item_code", "qrcode", "quantity", "status")


# ---------------------------------------------------------------- 内部工具
def _inventory_conditions(
    query: InventoryQuery,
    *,
    low_stock: bool | None = None,
) -> list[ColumnElement[bool]]:
    """构造库存汇总查询条件；`low_stock` 显式传入时覆盖查询参数。"""
    conditions: list[ColumnElement[bool]] = [
        Inventory.is_deleted == 0,
        Part.is_deleted == 0,
    ]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                Part.part_code.like(keyword),
                Part.part_name.like(keyword),
            )
        )
    if query.part_id is not None:
        conditions.append(Inventory.part_id == query.part_id)
    if query.warehouse_id is not None:
        conditions.append(Inventory.warehouse_id == query.warehouse_id)
    if query.location_id is not None:
        conditions.append(Inventory.location_id == query.location_id)

    # 未维护安全库存的配件不参与低库存预警，避免全表刷出 0 库存记录
    only_low_stock = query.low_stock if low_stock is None else low_stock
    if only_low_stock:
        conditions.append(Part.safety_stock.is_not(None))
        conditions.append(Part.safety_stock > 0)
        conditions.append(AVAILABLE_QTY < Part.safety_stock)

    return conditions


def _to_inventory_detail_vo(
    inventory: Inventory,
    part: Part,
    warehouse: Warehouse | None,
    location: WarehouseLocation | None,
) -> InventoryDetailVO:
    """库存汇总 ORM 转 VO，补齐配件、仓库、库位展示字段。"""
    vo = InventoryDetailVO.model_validate(inventory)
    vo.part_code = part.part_code
    vo.part_name = part.part_name
    vo.spec = part.spec
    vo.unit = part.unit
    vo.safety_stock = part.safety_stock
    vo.max_stock = part.max_stock
    vo.warehouse_name = warehouse.name if warehouse is not None else None
    vo.location_code = location.location_code if location is not None else None
    return vo


async def _paginate_inventory(
    db: AsyncSession,
    query: InventoryQuery,
    *,
    low_stock: bool | None = None,
    order_by_shortage: bool = False,
) -> PageResult[InventoryDetailVO]:
    """库存汇总分页查询（内部复用：库存列表 / 低库存预警）。"""
    conditions = _inventory_conditions(query, low_stock=low_stock)

    total = (
        await db.execute(
            select(func.count(Inventory.id))
            .select_from(Inventory)
            .join(Part, Part.id == Inventory.part_id)
            .where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(Inventory, Part, Warehouse, WarehouseLocation)
        .join(Part, Part.id == Inventory.part_id)
        .outerjoin(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == Inventory.location_id,
        )
        .where(*conditions)
    )
    if order_by_shortage:
        # 预警列表优先展示缺口最大的记录
        stmt = stmt.order_by(SHORTAGE_QTY.desc(), Inventory.id.desc())
    else:
        stmt = stmt.order_by(Inventory.id.desc())

    rows = (
        await db.execute(
            stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        )
    ).all()

    return PageResult[InventoryDetailVO](
        list=[_to_inventory_detail_vo(*row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def _inventory_item_conditions(
    query: InventoryItemQuery,
) -> list[ColumnElement[bool]]:
    """构造库存件分页查询条件。"""
    conditions: list[ColumnElement[bool]] = [
        InventoryItem.is_deleted == 0,
        Part.is_deleted == 0,
    ]

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                InventoryItem.item_code.like(keyword),
                InventoryItem.qrcode.like(keyword),
                InventoryItem.serial_no.like(keyword),
                InventoryItem.batch_no.like(keyword),
            )
        )
    if query.part_id is not None:
        conditions.append(InventoryItem.part_id == query.part_id)
    if query.warehouse_id is not None:
        conditions.append(InventoryItem.warehouse_id == query.warehouse_id)
    if query.location_id is not None:
        conditions.append(InventoryItem.location_id == query.location_id)
    if query.status is not None:
        conditions.append(InventoryItem.status == query.status)
    if query.vehicle_id is not None:
        conditions.append(InventoryItem.vehicle_id == query.vehicle_id)
    if query.work_order_id is not None:
        conditions.append(InventoryItem.work_order_id == query.work_order_id)
    if query.batch_no:
        conditions.append(InventoryItem.batch_no == query.batch_no.strip())
    if query.expire_before is not None:
        # 未设置到期日的库存件不参与临期查询
        conditions.append(InventoryItem.expire_date.is_not(None))
        conditions.append(InventoryItem.expire_date <= query.expire_before)

    return conditions


def _to_inventory_item_detail_vo(
    item: InventoryItem,
    part: Part | None,
    warehouse: Warehouse | None,
    location: WarehouseLocation | None,
) -> InventoryItemDetailVO:
    """库存件 ORM 转 VO，补齐配件、仓库、库位与状态文案。"""
    vo = InventoryItemDetailVO.model_validate(item)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
        vo.unit = part.unit
    vo.status_text = INVENTORY_ITEM_STATUS_TEXT.get(item.status, "未知")
    vo.warehouse_name = warehouse.name if warehouse is not None else None
    vo.location_code = location.location_code if location is not None else None
    return vo


async def _ensure_item_exists(db: AsyncSession, item_id: int) -> None:
    """校验库存件存在且未逻辑删除，不存在抛 404。"""
    exists = (
        await db.execute(
            select(InventoryItem.id)
            .where(
                InventoryItem.id == item_id,
                InventoryItem.is_deleted == 0,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if exists is None:
        raise BizException(code=404, message="库存件不存在")


# ------------------------------------------------- 编辑库存件：内部工具
def _qty(value: Decimal | int | None) -> Decimal:
    """数量统一保留两位小数（四舍五入），None 视为 0。"""
    if value is None:
        return ZERO_QTY
    return Decimal(value).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def _clean_text(value: str | None) -> str | None:
    """字符串去首尾空格；空串按「清空该字段」处理为 None。"""
    if value is None:
        return None
    text = value.strip()
    return text or None


def _reject_null(data: dict[str, Any], labels: dict[str, str]) -> None:
    """编辑时显式提交 null 视为参数错误，避免覆盖非空列后抛 500。"""
    for field, label in labels.items():
        if field in data and data[field] is None:
            raise BizException(code=400, message=f"{label}不能为空")


def _calc_avg_cost(
    before_qty: Decimal,
    before_avg: Decimal,
    in_qty: Decimal,
    in_price: Decimal,
) -> Decimal:
    """移动加权平均成本：(原数量×原均价 + 入库数量×入库成本) ÷ 入库后总数量。"""
    total_qty = before_qty + in_qty
    if total_qty <= 0:
        return ZERO_COST
    return ((before_qty * before_avg + in_qty * in_price) / total_qty).quantize(
        COST_QUANT, rounding=ROUND_HALF_UP
    )


def _shift_avg_cost(
    before_qty: Decimal,
    before_avg: Decimal,
    delta_cost: Decimal,
) -> Decimal:
    """单件成本变化后重算移动加权平均：(数量×原均价 + 成本差额) ÷ 数量。

    库存件按件追踪，改一件的成本等价于给所在库存行增加 `delta_cost` 金额，
    按原数量摊回即可保持「数量 × 均价 = 库存金额」不变形；无数量时保留原均价。
    """
    if before_qty <= 0:
        return before_avg
    avg = (before_qty * before_avg + delta_cost) / before_qty
    return max(avg, ZERO_COST).quantize(COST_QUANT, rounding=ROUND_HALF_UP)


def _ensure_item_movable(item: InventoryItem) -> None:
    """仅「在库」实例可调整仓库 / 库位，其余状态抛对应业务错误码。"""
    if item.status == InventoryItemStatus.IN_STOCK:
        return
    if item.status == InventoryItemStatus.OUT:
        raise BizException(
            code=ITEM_ALREADY_OUT,
            message="已出库的库存件不能调整仓库 / 库位",
        )
    if item.status == InventoryItemStatus.LOCKED:
        raise BizException(
            code=ITEM_LOCKED,
            message="调拨在途（锁定）的库存件不能调整仓库 / 库位，请先在调拨单确认调入",
        )
    raise BizException(
        code=ITEM_NOT_IN_STOCK,
        message="库存件当前不在库，不能调整仓库 / 库位",
    )


async def _get_item_for_update(db: AsyncSession, item_id: int) -> InventoryItem:
    """按 ID 锁库存件行，不存在或已逻辑删除抛 404。"""
    stmt = (
        select(InventoryItem)
        .where(
            InventoryItem.id == item_id,
            InventoryItem.is_deleted == 0,
        )
        .with_for_update()
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise BizException(code=404, message="库存件不存在")
    return item


async def _get_warehouse_or_404(db: AsyncSession, warehouse_id: int) -> Warehouse:
    """取启用中的仓库，不存在抛 404，已停用抛 400。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message="仓库不存在")
    if warehouse.status != CommonStatus.ENABLED:
        raise BizException(code=400, message=f"仓库 {warehouse.name} 已停用")
    return warehouse


async def _get_location_or_404(
    db: AsyncSession,
    warehouse_id: int,
    location_id: int | None,
) -> WarehouseLocation | None:
    """校验库位存在、属于指定仓库且启用（未指定库位表示仓库级）。"""
    if location_id is None:
        return None
    location = await db.get(WarehouseLocation, location_id)
    if location is None or location.is_deleted:
        raise BizException(code=404, message="库位不存在")
    if location.warehouse_id != warehouse_id:
        raise BizException(
            code=400,
            message=f"库位 {location.location_code} 不属于所选仓库",
        )
    if location.status != CommonStatus.ENABLED:
        raise BizException(
            code=400,
            message=f"库位 {location.location_code} 已停用",
        )
    return location


async def _lock_inventory_row(
    db: AsyncSession,
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
) -> Inventory | None:
    """按 配件 + 仓库 + 库位 加行锁取库存行，不存在返回 None。"""
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
    return (await db.execute(stmt)).scalar_one_or_none()


async def _lock_or_create_inventory(
    db: AsyncSession,
    *,
    part_id: int,
    warehouse_id: int,
    location_id: int | None,
    current_user_id: int,
) -> Inventory:
    """取 配件+仓库+库位 的库存行并加行锁，不存在则创建（与调拨调入一致）。"""
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
        )
        .with_for_update()
    )
    inventory = (await db.execute(stmt)).scalar_one_or_none()
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
        # 立即 flush：尽早暴露唯一索引冲突，并让后续调整读取到该行
        await db.flush()
    elif inventory.is_deleted:
        # 历史逻辑删除的库存行直接复用，避免与唯一索引冲突
        inventory.is_deleted = 0
        inventory.quantity = ZERO_QTY
        inventory.item_count = 0
        inventory.locked_qty = ZERO_QTY
        inventory.avg_cost = ZERO_COST
        inventory.updated_by = current_user_id
    return inventory


async def _apply_item_move(
    db: AsyncSession,
    item: InventoryItem,
    *,
    to_warehouse_id: int,
    to_location_id: int | None,
    unit_cost: Decimal,
    batch_no: str | None,
    current_user_id: int,
    now: datetime,
) -> None:
    """单件移动记账：扣减原仓库/库位库存、增加目标仓库/库位库存并写调拨流水。

    库存件按件追踪，单件搬家等价于「数量 1 的调拨」：两侧 `quantity` 与
    `item_count` 同步增减，目标行按该件成本重算移动加权平均；流水沿用
    TRANSFER_OUT / TRANSFER_IN + TRANSFER 单据类型，便于在库存件流水中追溯。
    """
    from_warehouse_id = item.warehouse_id
    from_location_id = item.location_id

    # 锁配件行，串行化目标库存行的创建，避免并发下唯一索引冲突
    await db.execute(select(Part.id).where(Part.id == item.part_id).with_for_update())

    source = await _lock_inventory_row(
        db,
        part_id=item.part_id,
        warehouse_id=from_warehouse_id,
        location_id=from_location_id,
    )
    if source is None or _qty(source.quantity) < ONE_QTY:
        raise BizException(
            code=INSUFFICIENT_STOCK,
            message="原仓库 / 库位库存汇总不足，无法调整存放位置，请使用调拨单处理",
        )

    source_before = _qty(source.quantity)
    source.quantity = source_before - ONE_QTY
    source.item_count = max(int(source.item_count or 0) - 1, 0)
    source.last_out_at = now
    source.updated_by = current_user_id

    target = await _lock_or_create_inventory(
        db,
        part_id=item.part_id,
        warehouse_id=to_warehouse_id,
        location_id=to_location_id,
        current_user_id=current_user_id,
    )
    target_before = _qty(target.quantity)
    target.quantity = target_before + ONE_QTY
    if unit_cost > 0:
        target.avg_cost = _calc_avg_cost(
            target_before,
            Decimal(target.avg_cost or 0),
            ONE_QTY,
            unit_cost,
        )
    target.item_count = int(target.item_count or 0) + 1
    target.last_in_at = now
    target.updated_by = current_user_id

    for warehouse_id, location_id, biz_type, change_qty, before_qty, after_qty in (
        (
            from_warehouse_id,
            from_location_id,
            BizType.TRANSFER_OUT,
            -ONE_QTY,
            source_before,
            source.quantity,
        ),
        (
            to_warehouse_id,
            to_location_id,
            BizType.TRANSFER_IN,
            ONE_QTY,
            target_before,
            target.quantity,
        ),
    ):
        db.add(
            InventoryTransaction(
                part_id=item.part_id,
                inventory_item_id=item.id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                biz_type=biz_type,
                change_qty=change_qty,
                before_qty=before_qty,
                after_qty=after_qty,
                unit_cost=unit_cost,
                ref_type=RefType.TRANSFER,
                ref_id=None,
                ref_no=None,
                batch_no=batch_no,
                scan_code=item.item_code,
                operator_id=current_user_id,
                remark="编辑库存件：调整存放位置（单件调拨）",
                created_by=current_user_id,
            )
        )


async def _apply_unit_cost_change(
    db: AsyncSession,
    item: InventoryItem,
    old_cost: Decimal,
    new_cost: Decimal,
    current_user_id: int,
) -> None:
    """单位成本变更：按差额重算所在库存行的移动加权平均成本。

    已出库 / 已报废 / 已盘亏的实例不计入当前库存金额，只更新实例自身成本。
    """
    if item.status != InventoryItemStatus.IN_STOCK:
        return
    inventory = await _lock_inventory_row(
        db,
        part_id=item.part_id,
        warehouse_id=item.warehouse_id,
        location_id=item.location_id,
    )
    if inventory is None:
        return
    inventory.avg_cost = _shift_avg_cost(
        _qty(inventory.quantity),
        Decimal(inventory.avg_cost or 0),
        new_cost - old_cost,
    )
    inventory.updated_by = current_user_id


# ---------------------------------------------------------------- 库存汇总
async def list_inventory(
    db: AsyncSession,
    query: InventoryQuery,
) -> PageResult[InventoryDetailVO]:
    """库存汇总分页（按配件 + 仓库 + 库位）。

    支持配件编码/名称关键字、配件、仓库、库位筛选；
    `low_stock=true` 时只返回可用数量低于安全库存的记录（低库存高亮）。
    """
    return await _paginate_inventory(db, query)


async def list_inventory_warnings(
    db: AsyncSession,
    query: InventoryQuery,
) -> PageResult[InventoryDetailVO]:
    """低库存预警分页：可用数量（quantity - locked_qty）低于安全库存。

    与库存列表使用相同的筛选条件，`low_stock` 强制为 true；
    结果按缺口数量倒序，缺口最大的记录排在最前，便于优先补货。
    """
    return await _paginate_inventory(
        db,
        query,
        low_stock=True,
        order_by_shortage=True,
    )


# ---------------------------------------------------------------- 库存件
async def list_inventory_items(
    db: AsyncSession,
    query: InventoryItemQuery,
) -> PageResult[InventoryItemDetailVO]:
    """库存件实例分页。

    支持库存件编码 / 二维码 / 序列号 / 批次号关键字，以及配件、仓库、库位、
    状态、车辆、工单、批次、到期日（临期）筛选。
    """
    conditions = _inventory_item_conditions(query)

    total = (
        await db.execute(
            select(func.count(InventoryItem.id))
            .select_from(InventoryItem)
            .join(Part, Part.id == InventoryItem.part_id)
            .where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(InventoryItem, Part, Warehouse, WarehouseLocation)
        .join(Part, Part.id == InventoryItem.part_id)
        .outerjoin(Warehouse, Warehouse.id == InventoryItem.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == InventoryItem.location_id,
        )
        .where(*conditions)
        .order_by(InventoryItem.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    return PageResult[InventoryItemDetailVO](
        list=[_to_inventory_item_detail_vo(*row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_inventory_item(
    db: AsyncSession,
    item_id: int,
) -> InventoryItemDetailVO:
    """库存件详情（含配件、仓库、库位与状态文案），不存在返回 404。"""
    stmt = (
        select(InventoryItem, Part, Warehouse, WarehouseLocation)
        .outerjoin(Part, Part.id == InventoryItem.part_id)
        .outerjoin(Warehouse, Warehouse.id == InventoryItem.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == InventoryItem.location_id,
        )
        .where(
            InventoryItem.id == item_id,
            InventoryItem.is_deleted == 0,
        )
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="库存件不存在")
    return _to_inventory_item_detail_vo(*row)


async def list_inventory_item_transactions(
    db: AsyncSession,
    item_id: int,
    query: InventoryTransactionQuery,
) -> PageResult[InventoryTransactionVO]:
    """库存件流水（只读，按创建时间倒序）。

    `inventory_item_id` 一律以路径中的库存件 ID 为准，查询参数中的同名条件忽略；
    其余条件（业务类型、单据类型/单号、时间范围等）作为附加筛选。
    """
    await _ensure_item_exists(db, item_id)

    conditions: list[ColumnElement[bool]] = [
        InventoryTransaction.inventory_item_id == item_id,
    ]
    if query.part_id is not None:
        conditions.append(InventoryTransaction.part_id == query.part_id)
    if query.warehouse_id is not None:
        conditions.append(InventoryTransaction.warehouse_id == query.warehouse_id)
    if query.location_id is not None:
        conditions.append(InventoryTransaction.location_id == query.location_id)
    if query.biz_type:
        conditions.append(InventoryTransaction.biz_type == query.biz_type)
    if query.ref_type:
        conditions.append(InventoryTransaction.ref_type == query.ref_type)
    if query.ref_id is not None:
        conditions.append(InventoryTransaction.ref_id == query.ref_id)
    if query.ref_no:
        conditions.append(InventoryTransaction.ref_no.like(f"%{query.ref_no.strip()}%"))
    if query.start_time is not None:
        conditions.append(InventoryTransaction.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(InventoryTransaction.created_at <= query.end_time)

    total = (
        await db.execute(select(func.count(InventoryTransaction.id)).where(*conditions))
    ).scalar_one()

    stmt = (
        select(InventoryTransaction)
        .where(*conditions)
        .order_by(
            InventoryTransaction.created_at.desc(),
            InventoryTransaction.id.desc(),
        )
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[InventoryTransactionVO](
        list=[
            InventoryTransactionVO.model_validate(transaction) for transaction in rows
        ],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


# ---------------------------------------------------------------- 编辑库存件
async def update_inventory_item(
    db: AsyncSession,
    item_id: int,
    payload: InventoryItemUpdate,
    current_user_id: int,
) -> InventoryItemDetailVO:
    """编辑库存件资料（编码 / 二维码 / 数量 / 状态不可编辑）。

    - 仅更新请求中出现的字段，`location_id` 传 null 表示改为仓库级存放；
    - 仓库 / 库位变更按「单件调拨」处理：同步 `inventory` 汇总（两侧
      `quantity` / `item_count`）并写 TRANSFER_OUT / TRANSFER_IN 流水，
      仅「在库」实例可调整，其余状态返回 2002 / 2003 / 2004；
    - 单位成本变更按移动加权平均重算所在库存行均价，保持库存金额一致；
    - 库存件编码、二维码、数量、状态、配件、车辆 / 工单字段一律拒绝修改。
    """
    item = await _get_item_for_update(db, item_id)
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    _reject_null(data, {"warehouse_id": "仓库", "unit_cost": "单位成本"})
    for field in ("batch_no", "serial_no", "remark"):
        if field in data:
            data[field] = _clean_text(data[field])

    old_unit_cost = Decimal(item.unit_cost or 0)
    new_unit_cost = Decimal(data["unit_cost"]) if "unit_cost" in data else old_unit_cost

    target_warehouse_id = (
        int(data["warehouse_id"]) if "warehouse_id" in data else item.warehouse_id
    )
    if "location_id" in data:
        target_location_id = data["location_id"]
    elif target_warehouse_id != item.warehouse_id:
        # 库位隶属于原仓库，换仓库且未指定库位时改为仓库级存放
        target_location_id = None
    else:
        target_location_id = item.location_id

    warehouse_changed = target_warehouse_id != item.warehouse_id
    location_changed = target_location_id != item.location_id
    if warehouse_changed:
        await _get_warehouse_or_404(db, target_warehouse_id)
    if warehouse_changed or location_changed:
        await _get_location_or_404(db, target_warehouse_id, target_location_id)

    production_date = data.get("production_date", item.production_date)
    expire_date = data.get("expire_date", item.expire_date)
    if production_date and expire_date and expire_date < production_date:
        raise BizException(code=400, message="到期日期不能早于生产日期")

    if warehouse_changed or location_changed:
        _ensure_item_movable(item)
        await _apply_item_move(
            db,
            item,
            to_warehouse_id=target_warehouse_id,
            to_location_id=target_location_id,
            unit_cost=new_unit_cost,
            batch_no=data.get("batch_no", item.batch_no),
            current_user_id=current_user_id,
            now=datetime.now(),
        )
    elif new_unit_cost != old_unit_cost:
        await _apply_unit_cost_change(
            db,
            item,
            old_unit_cost,
            new_unit_cost,
            current_user_id,
        )

    item.warehouse_id = target_warehouse_id
    item.location_id = target_location_id
    for field in (
        "batch_no",
        "serial_no",
        "production_date",
        "expire_date",
        "remark",
    ):
        if field in data:
            setattr(item, field, data[field])
    item.unit_cost = new_unit_cost
    item.updated_by = current_user_id

    await db.commit()
    return await get_inventory_item(db, item_id)

