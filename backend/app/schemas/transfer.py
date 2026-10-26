"""调拨单 Schema（transfer_order、transfer_order_item）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "TransferOrderCreate",
    "TransferOrderDetailVO",
    "TransferOrderItemCreate",
    "TransferOrderItemVO",
    "TransferOrderQuery",
    "TransferOrderUpdate",
    "TransferOrderVO",
]


class TransferOrderItemCreate(SchemaBase):
    """调拨单明细。"""

    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="数量")
    from_location_id: int | None = Field(default=None, description="调出库位ID")
    to_location_id: int | None = Field(default=None, description="调入库位ID")
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class TransferOrderCreate(SchemaBase):
    """新建调拨单（order_no 由服务层生成）。"""

    from_warehouse_id: int = Field(description="调出仓库ID")
    to_warehouse_id: int = Field(description="调入仓库ID")
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[TransferOrderItemCreate] = Field(
        default_factory=list, description="调拨明细"
    )


class TransferOrderUpdate(SchemaBase):
    """编辑草稿调拨单；传 items 时整体替换原明细。"""

    from_warehouse_id: int | None = Field(default=None, description="调出仓库ID")
    to_warehouse_id: int | None = Field(default=None, description="调入仓库ID")
    operator_id: int | None = Field(default=None, description="经办人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[TransferOrderItemCreate] | None = Field(
        default=None, description="调拨明细，传 null 表示不修改明细"
    )


class TransferOrderQuery(PageQuery):
    """调拨单分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="调拨单号模糊搜索"
    )
    order_no: str | None = Field(default=None, max_length=50, description="调拨单号")
    from_warehouse_id: int | None = Field(default=None, description="调出仓库ID")
    to_warehouse_id: int | None = Field(default=None, description="调入仓库ID")
    status: int | None = Field(
        default=None, ge=1, le=5, description="1草稿 2待审 3已调出 4已调入 5作废"
    )
    operator_id: int | None = Field(default=None, description="经办人ID")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class TransferOrderVO(AuditVO):
    """调拨单主表详情。"""

    id: int = Field(description="主键")
    order_no: str = Field(description="调拨单号")
    from_warehouse_id: int = Field(description="调出仓库ID")
    to_warehouse_id: int = Field(description="调入仓库ID")
    status: int = Field(description="1草稿 2待审 3已调出 4已调入 5作废")
    operator_id: int | None = Field(default=None, description="经办人ID")
    audit_user_id: int | None = Field(default=None, description="审核人ID")
    transfer_at: datetime | None = Field(default=None, description="调拨时间")
    remark: str | None = Field(default=None, description="备注")
    from_warehouse_name: str | None = Field(default=None, description="调出仓库名称")
    to_warehouse_name: str | None = Field(default=None, description="调入仓库名称")


class TransferOrderItemVO(AuditVO):
    """调拨单明细详情（含配件 / 库存件 / 库位展示字段）。"""

    id: int = Field(description="主键")
    order_id: int = Field(description="调拨单ID")
    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    quantity: JsonDecimal = Field(description="数量")
    from_location_id: int | None = Field(default=None, description="调出库位ID")
    to_location_id: int | None = Field(default=None, description="调入库位ID")
    batch_no: str | None = Field(default=None, description="批次号")
    remark: str | None = Field(default=None, description="备注")
    part_code: str | None = Field(default=None, description="配件编码")
    part_name: str | None = Field(default=None, description="配件名称")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str | None = Field(default=None, description="单位")
    item_code: str | None = Field(default=None, description="库存件编码")
    from_location_code: str | None = Field(default=None, description="调出库位编码")
    to_location_code: str | None = Field(default=None, description="调入库位编码")


class TransferOrderDetailVO(TransferOrderVO):
    """调拨单详情（含明细）。"""

    items: list[TransferOrderItemVO] = Field(
        default_factory=list, description="调拨明细"
    )
