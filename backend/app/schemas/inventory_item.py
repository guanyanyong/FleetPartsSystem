"""库存件实例 Schema（inventory_item）与扫码结果 VO。

`item_code` / `qrcode` 由入库审核时通过编码生成器统一生成，
因此 `InventoryItemCreate` 不接收这两个字段；如需手动建档请在服务层生成。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "InventoryItemCreate",
    "InventoryItemDetailVO",
    "InventoryItemQuery",
    "InventoryItemUpdate",
    "InventoryItemVO",
    "ScanQuery",
    "ScanResultVO",
]


class InventoryItemCreate(SchemaBase):
    """新增库存件实例（item_code、qrcode 由服务层生成）。"""

    part_id: int = Field(description="所属配件ID")
    warehouse_id: int = Field(description="当前仓库ID")
    location_id: int | None = Field(default=None, description="当前库位ID")
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    serial_no: str | None = Field(
        default=None, max_length=100, description="序列号/出厂编号"
    )
    production_date: date | None = Field(default=None, description="生产日期")
    expire_date: date | None = Field(default=None, description="到期日期")
    unit_cost: Decimal = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=4,
        description="该件入库成本",
    )
    status: int = Field(
        default=1, ge=1, le=5, description="1在库 2锁定 3已出库 4已报废 5已盘亏"
    )
    inbound_item_id: int | None = Field(default=None, description="来源入库明细ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class InventoryItemUpdate(SchemaBase):
    """编辑库存件资料（`PUT /inventory-items/{id}`）。

    只接收资料类字段，仅更新请求中出现的字段：
    - 不可编辑：`item_code` / `qrcode`（系统生成）、`part_id`（换件需重新入库）、
      `status` / `vehicle_id` / `work_order_id` / `in_at` / `out_at`
      （由入库、出库、调拨、盘点状态机维护）；
    - `quantity` 不在此表：库存件按件追踪，每件数量恒为 1，数量只能通过
      入库 / 出库 / 盘点单据调整；
    - `location_id` 显式传 null 表示改为仓库级存放（不指定库位）。
    """

    warehouse_id: int | None = Field(default=None, ge=1, description="当前仓库ID")
    location_id: int | None = Field(
        default=None, ge=1, description="当前库位ID，null 表示仓库级存放"
    )
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    serial_no: str | None = Field(
        default=None, max_length=100, description="序列号/出厂编号"
    )
    production_date: date | None = Field(default=None, description="生产日期")
    expire_date: date | None = Field(default=None, description="到期日期")
    unit_cost: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4, description="该件入库成本"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")


class InventoryItemQuery(PageQuery):
    """库存件分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="库存件编码/序列号/批次号模糊搜索"
    )
    part_id: int | None = Field(default=None, description="所属配件ID")
    warehouse_id: int | None = Field(default=None, description="当前仓库ID")
    location_id: int | None = Field(default=None, description="当前库位ID")
    status: int | None = Field(
        default=None, ge=1, le=5, description="1在库 2锁定 3已出库 4已报废 5已盘亏"
    )
    vehicle_id: int | None = Field(default=None, description="装到哪台车")
    work_order_id: int | None = Field(default=None, description="关联维修工单")
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    expire_before: date | None = Field(
        default=None, description="到期日期早于等于该日期（临期查询）"
    )


class InventoryItemVO(AuditVO):
    """库存件详情。"""

    id: int = Field(description="主键")
    item_code: str = Field(description="库存件唯一编码")
    qrcode: str = Field(description="二维码内容")
    qrcode_image: str | None = Field(default=None, description="二维码图片路径")
    part_id: int = Field(description="所属配件ID")
    warehouse_id: int = Field(description="当前仓库ID")
    location_id: int | None = Field(default=None, description="当前库位ID")
    batch_no: str | None = Field(default=None, description="批次号")
    serial_no: str | None = Field(default=None, description="序列号/出厂编号")
    production_date: date | None = Field(default=None, description="生产日期")
    expire_date: date | None = Field(default=None, description="到期日期")
    unit_cost: Decimal = Field(description="该件入库成本")
    status: int = Field(description="1在库 2锁定 3已出库 4已报废 5已盘亏")
    inbound_item_id: int | None = Field(default=None, description="来源入库明细ID")
    outbound_item_id: int | None = Field(default=None, description="出库明细ID")
    vehicle_id: int | None = Field(default=None, description="装到哪台车")
    work_order_id: int | None = Field(default=None, description="关联维修工单")
    in_at: datetime | None = Field(default=None, description="入库时间")
    out_at: datetime | None = Field(default=None, description="出库时间")
    remark: str | None = Field(default=None, description="备注")


class InventoryItemDetailVO(InventoryItemVO):
    """库存件详情（带配件/仓库/库位名称，由服务层 join 填充）。"""

    part_code: str | None = Field(default=None, description="配件编码")
    part_name: str | None = Field(default=None, description="配件名称")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str | None = Field(default=None, description="基本单位")
    status_text: str | None = Field(default=None, description="状态文案，如「在库」")
    warehouse_name: str | None = Field(default=None, description="仓库名")
    location_code: str | None = Field(default=None, description="库位编码")


class ScanQuery(SchemaBase):
    """扫码查询参数：`GET /scan/inventory-item?code=xxx`。"""

    code: str = Field(
        min_length=1, max_length=255, description="扫码内容（支持 QR: 前缀）"
    )


class ScanResultVO(SchemaBase):
    """扫码成功返回的库存件聚合信息（对应文档 data 结构）。"""

    item_id: int = Field(description="库存件ID")
    item_code: str = Field(description="库存件编码")
    qrcode: str = Field(description="二维码内容")
    part_id: int = Field(description="所属配件ID")
    part_code: str | None = Field(default=None, description="配件编码")
    part_name: str | None = Field(default=None, description="配件名称")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str | None = Field(default=None, description="基本单位")
    batch_no: str | None = Field(default=None, description="批次号")
    status: int = Field(description="1在库 2锁定 3已出库 4已报废 5已盘亏")
    status_text: str = Field(description="状态文案，如「在库」")
    warehouse_id: int = Field(description="当前仓库ID")
    warehouse_name: str | None = Field(default=None, description="仓库名")
    location_id: int | None = Field(default=None, description="当前库位ID")
    location_code: str | None = Field(default=None, description="库位编码")
    unit_cost: JsonDecimal = Field(description="该件入库成本")
    in_at: datetime | None = Field(default=None, description="入库时间")
