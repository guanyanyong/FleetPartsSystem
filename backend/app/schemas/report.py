"""报表 Schema（库存报表、流水报表、单车成本、首页看板）。

报表 VO 的字段来自多表聚合，服务层用 SQLAlchemy `Row` 或 dict 构造，
因此统一继承 `SchemaBase`，支持 `model_validate(row)`。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import PageQuery, PageResult, SchemaBase

__all__ = [
    "DashboardVO",
    "InventoryReportQuery",
    "InventoryReportResult",
    "InventoryReportSummaryVO",
    "InventoryReportVO",
    "TransactionReportQuery",
    "TransactionReportResult",
    "TransactionReportSummaryVO",
    "TransactionReportVO",
    "VehicleCostQuery",
    "VehicleCostResult",
    "VehicleCostSummaryVO",
    "VehicleCostVO",
]


# ---------------------------------------------------------------- 查询条件
class InventoryReportQuery(PageQuery):
    """库存报表查询条件（GET /reports/inventory）。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="配件编码/名称模糊搜索"
    )
    part_id: int | None = Field(default=None, description="配件ID")
    category_id: int | None = Field(default=None, description="配件分类ID")
    warehouse_id: int | None = Field(default=None, description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    low_stock: bool = Field(default=False, description="只看低于安全库存的记录")
    include_zero: bool = Field(default=False, description="是否包含数量为 0 的记录")


class TransactionReportQuery(PageQuery):
    """流水报表查询条件（GET /reports/transaction）。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="配件编码/名称、单号模糊搜索"
    )
    part_id: int | None = Field(default=None, description="配件ID")
    warehouse_id: int | None = Field(default=None, description="仓库ID")
    biz_type: str | None = Field(
        default=None,
        max_length=20,
        description="IN/OUT/TRANSFER_IN/TRANSFER_OUT/ADJUST_IN/ADJUST_OUT",
    )
    ref_type: str | None = Field(
        default=None, max_length=20, description="INBOUND/OUTBOUND/TRANSFER/STOCKTAKE"
    )
    ref_no: str | None = Field(default=None, max_length=50, description="关联单号")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class VehicleCostQuery(PageQuery):
    """单车成本查询条件（GET /reports/vehicle-cost）。"""

    vehicle_id: int | None = Field(default=None, description="车辆ID")
    model_id: int | None = Field(default=None, description="车型ID")
    department: str | None = Field(
        default=None, max_length=50, description="所属车队/部门"
    )
    start_time: datetime | None = Field(
        default=None, description="工单创建时间起（含）"
    )
    end_time: datetime | None = Field(default=None, description="工单创建时间止（含）")


# ---------------------------------------------------------------- 库存报表
class InventoryReportVO(SchemaBase):
    """库存报表一行（配件 + 仓库 + 库位维度）。"""

    part_id: int = Field(description="配件ID")
    part_code: str = Field(description="配件编码")
    part_name: str = Field(description="配件名称")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str | None = Field(default=None, description="基本单位")
    category_id: int | None = Field(default=None, description="配件分类ID")
    category_name: str | None = Field(default=None, description="配件分类名")
    warehouse_id: int = Field(description="仓库ID")
    warehouse_name: str | None = Field(default=None, description="仓库名")
    location_id: int | None = Field(default=None, description="库位ID")
    location_code: str | None = Field(default=None, description="库位编码")
    quantity: Decimal = Field(description="当前数量")
    item_count: int = Field(description="在库实例数")
    locked_qty: Decimal = Field(description="锁定数量")
    avg_cost: Decimal = Field(description="移动加权平均成本")
    amount: Decimal = Field(description="库存金额（数量 × 平均成本）")
    safety_stock: Decimal | None = Field(default=None, description="安全库存")
    max_stock: Decimal | None = Field(default=None, description="最高库存")


class InventoryReportSummaryVO(SchemaBase):
    """库存报表合计。"""

    part_kinds: int = Field(default=0, ge=0, description="配件种类数")
    total_quantity: Decimal = Field(default=Decimal(0), description="库存总数量")
    total_amount: Decimal = Field(default=Decimal(0), description="库存总金额")
    low_stock_count: int = Field(default=0, ge=0, description="低库存记录数")


class InventoryReportResult(PageResult[InventoryReportVO]):
    """库存报表分页结果（分页字段 + 合计）。"""

    summary: InventoryReportSummaryVO = Field(
        default_factory=InventoryReportSummaryVO, description="报表合计"
    )


# ---------------------------------------------------------------- 流水报表
class TransactionReportVO(SchemaBase):
    """流水报表一行。"""

    id: int = Field(description="流水ID")
    part_id: int = Field(description="配件ID")
    part_code: str | None = Field(default=None, description="配件编码")
    part_name: str | None = Field(default=None, description="配件名称")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    warehouse_id: int = Field(description="仓库ID")
    warehouse_name: str | None = Field(default=None, description="仓库名")
    location_id: int | None = Field(default=None, description="库位ID")
    location_code: str | None = Field(default=None, description="库位编码")
    biz_type: str = Field(description="业务类型")
    change_qty: Decimal = Field(description="变动数量")
    before_qty: Decimal = Field(description="变动前数量")
    after_qty: Decimal = Field(description="变动后数量")
    unit_cost: Decimal | None = Field(default=None, description="单位成本")
    ref_type: str = Field(description="单据类型")
    ref_id: int | None = Field(default=None, description="关联单据ID")
    ref_no: str | None = Field(default=None, description="关联单号")
    batch_no: str | None = Field(default=None, description="批次号")
    scan_code: str | None = Field(default=None, description="扫码原始编码")
    operator_id: int | None = Field(default=None, description="操作人ID")
    created_at: datetime = Field(description="创建时间")


class TransactionReportSummaryVO(SchemaBase):
    """流水报表合计（按业务类型汇总数量）。"""

    in_qty: Decimal = Field(default=Decimal(0), description="入库数量")
    out_qty: Decimal = Field(default=Decimal(0), description="出库数量")
    transfer_in_qty: Decimal = Field(default=Decimal(0), description="调拨入库数量")
    transfer_out_qty: Decimal = Field(default=Decimal(0), description="调拨出库数量")
    adjust_in_qty: Decimal = Field(default=Decimal(0), description="盘盈数量")
    adjust_out_qty: Decimal = Field(default=Decimal(0), description="盘亏数量")
    net_qty: Decimal = Field(default=Decimal(0), description="净变动数量")


class TransactionReportResult(PageResult[TransactionReportVO]):
    """流水报表分页结果（分页字段 + 合计）。"""

    summary: TransactionReportSummaryVO = Field(
        default_factory=TransactionReportSummaryVO, description="报表合计"
    )


# ---------------------------------------------------------------- 单车成本
class VehicleCostVO(SchemaBase):
    """单车成本报表一行。"""

    vehicle_id: int = Field(description="车辆ID")
    plate_no: str = Field(description="车牌号")
    model_id: int | None = Field(default=None, description="车型ID")
    model_name: str | None = Field(default=None, description="车型名称")
    department: str | None = Field(default=None, description="所属车队/部门")
    repair_count: int = Field(default=0, ge=0, description="维修工单数")
    total_parts_cost: Decimal = Field(default=Decimal(0), description="配件总成本")
    total_labor_cost: Decimal = Field(default=Decimal(0), description="工时费合计")
    total_cost: Decimal = Field(default=Decimal(0), description="总成本")
    last_repair_at: datetime | None = Field(
        default=None, description="最近一次进厂时间"
    )


class VehicleCostSummaryVO(SchemaBase):
    """单车成本合计。"""

    vehicle_count: int = Field(default=0, ge=0, description="车辆数")
    repair_count: int = Field(default=0, ge=0, description="维修工单数")
    total_parts_cost: Decimal = Field(default=Decimal(0), description="配件总成本")
    total_labor_cost: Decimal = Field(default=Decimal(0), description="工时费合计")
    total_cost: Decimal = Field(default=Decimal(0), description="总成本")


class VehicleCostResult(PageResult[VehicleCostVO]):
    """单车成本分页结果（分页字段 + 合计）。"""

    summary: VehicleCostSummaryVO = Field(
        default_factory=VehicleCostSummaryVO, description="报表合计"
    )


# ---------------------------------------------------------------- 首页看板
class DashboardVO(SchemaBase):
    """首页看板数据（GET /reports/dashboard）。"""

    part_count: int = Field(default=0, ge=0, description="配件种类数")
    vehicle_count: int = Field(default=0, ge=0, description="车辆数")
    warehouse_count: int = Field(default=0, ge=0, description="仓库数")
    inventory_quantity: Decimal = Field(default=Decimal(0), description="库存总数量")
    inventory_amount: Decimal = Field(default=Decimal(0), description="库存总金额")
    low_stock_count: int = Field(default=0, ge=0, description="低库存配件数")
    pending_inbound_count: int = Field(default=0, ge=0, description="待审入库单数")
    pending_outbound_count: int = Field(default=0, ge=0, description="待审出库单数")
    repairing_work_order_count: int = Field(default=0, ge=0, description="维修中工单数")
    month_inbound_amount: Decimal = Field(
        default=Decimal(0), description="本月入库金额"
    )
    month_outbound_amount: Decimal = Field(
        default=Decimal(0), description="本月出库金额"
    )
