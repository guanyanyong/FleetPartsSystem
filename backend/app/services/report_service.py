"""报表业务逻辑：库存报表、流水报表、单车成本与首页看板。

约定：
- 报表全部只读，不做任何写操作；
- 金额统一保留两位小数（四舍五入），库存金额 = 当前数量 × 移动加权平均成本；
- 库存报表按「配件 + 仓库 + 库位」一行，低库存判定与库存预警一致：
  配件维护了安全库存（`safety_stock > 0`）且可用数量（`quantity - locked_qty`）
  低于安全库存；
- 流水报表保留历史数据，配件 / 仓库被逻辑删除后仍可查询，展示字段通过
  LEFT JOIN 补齐；
- 流水合计中的出库 / 调拨出 / 盘亏按正数展示，净变动保留正负号；
- 单车成本只统计已完工 / 已结算工单，按车辆输出（无维修记录的车辆成本为 0）；
- 首页看板中本月入库 / 出库金额按业务时间（`inbound_at` / `outbound_at`）统计，
  业务时间为空时回退到创建时间。
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import (  # type: ignore[import-untyped]
    Alignment,
    Font,
    PatternFill,
)
from openpyxl.utils import get_column_letter  # type: ignore[import-untyped]
from sqlalchemy import (
    ColumnElement,
    and_,
    case,
    func,
    literal_column,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InboundOrder,
    Inventory,
    InventoryTransaction,
    OutboundOrder,
    Part,
    PartCategory,
    Vehicle,
    VehicleModel,
    Warehouse,
    WarehouseLocation,
    WorkOrder,
)
from app.models.enums import BizType, OrderStatus, WorkOrderStatus
from app.schemas.report import (
    DashboardVO,
    InventoryReportQuery,
    InventoryReportResult,
    InventoryReportSummaryVO,
    InventoryReportVO,
    TransactionReportQuery,
    TransactionReportResult,
    TransactionReportSummaryVO,
    TransactionReportVO,
    VehicleCostQuery,
    VehicleCostResult,
    VehicleCostSummaryVO,
    VehicleCostVO,
)

__all__ = [
    "build_inventory_report_workbook",
    "export_inventory_report",
    "get_dashboard",
    "list_inventory_report",
    "list_transaction_report",
    "list_vehicle_cost_report",
]

# 可用数量：当前数量 - 锁定数量（均为非空列）
AVAILABLE_QTY = Inventory.quantity - Inventory.locked_qty
# 库存金额：当前数量 × 移动加权平均成本
INVENTORY_AMOUNT = Inventory.quantity * Inventory.avg_cost


# ---------------------------------------------------------------- 内部工具
def _money(value: Decimal | float | None) -> Decimal:
    """金额统一保留两位小数（四舍五入）。"""
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _low_stock_conditions() -> list[ColumnElement[bool]]:
    """低库存条件：维护了安全库存且可用数量不足。"""
    return [
        Part.safety_stock.is_not(None),
        Part.safety_stock > 0,
        AVAILABLE_QTY < Part.safety_stock,
    ]


# ---------------------------------------------------------------- 库存报表
def _inventory_conditions(query: InventoryReportQuery) -> list[ColumnElement[bool]]:
    """构造库存报表查询条件。"""
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
    if query.category_id is not None:
        conditions.append(Part.category_id == query.category_id)
    if query.warehouse_id is not None:
        conditions.append(Inventory.warehouse_id == query.warehouse_id)
    if query.location_id is not None:
        conditions.append(Inventory.location_id == query.location_id)
    if not query.include_zero:
        conditions.append(Inventory.quantity > 0)
    if query.low_stock:
        conditions.extend(_low_stock_conditions())

    return conditions


def _inventory_rows_stmt(query: InventoryReportQuery) -> Any:
    """库存报表明细查询（分页 / 导出共用）。"""
    return (
        select(
            Inventory,
            Part,
            PartCategory.name,
            Warehouse.name,
            WarehouseLocation.location_code,
        )
        .join(Part, Part.id == Inventory.part_id)
        .outerjoin(PartCategory, PartCategory.id == Part.category_id)
        .outerjoin(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == Inventory.location_id,
        )
        .where(*_inventory_conditions(query))
        .order_by(
            Part.part_code.asc(),
            Inventory.warehouse_id.asc(),
            Inventory.location_id.asc(),
            Inventory.id.asc(),
        )
    )


def _to_inventory_report_vo(
    inventory: Inventory,
    part: Part,
    category_name: str | None,
    warehouse_name: str | None,
    location_code: str | None,
) -> InventoryReportVO:
    """库存报表行 ORM 转 VO，补齐分类、仓库、库位与金额。"""
    return InventoryReportVO(
        part_id=part.id,
        part_code=part.part_code,
        part_name=part.part_name,
        spec=part.spec,
        unit=part.unit,
        category_id=part.category_id,
        category_name=category_name,
        warehouse_id=inventory.warehouse_id,
        warehouse_name=warehouse_name,
        location_id=inventory.location_id,
        location_code=location_code,
        quantity=inventory.quantity,
        item_count=inventory.item_count,
        locked_qty=inventory.locked_qty,
        avg_cost=inventory.avg_cost,
        amount=_money(Decimal(inventory.quantity) * Decimal(inventory.avg_cost)),
        safety_stock=part.safety_stock,
        max_stock=part.max_stock,
    )


async def list_inventory_report(
    db: AsyncSession,
    query: InventoryReportQuery,
) -> InventoryReportResult:
    """库存报表分页：按配件 + 仓库 + 库位汇总，并返回筛选结果合计。"""
    conditions = _inventory_conditions(query)

    total = (
        await db.execute(
            select(func.count(Inventory.id))
            .select_from(Inventory)
            .join(Part, Part.id == Inventory.part_id)
            .where(*conditions)
        )
    ).scalar_one()

    stmt = _inventory_rows_stmt(query)
    rows = (
        await db.execute(
            stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        )
    ).all()

    low_stock_flag = case((and_(*_low_stock_conditions()), 1), else_=0)
    (
        part_kinds,
        total_quantity,
        total_amount,
        low_stock_count,
    ) = (
        await db.execute(
            select(
                func.count(func.distinct(Inventory.part_id)),
                func.coalesce(func.sum(Inventory.quantity), 0),
                func.coalesce(func.sum(INVENTORY_AMOUNT), 0),
                func.coalesce(func.sum(low_stock_flag), 0),
            )
            .select_from(Inventory)
            .join(Part, Part.id == Inventory.part_id)
            .where(*conditions)
        )
    ).one()

    summary = InventoryReportSummaryVO(
        part_kinds=int(part_kinds or 0),
        total_quantity=Decimal(total_quantity or 0),
        total_amount=_money(total_amount),
        low_stock_count=int(low_stock_count or 0),
    )
    return InventoryReportResult(
        list=[_to_inventory_report_vo(*row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
        summary=summary,
    )


# 导出列：表头、宽度、数字格式
_INVENTORY_EXPORT_COLUMNS: list[tuple[str, int]] = [
    ("配件编码", 16),
    ("配件名称", 24),
    ("规格型号", 18),
    ("单位", 8),
    ("配件分类", 16),
    ("仓库", 16),
    ("库位", 12),
    ("库存数量", 12),
    ("锁定数量", 12),
    ("平均成本", 12),
    ("库存金额", 14),
    ("安全库存", 12),
    ("最高库存", 12),
    ("库存状态", 10),
]
# 需要按两位小数展示的列（Excel 列号，从 1 开始）
_INVENTORY_QTY_COLUMNS = {8, 9, 12, 13}
_INVENTORY_COST_COLUMNS = {10}
_INVENTORY_AMOUNT_COLUMNS = {11}


def _is_low_stock(item: InventoryReportVO) -> bool:
    """导出状态列：维护了安全库存且可用数量不足。"""
    return (
        item.safety_stock is not None
        and item.safety_stock > 0
        and item.quantity - item.locked_qty < item.safety_stock
    )


def build_inventory_report_workbook(items: list[InventoryReportVO]) -> bytes:
    """把库存报表行写入 Excel，返回文件字节内容（便于单元测试）。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "库存报表"

    header_fill = PatternFill("solid", fgColor="DDEBF7")
    header_font = Font(bold=True)
    for index, (title, width) in enumerate(_INVENTORY_EXPORT_COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        sheet.column_dimensions[get_column_letter(index)].width = width

    for item in items:
        sheet.append(
            [
                item.part_code,
                item.part_name,
                item.spec or "",
                item.unit or "",
                item.category_name or "",
                item.warehouse_name or "",
                item.location_code or "",
                float(item.quantity),
                float(item.locked_qty),
                float(item.avg_cost),
                float(item.amount),
                float(item.safety_stock) if item.safety_stock is not None else None,
                float(item.max_stock) if item.max_stock is not None else None,
                "低库存" if _is_low_stock(item) else "正常",
            ]
        )

    for row in range(2, sheet.max_row + 1):
        for column in _INVENTORY_QTY_COLUMNS:
            sheet.cell(row=row, column=column).number_format = "0.00"
        for column in _INVENTORY_COST_COLUMNS:
            sheet.cell(row=row, column=column).number_format = "0.0000"
        for column in _INVENTORY_AMOUNT_COLUMNS:
            sheet.cell(row=row, column=column).number_format = "#,##0.00"

    if items:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

    summary_sheet = workbook.create_sheet("汇总")
    summary_sheet.append(["指标", "数值"])
    for cell in summary_sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
    summary_sheet.append(["配件种类", len({item.part_id for item in items})])
    summary_sheet.append(
        ["库存总数量", float(sum((item.quantity for item in items), Decimal(0)))]
    )
    summary_sheet.append(
        ["库存总金额", float(sum((item.amount for item in items), Decimal(0)))]
    )
    summary_sheet.append(
        ["低库存记录数", sum(1 for item in items if _is_low_stock(item))]
    )
    summary_sheet.column_dimensions["A"].width = 18
    summary_sheet.column_dimensions["B"].width = 18
    for row in range(2, summary_sheet.max_row + 1):
        summary_sheet.cell(row=row, column=2).number_format = "#,##0.00"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def export_inventory_report(
    db: AsyncSession,
    query: InventoryReportQuery,
) -> bytes:
    """导出库存报表 Excel（忽略分页，导出当前筛选条件下的全部数据）。"""
    rows = (await db.execute(_inventory_rows_stmt(query))).all()
    items = [_to_inventory_report_vo(*row) for row in rows]
    return build_inventory_report_workbook(items)



# ---------------------------------------------------------------- 流水报表
def _transaction_conditions(
    query: TransactionReportQuery,
) -> list[ColumnElement[bool]]:
    """构造流水报表查询条件（不限制逻辑删除，保留历史流水）。"""
    conditions: list[ColumnElement[bool]] = []

    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                Part.part_code.like(keyword),
                Part.part_name.like(keyword),
                InventoryTransaction.ref_no.like(keyword),
            )
        )
    if query.part_id is not None:
        conditions.append(InventoryTransaction.part_id == query.part_id)
    if query.warehouse_id is not None:
        conditions.append(
            InventoryTransaction.warehouse_id == query.warehouse_id
        )
    if query.biz_type:
        conditions.append(InventoryTransaction.biz_type == query.biz_type)
    if query.ref_type:
        conditions.append(InventoryTransaction.ref_type == query.ref_type)
    if query.ref_no:
        conditions.append(
            InventoryTransaction.ref_no.like(f"%{query.ref_no.strip()}%")
        )
    if query.start_time is not None:
        conditions.append(InventoryTransaction.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(InventoryTransaction.created_at <= query.end_time)

    return conditions


def _transaction_rows_stmt(query: TransactionReportQuery) -> Any:
    """流水报表明细查询。"""
    return (
        select(InventoryTransaction, Part, Warehouse, WarehouseLocation)
        .outerjoin(Part, Part.id == InventoryTransaction.part_id)
        .outerjoin(Warehouse, Warehouse.id == InventoryTransaction.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == InventoryTransaction.location_id,
        )
        .where(*_transaction_conditions(query))
        .order_by(
            InventoryTransaction.created_at.desc(),
            InventoryTransaction.id.desc(),
        )
    )


def _to_transaction_report_vo(
    transaction: InventoryTransaction,
    part: Part | None,
    warehouse: Warehouse | None,
    location: WarehouseLocation | None,
) -> TransactionReportVO:
    """流水 ORM 转报表 VO，补齐配件、仓库与库位展示字段。"""
    vo = TransactionReportVO.model_validate(transaction)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
    vo.warehouse_name = warehouse.name if warehouse is not None else None
    vo.location_code = location.location_code if location is not None else None
    return vo


def _sum_by_biz_type(biz_type: str, *, negative: bool = False) -> Any:
    """按业务类型汇总变动数量；出库类取相反数，使合计为正数。"""
    expression: Any = InventoryTransaction.change_qty
    if negative:
        expression = -expression
    return func.coalesce(
        func.sum(
            case(
                (InventoryTransaction.biz_type == biz_type, expression),
                else_=0,
            )
        ),
        0,
    )


async def list_transaction_report(
    db: AsyncSession,
    query: TransactionReportQuery,
) -> TransactionReportResult:
    """流水报表分页，合计按当前筛选条件下的全部流水计算。"""
    conditions = _transaction_conditions(query)

    total = (
        await db.execute(
            select(func.count(InventoryTransaction.id))
            .select_from(InventoryTransaction)
            .outerjoin(Part, Part.id == InventoryTransaction.part_id)
            .where(*conditions)
        )
    ).scalar_one()

    rows = (
        await db.execute(
            _transaction_rows_stmt(query)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
    ).all()

    (
        in_qty,
        out_qty,
        transfer_in_qty,
        transfer_out_qty,
        adjust_in_qty,
        adjust_out_qty,
        net_qty,
    ) = (
        await db.execute(
            select(
                _sum_by_biz_type(BizType.IN),
                _sum_by_biz_type(BizType.OUT, negative=True),
                _sum_by_biz_type(BizType.TRANSFER_IN),
                _sum_by_biz_type(BizType.TRANSFER_OUT, negative=True),
                _sum_by_biz_type(BizType.ADJUST_IN),
                _sum_by_biz_type(BizType.ADJUST_OUT, negative=True),
                func.coalesce(func.sum(InventoryTransaction.change_qty), 0),
            )
            .select_from(InventoryTransaction)
            .outerjoin(Part, Part.id == InventoryTransaction.part_id)
            .where(*conditions)
        )
    ).one()

    summary = TransactionReportSummaryVO(
        in_qty=Decimal(in_qty or 0),
        out_qty=Decimal(out_qty or 0),
        transfer_in_qty=Decimal(transfer_in_qty or 0),
        transfer_out_qty=Decimal(transfer_out_qty or 0),
        adjust_in_qty=Decimal(adjust_in_qty or 0),
        adjust_out_qty=Decimal(adjust_out_qty or 0),
        net_qty=Decimal(net_qty or 0),
    )
    return TransactionReportResult(
        list=[_to_transaction_report_vo(*row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
        summary=summary,
    )



# ---------------------------------------------------------------- 单车成本
def _work_order_cost_conditions(
    query: VehicleCostQuery,
) -> list[ColumnElement[bool]]:
    """单车成本中纳入统计的工单条件：已完工 / 已结算。"""
    conditions: list[ColumnElement[bool]] = [
        WorkOrder.is_deleted == 0,
        WorkOrder.status.in_(
            (WorkOrderStatus.FINISHED, WorkOrderStatus.SETTLED)
        ),
    ]
    if query.start_time is not None:
        conditions.append(WorkOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(WorkOrder.created_at <= query.end_time)
    return conditions


def _vehicle_conditions(query: VehicleCostQuery) -> list[ColumnElement[bool]]:
    """构造车辆维度筛选条件。"""
    conditions: list[ColumnElement[bool]] = [Vehicle.is_deleted == 0]
    if query.vehicle_id is not None:
        conditions.append(Vehicle.id == query.vehicle_id)
    if query.model_id is not None:
        conditions.append(Vehicle.model_id == query.model_id)
    if query.department:
        conditions.append(Vehicle.department == query.department.strip())
    return conditions


def _vehicle_cost_base_stmt(query: VehicleCostQuery) -> Any:
    """车辆 LEFT JOIN 工单成本聚合子查询，无维修记录也保留车辆行。"""
    cost_subquery = (
        select(
            WorkOrder.vehicle_id.label("vehicle_id"),
            func.count(WorkOrder.id).label("repair_count"),
            func.coalesce(func.sum(WorkOrder.total_parts_cost), 0).label(
                "total_parts_cost"
            ),
            func.coalesce(func.sum(WorkOrder.total_labor_cost), 0).label(
                "total_labor_cost"
            ),
            func.max(
                func.coalesce(WorkOrder.in_at, WorkOrder.created_at)
            ).label("last_repair_at"),
        )
        .where(*_work_order_cost_conditions(query))
        .group_by(WorkOrder.vehicle_id)
        .subquery()
    )

    parts_cost = func.coalesce(cost_subquery.c.total_parts_cost, 0)
    labor_cost = func.coalesce(cost_subquery.c.total_labor_cost, 0)
    total_cost = parts_cost + labor_cost

    return (
        select(
            Vehicle.id.label("vehicle_id"),
            Vehicle.plate_no.label("plate_no"),
            Vehicle.model_id.label("model_id"),
            VehicleModel.model_name.label("model_name"),
            Vehicle.department.label("department"),
            func.coalesce(cost_subquery.c.repair_count, 0).label("repair_count"),
            parts_cost.label("total_parts_cost"),
            labor_cost.label("total_labor_cost"),
            total_cost.label("total_cost"),
            cost_subquery.c.last_repair_at.label("last_repair_at"),
        )
        .outerjoin(VehicleModel, VehicleModel.id == Vehicle.model_id)
        .outerjoin(
            cost_subquery,
            cost_subquery.c.vehicle_id == Vehicle.id,
        )
        .where(*_vehicle_conditions(query))
    )


def _to_vehicle_cost_vo(
    vehicle_id: int,
    plate_no: str,
    model_id: int | None,
    model_name: str | None,
    department: str | None,
    repair_count: int,
    total_parts_cost: Decimal,
    total_labor_cost: Decimal,
    total_cost: Decimal,
    last_repair_at: datetime | None,
) -> VehicleCostVO:
    """单车成本行转 VO。"""
    return VehicleCostVO(
        vehicle_id=vehicle_id,
        plate_no=plate_no,
        model_id=model_id,
        model_name=model_name,
        department=department,
        repair_count=int(repair_count or 0),
        total_parts_cost=_money(total_parts_cost),
        total_labor_cost=_money(total_labor_cost),
        total_cost=_money(total_cost),
        last_repair_at=last_repair_at,
    )


async def list_vehicle_cost_report(
    db: AsyncSession,
    query: VehicleCostQuery,
) -> VehicleCostResult:
    """单车成本分页：按总成本倒序，合计统计当前筛选下的全部车辆。"""
    base = _vehicle_cost_base_stmt(query)
    stats = base.subquery()

    (
        vehicle_count,
        repair_count,
        total_parts_cost,
        total_labor_cost,
        total_cost,
    ) = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(stats.c.repair_count), 0),
                func.coalesce(func.sum(stats.c.total_parts_cost), 0),
                func.coalesce(func.sum(stats.c.total_labor_cost), 0),
                func.coalesce(func.sum(stats.c.total_cost), 0),
            ).select_from(stats)
        )
    ).one()

    rows = (
        await db.execute(
            base.order_by(
                literal_column("total_cost").desc(),
                Vehicle.plate_no.asc(),
            )
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
    ).all()

    summary = VehicleCostSummaryVO(
        vehicle_count=int(vehicle_count or 0),
        repair_count=int(repair_count or 0),
        total_parts_cost=_money(total_parts_cost),
        total_labor_cost=_money(total_labor_cost),
        total_cost=_money(total_cost),
    )
    return VehicleCostResult(
        list=[_to_vehicle_cost_vo(*row) for row in rows],
        total=int(vehicle_count or 0),
        page=query.page,
        page_size=query.page_size,
        summary=summary,
    )



# ---------------------------------------------------------------- 首页看板
def _month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """返回当前自然月的起止时间（左闭右开）。"""
    current = now or datetime.now()
    start = current.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    if start.month == 12:
        next_start = start.replace(year=start.year + 1, month=1)
    else:
        next_start = start.replace(month=start.month + 1)
    return start, next_start


async def get_dashboard(db: AsyncSession) -> DashboardVO:
    """首页看板：基础档案、库存、待办与本月出入库金额。"""
    part_count = (
        await db.execute(
            select(func.count(Part.id)).where(Part.is_deleted == 0)
        )
    ).scalar_one()
    vehicle_count = (
        await db.execute(
            select(func.count(Vehicle.id)).where(Vehicle.is_deleted == 0)
        )
    ).scalar_one()
    warehouse_count = (
        await db.execute(
            select(func.count(Warehouse.id)).where(Warehouse.is_deleted == 0)
        )
    ).scalar_one()

    inventory_quantity, inventory_amount = (
        await db.execute(
            select(
                func.coalesce(func.sum(Inventory.quantity), 0),
                func.coalesce(func.sum(INVENTORY_AMOUNT), 0),
            )
            .select_from(Inventory)
            .join(Part, Part.id == Inventory.part_id)
            .where(Inventory.is_deleted == 0, Part.is_deleted == 0)
        )
    ).one()

    low_stock_count = (
        await db.execute(
            select(func.count(func.distinct(Inventory.part_id)))
            .select_from(Inventory)
            .join(Part, Part.id == Inventory.part_id)
            .where(
                Inventory.is_deleted == 0,
                Part.is_deleted == 0,
                *_low_stock_conditions(),
            )
        )
    ).scalar_one()

    pending_inbound_count = (
        await db.execute(
            select(func.count(InboundOrder.id)).where(
                InboundOrder.is_deleted == 0,
                InboundOrder.status == OrderStatus.PENDING,
            )
        )
    ).scalar_one()
    pending_outbound_count = (
        await db.execute(
            select(func.count(OutboundOrder.id)).where(
                OutboundOrder.is_deleted == 0,
                OutboundOrder.status == OrderStatus.PENDING,
            )
        )
    ).scalar_one()
    repairing_work_order_count = (
        await db.execute(
            select(func.count(WorkOrder.id)).where(
                WorkOrder.is_deleted == 0,
                WorkOrder.status == WorkOrderStatus.REPAIRING,
            )
        )
    ).scalar_one()

    month_start, next_month = _month_bounds()
    inbound_at = func.coalesce(InboundOrder.inbound_at, InboundOrder.created_at)
    outbound_at = func.coalesce(
        OutboundOrder.outbound_at, OutboundOrder.created_at
    )
    month_inbound_amount = (
        await db.execute(
            select(func.coalesce(func.sum(InboundOrder.total_amount), 0)).where(
                InboundOrder.is_deleted == 0,
                InboundOrder.status == OrderStatus.COMPLETED,
                inbound_at >= month_start,
                inbound_at < next_month,
            )
        )
    ).scalar_one()
    month_outbound_amount = (
        await db.execute(
            select(func.coalesce(func.sum(OutboundOrder.total_amount), 0)).where(
                OutboundOrder.is_deleted == 0,
                OutboundOrder.status == OrderStatus.COMPLETED,
                outbound_at >= month_start,
                outbound_at < next_month,
            )
        )
    ).scalar_one()

    return DashboardVO(
        part_count=int(part_count or 0),
        vehicle_count=int(vehicle_count or 0),
        warehouse_count=int(warehouse_count or 0),
        inventory_quantity=Decimal(inventory_quantity or 0),
        inventory_amount=_money(inventory_amount),
        low_stock_count=int(low_stock_count or 0),
        pending_inbound_count=int(pending_inbound_count or 0),
        pending_outbound_count=int(pending_outbound_count or 0),
        repairing_work_order_count=int(repairing_work_order_count or 0),
        month_inbound_amount=_money(month_inbound_amount),
        month_outbound_amount=_money(month_outbound_amount),
    )

