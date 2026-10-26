"""维修工单 Schema（work_order、work_order_part）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, SchemaBase

__all__ = [
    "WorkOrderCreate",
    "WorkOrderDetailVO",
    "WorkOrderPartCreate",
    "WorkOrderPartQuery",
    "WorkOrderPartVO",
    "WorkOrderQuery",
    "WorkOrderSettle",
    "WorkOrderUpdate",
    "WorkOrderVO",
]


class WorkOrderCreate(SchemaBase):
    """新建维修工单（order_no 由服务层生成）。"""

    vehicle_id: int = Field(description="车辆ID")
    repair_type: str = Field(
        default="REPAIR", max_length=20, description="MAINTENANCE/REPAIR/ACCIDENT"
    )
    description: str | None = Field(default=None, description="故障描述")
    repair_man_id: int | None = Field(default=None, description="维修负责人ID")
    in_at: datetime | None = Field(default=None, description="进厂时间")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WorkOrderUpdate(SchemaBase):
    """编辑维修工单。"""

    repair_type: str | None = Field(
        default=None, max_length=20, description="MAINTENANCE/REPAIR/ACCIDENT"
    )
    description: str | None = Field(default=None, description="故障描述")
    repair_man_id: int | None = Field(default=None, description="维修负责人ID")
    in_at: datetime | None = Field(default=None, description="进厂时间")
    out_at: datetime | None = Field(default=None, description="出厂时间")
    status: int | None = Field(
        default=None, ge=1, le=4, description="1待修 2维修中 3已完工 4已结算"
    )
    total_parts_cost: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2, description="配件总成本"
    )
    total_labor_cost: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2, description="工时费"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WorkOrderQuery(PageQuery):
    """维修工单分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="工单号模糊搜索"
    )
    order_no: str | None = Field(default=None, max_length=50, description="工单号")
    vehicle_id: int | None = Field(default=None, description="车辆ID")
    repair_type: str | None = Field(
        default=None, max_length=20, description="MAINTENANCE/REPAIR/ACCIDENT"
    )
    repair_man_id: int | None = Field(default=None, description="维修负责人ID")
    status: int | None = Field(
        default=None, ge=1, le=4, description="1待修 2维修中 3已完工 4已结算"
    )
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class WorkOrderVO(AuditVO):
    """维修工单详情。"""

    id: int = Field(description="主键")
    order_no: str = Field(description="工单号")
    vehicle_id: int = Field(description="车辆ID")
    plate_no: str | None = Field(default=None, description="车牌号（车辆扩展字段）")
    repair_type: str = Field(description="MAINTENANCE/REPAIR/ACCIDENT")
    description: str | None = Field(default=None, description="故障描述")
    repair_man_id: int | None = Field(default=None, description="维修负责人ID")
    repair_man_name: str | None = Field(
        default=None, description="维修负责人姓名（用户扩展字段）"
    )
    in_at: datetime | None = Field(default=None, description="进厂时间")
    out_at: datetime | None = Field(default=None, description="出厂时间")
    status: int = Field(description="1待修 2维修中 3已完工 4已结算")
    total_parts_cost: Decimal | None = Field(default=None, description="配件总成本")
    total_labor_cost: Decimal | None = Field(default=None, description="工时费")
    remark: str | None = Field(default=None, description="备注")


class WorkOrderPartCreate(SchemaBase):
    """工单领料记录（出库审核通过时由服务层写入）。"""

    work_order_id: int = Field(description="工单ID")
    outbound_item_id: int | None = Field(default=None, description="出库明细ID")
    part_id: int = Field(description="配件ID")
    quantity: Decimal | None = Field(
        default=Decimal(0), ge=0, max_digits=12, decimal_places=2, description="数量"
    )
    cost: Decimal | None = Field(
        default=Decimal(0), ge=0, max_digits=14, decimal_places=2, description="成本"
    )


class WorkOrderPartQuery(PageQuery):
    """工单领料记录查询条件。"""

    work_order_id: int | None = Field(default=None, description="工单ID")
    outbound_item_id: int | None = Field(default=None, description="出库明细ID")
    part_id: int | None = Field(default=None, description="配件ID")


class WorkOrderPartVO(AuditVO):
    """工单领料记录详情。"""

    id: int = Field(description="主键")
    work_order_id: int = Field(description="工单ID")
    outbound_item_id: int | None = Field(default=None, description="出库明细ID")
    part_id: int = Field(description="配件ID")
    part_code: str | None = Field(default=None, description="配件编码（扩展字段）")
    part_name: str | None = Field(default=None, description="配件名称（扩展字段）")
    spec: str | None = Field(default=None, description="规格型号（扩展字段）")
    unit: str | None = Field(default=None, description="单位（扩展字段）")
    quantity: Decimal | None = Field(default=None, description="数量")
    cost: Decimal | None = Field(default=None, description="成本")


class WorkOrderSettle(SchemaBase):
    """工单结算：填写工时费（配件成本在完工时自动汇总）。"""

    total_labor_cost: Decimal = Field(
        ge=0,
        max_digits=14,
        decimal_places=2,
        description="工时费",
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class WorkOrderDetailVO(WorkOrderVO):
    """维修工单详情（含领料记录）。"""

    parts: list[WorkOrderPartVO] = Field(default_factory=list, description="领料记录")
