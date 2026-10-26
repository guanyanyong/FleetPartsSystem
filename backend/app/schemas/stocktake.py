"""盘点单 Schema（stocktake_order、stocktake_order_item）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "StocktakeOrderCreate",
    "StocktakeOrderDetailVO",
    "StocktakeOrderItemCreate",
    "StocktakeOrderItemUpdate",
    "StocktakeOrderItemVO",
    "StocktakeOrderQuery",
    "StocktakeOrderUpdate",
    "StocktakeOrderVO",
    "StocktakeScanRequest",
]


class StocktakeOrderItemCreate(SchemaBase):
    """盘点单明细（diff_qty 由服务层按账面/实盘计算）。"""

    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    location_id: int | None = Field(default=None, description="库位ID")
    book_qty: Decimal | None = Field(
        default=Decimal(0), max_digits=12, decimal_places=2, description="账面数量"
    )
    actual_qty: Decimal | None = Field(
        default=Decimal(0), max_digits=12, decimal_places=2, description="实盘数量"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class StocktakeOrderCreate(SchemaBase):
    """新建盘点单（order_no 由服务层生成）。"""

    warehouse_id: int = Field(description="盘点仓库ID")
    operator_id: int | None = Field(default=None, description="盘点人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[StocktakeOrderItemCreate] = Field(
        default_factory=list, description="盘点明细"
    )


class StocktakeOrderUpdate(SchemaBase):
    """编辑草稿盘点单；传 items 时整体替换原明细。"""

    warehouse_id: int | None = Field(default=None, description="盘点仓库ID")
    operator_id: int | None = Field(default=None, description="盘点人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    items: list[StocktakeOrderItemCreate] | None = Field(
        default=None, description="盘点明细，传 null 表示不修改明细"
    )


class StocktakeOrderItemUpdate(SchemaBase):
    """修改实盘数量（PUT /stocktake-orders/{id}/items/{itemId}）。"""

    actual_qty: Decimal = Field(
        ge=0, max_digits=12, decimal_places=2, description="实盘数量"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class StocktakeScanRequest(SchemaBase):
    """扫码盘点（POST /stocktake-orders/{id}/scan）。"""

    code: str = Field(
        min_length=1, max_length=255, description="扫码内容（item_code/qrcode）"
    )
    location_id: int | None = Field(default=None, description="当前库位ID")


class StocktakeOrderQuery(PageQuery):
    """盘点单分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="盘点单号模糊搜索"
    )
    order_no: str | None = Field(default=None, max_length=50, description="盘点单号")
    warehouse_id: int | None = Field(default=None, description="盘点仓库ID")
    status: int | None = Field(
        default=None, ge=1, le=4, description="1草稿 2盘点中 3已完成 4作废"
    )
    operator_id: int | None = Field(default=None, description="盘点人ID")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class StocktakeOrderVO(AuditVO):
    """盘点单主表详情。"""

    id: int = Field(description="主键")
    order_no: str = Field(description="盘点单号")
    warehouse_id: int = Field(description="盘点仓库ID")
    status: int = Field(description="1草稿 2盘点中 3已完成 4作废")
    operator_id: int | None = Field(default=None, description="盘点人ID")
    audit_user_id: int | None = Field(default=None, description="审核人ID")
    stocktake_at: datetime | None = Field(default=None, description="盘点时间")
    remark: str | None = Field(default=None, description="备注")
    warehouse_name: str | None = Field(default=None, description="仓库名称（扩展字段）")


class StocktakeOrderItemVO(AuditVO):
    """盘点单明细详情。"""

    id: int = Field(description="主键")
    order_id: int = Field(description="盘点单ID")
    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    location_id: int | None = Field(default=None, description="库位ID")
    book_qty: JsonDecimal | None = Field(default=None, description="账面数量")
    actual_qty: JsonDecimal | None = Field(default=None, description="实盘数量")
    diff_qty: JsonDecimal | None = Field(default=None, description="差异数量")
    scan_code: str | None = Field(default=None, description="扫码原始编码")
    remark: str | None = Field(default=None, description="备注")
    part_code: str | None = Field(default=None, description="配件编码（扩展字段）")
    part_name: str | None = Field(default=None, description="配件名称（扩展字段）")
    spec: str | None = Field(default=None, description="规格型号（扩展字段）")
    unit: str | None = Field(default=None, description="单位（扩展字段）")
    item_code: str | None = Field(default=None, description="库存件编码（扩展字段）")
    location_code: str | None = Field(default=None, description="库位编码（扩展字段）")


class StocktakeOrderDetailVO(StocktakeOrderVO):
    """盘点单详情（含明细）。"""

    items: list[StocktakeOrderItemVO] = Field(
        default_factory=list, description="盘点明细"
    )
