"""出库单 Schema（outbound_order、outbound_order_item）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "OutboundOrderCreate",
    "OutboundOrderDetailVO",
    "OutboundOrderItemCreate",
    "OutboundOrderItemVO",
    "OutboundOrderQuery",
    "OutboundOrderUpdate",
    "OutboundOrderVO",
]


class OutboundOrderItemCreate(SchemaBase):
    """出库单明细（扫码出库时带 inventory_item_id / scan_code / scan_type）。"""

    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="数量")
    unit: str | None = Field(default=None, max_length=20, description="单位")
    unit_cost: Decimal | None = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=4,
        description="单位成本",
    )
    amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
        description="金额，不传时按 数量 × 单位成本 由后端计算",
    )
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    location_id: int | None = Field(default=None, description="库位ID")
    scan_code: str | None = Field(
        default=None, max_length=100, description="扫码原始编码"
    )
    scan_type: str | None = Field(
        default=None, max_length=20, description="BARCODE/QRCODE/MANUAL"
    )
    scan_at: datetime | None = Field(default=None, description="扫码时间")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class OutboundOrderCreate(SchemaBase):
    """新建出库单（order_no、total_amount 由服务层生成）。"""

    warehouse_id: int = Field(description="出库仓库ID")
    outbound_type: str = Field(
        default="REPAIR", max_length=20, description="REPAIR/SALE/RETURN/TRANSFER/SCRAP"
    )
    vehicle_id: int | None = Field(default=None, description="关联车辆ID")
    work_order_id: int | None = Field(default=None, description="关联维修工单ID")
    receiver_id: int | None = Field(default=None, description="领用人ID")
    scan_mode: int = Field(default=0, ge=0, le=1, description="是否扫码模式 1是 0否")
    scanner_id: int | None = Field(default=None, description="扫码操作人ID")
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[OutboundOrderItemCreate] = Field(
        default_factory=list, description="出库明细"
    )


class OutboundOrderUpdate(SchemaBase):
    """编辑草稿出库单；传 items 时整体替换原明细。"""

    warehouse_id: int | None = Field(default=None, description="出库仓库ID")
    outbound_type: str | None = Field(
        default=None, max_length=20, description="REPAIR/SALE/RETURN/TRANSFER/SCRAP"
    )
    vehicle_id: int | None = Field(default=None, description="关联车辆ID")
    work_order_id: int | None = Field(default=None, description="关联维修工单ID")
    receiver_id: int | None = Field(default=None, description="领用人ID")
    scan_mode: int | None = Field(default=None, ge=0, le=1, description="是否扫码模式")
    scanner_id: int | None = Field(default=None, description="扫码操作人ID")
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[OutboundOrderItemCreate] | None = Field(
        default=None, description="出库明细，传 null 表示不修改明细"
    )


class OutboundOrderQuery(PageQuery):
    """出库单分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="出库单号/备注模糊搜索"
    )
    order_no: str | None = Field(default=None, max_length=50, description="出库单号")
    warehouse_id: int | None = Field(default=None, description="出库仓库ID")
    outbound_type: str | None = Field(
        default=None, max_length=20, description="REPAIR/SALE/RETURN/TRANSFER/SCRAP"
    )
    vehicle_id: int | None = Field(default=None, description="关联车辆ID")
    work_order_id: int | None = Field(default=None, description="关联维修工单ID")
    receiver_id: int | None = Field(default=None, description="领用人ID")
    status: int | None = Field(
        default=None, ge=1, le=4, description="1草稿 2待审 3已出库 4作废"
    )
    scan_mode: int | None = Field(default=None, ge=0, le=1, description="是否扫码模式")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class OutboundOrderVO(AuditVO):
    """出库单主表详情。"""

    id: int = Field(description="主键")
    order_no: str = Field(description="出库单号")
    warehouse_id: int = Field(description="出库仓库ID")
    outbound_type: str = Field(description="REPAIR/SALE/RETURN/TRANSFER/SCRAP")
    vehicle_id: int | None = Field(default=None, description="关联车辆ID")
    work_order_id: int | None = Field(default=None, description="关联维修工单ID")
    receiver_id: int | None = Field(default=None, description="领用人ID")
    total_amount: JsonDecimal | None = Field(default=None, description="总金额")
    status: int = Field(description="1草稿 2待审 3已出库 4作废")
    scan_mode: int = Field(description="是否扫码模式")
    scanner_id: int | None = Field(default=None, description="扫码操作人ID")
    operator_id: int | None = Field(default=None, description="经办人ID")
    audit_user_id: int | None = Field(default=None, description="审核人ID")
    audit_at: datetime | None = Field(default=None, description="审核时间")
    outbound_at: datetime | None = Field(default=None, description="出库时间")
    remark: str | None = Field(default=None, description="备注")
    warehouse_name: str | None = Field(default=None, description="仓库名称（扩展字段）")
    vehicle_plate_no: str | None = Field(default=None, description="车牌号（扩展字段）")


class OutboundOrderItemVO(AuditVO):
    """出库单明细详情。"""

    id: int = Field(description="主键")
    order_id: int = Field(description="出库单ID")
    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    quantity: JsonDecimal = Field(description="数量")
    unit: str | None = Field(default=None, description="单位")
    unit_cost: JsonDecimal | None = Field(default=None, description="单位成本")
    amount: JsonDecimal | None = Field(default=None, description="金额")
    batch_no: str | None = Field(default=None, description="批次号")
    location_id: int | None = Field(default=None, description="库位ID")
    scan_code: str | None = Field(default=None, description="扫码原始编码")
    scan_type: str | None = Field(default=None, description="BARCODE/QRCODE/MANUAL")
    scan_at: datetime | None = Field(default=None, description="扫码时间")
    remark: str | None = Field(default=None, description="备注")
    part_code: str | None = Field(default=None, description="配件编码（扩展字段）")
    part_name: str | None = Field(default=None, description="配件名称（扩展字段）")
    spec: str | None = Field(default=None, description="规格型号（扩展字段）")
    item_code: str | None = Field(default=None, description="库存件编码（扩展字段）")


class OutboundOrderDetailVO(OutboundOrderVO):
    """出库单详情（含明细）。"""

    items: list[OutboundOrderItemVO] = Field(
        default_factory=list, description="出库明细"
    )
