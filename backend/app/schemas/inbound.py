"""入库单 Schema（inbound_order、inbound_order_item）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "InboundOrderCreate",
    "InboundOrderDetailVO",
    "InboundOrderItemCreate",
    "InboundOrderItemVO",
    "InboundOrderQuery",
    "InboundOrderUpdate",
    "InboundOrderVO",
]


class InboundOrderItemCreate(SchemaBase):
    """入库单明细（新建/编辑草稿时随主单一起提交）。"""

    part_id: int = Field(description="配件ID")
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="数量")
    unit: str | None = Field(default=None, max_length=20, description="单位")
    unit_price: Decimal = Field(
        default=Decimal(0), ge=0, max_digits=12, decimal_places=4, description="单价"
    )
    amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
        description="金额，不传时按 数量 × 单价 由后端计算",
    )
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    production_date: date | None = Field(default=None, description="生产日期")
    expire_date: date | None = Field(default=None, description="到期日期")
    location_id: int | None = Field(default=None, description="库位ID")
    track_by_item: int = Field(default=0, ge=0, le=1, description="是否逐件追踪")
    scan_code: str | None = Field(
        default=None, max_length=100, description="扫码原始编码"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class InboundOrderCreate(SchemaBase):
    """新建入库单（order_no、total_amount 由服务层生成）。"""

    supplier_id: int | None = Field(default=None, description="供应商ID")
    warehouse_id: int = Field(description="入库仓库ID")
    inbound_type: str = Field(
        default="PURCHASE", max_length=20, description="PURCHASE/RETURN/TRANSFER/ADJUST"
    )
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[InboundOrderItemCreate] = Field(
        default_factory=list, description="入库明细"
    )


class InboundOrderUpdate(SchemaBase):
    """编辑草稿入库单；传 items 时整体替换原明细。"""

    supplier_id: int | None = Field(default=None, description="供应商ID")
    warehouse_id: int | None = Field(default=None, description="入库仓库ID")
    inbound_type: str | None = Field(
        default=None, max_length=20, description="PURCHASE/RETURN/TRANSFER/ADJUST"
    )
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[InboundOrderItemCreate] | None = Field(
        default=None, description="入库明细，传 null 表示不修改明细"
    )


class InboundOrderQuery(PageQuery):
    """入库单分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="入库单号模糊搜索"
    )
    order_no: str | None = Field(default=None, max_length=50, description="入库单号")
    supplier_id: int | None = Field(default=None, description="供应商ID")
    warehouse_id: int | None = Field(default=None, description="入库仓库ID")
    inbound_type: str | None = Field(
        default=None, max_length=20, description="PURCHASE/RETURN/TRANSFER/ADJUST"
    )
    status: int | None = Field(
        default=None, ge=1, le=4, description="1草稿 2待审 3已入库 4作废"
    )
    operator_id: int | None = Field(default=None, description="经办人ID")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class InboundOrderVO(AuditVO):
    """入库单主表详情。"""

    id: int = Field(description="主键")
    order_no: str = Field(description="入库单号")
    supplier_id: int | None = Field(default=None, description="供应商ID")
    warehouse_id: int = Field(description="入库仓库ID")
    inbound_type: str = Field(description="PURCHASE/RETURN/TRANSFER/ADJUST")
    total_amount: JsonDecimal | None = Field(default=None, description="总金额")
    status: int = Field(description="1草稿 2待审 3已入库 4作废")
    operator_id: int | None = Field(default=None, description="经办人ID")
    audit_user_id: int | None = Field(default=None, description="审核人ID")
    audit_at: datetime | None = Field(default=None, description="审核时间")
    inbound_at: datetime | None = Field(default=None, description="入库时间")
    remark: str | None = Field(default=None, description="备注")
    warehouse_name: str | None = Field(default=None, description="仓库名称（扩展字段）")
    supplier_name: str | None = Field(
        default=None, description="供应商名称（扩展字段）"
    )


class InboundOrderItemVO(AuditVO):
    """入库单明细详情。"""

    id: int = Field(description="主键")
    order_id: int = Field(description="入库单ID")
    part_id: int = Field(description="配件ID")
    quantity: JsonDecimal = Field(description="数量")
    unit: str | None = Field(default=None, description="单位")
    unit_price: JsonDecimal = Field(description="单价")
    amount: JsonDecimal | None = Field(default=None, description="金额")
    batch_no: str | None = Field(default=None, description="批次号")
    production_date: date | None = Field(default=None, description="生产日期")
    expire_date: date | None = Field(default=None, description="到期日期")
    location_id: int | None = Field(default=None, description="库位ID")
    track_by_item: int = Field(description="是否逐件追踪")
    generate_item_qty: int | None = Field(default=None, description="本次生成实例数量")
    generated: int = Field(description="是否已生成实例")
    scan_code: str | None = Field(default=None, description="扫码原始编码")
    remark: str | None = Field(default=None, description="备注")
    part_code: str | None = Field(default=None, description="配件编码（扩展字段）")
    part_name: str | None = Field(default=None, description="配件名称（扩展字段）")
    spec: str | None = Field(default=None, description="规格型号（扩展字段）")


class InboundOrderDetailVO(InboundOrderVO):
    """入库单详情（含明细）。"""

    items: list[InboundOrderItemVO] = Field(
        default_factory=list, description="入库明细"
    )
