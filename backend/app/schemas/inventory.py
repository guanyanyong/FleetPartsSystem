"""库存 Schema（inventory、inventory_transaction）。

`inventory_transaction` 是只读流水表，只提供 Create/Query/VO，不提供 Update。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, ReadOnlyAuditVO, SchemaBase

__all__ = [
    "InventoryCreate",
    "InventoryDetailVO",
    "InventoryQuery",
    "InventoryTransactionCreate",
    "InventoryTransactionQuery",
    "InventoryTransactionVO",
    "InventoryUpdate",
    "InventoryVO",
]


# ---------------------------------------------------------------- 库存汇总
class InventoryCreate(SchemaBase):
    """新增库存记录（正常由入库审核自动生成）。"""

    part_id: int = Field(description="配件ID")
    warehouse_id: int = Field(description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    quantity: Decimal = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="当前数量",
    )
    item_count: int = Field(default=0, ge=0, description="在库实例数")
    locked_qty: Decimal = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="锁定数量",
    )
    avg_cost: Decimal = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=4,
        description="移动加权平均成本",
    )


class InventoryUpdate(SchemaBase):
    """调整库存（仅供盘点/调拨等内部服务使用）。"""

    location_id: int | None = Field(default=None, description="库位ID")
    quantity: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, description="当前数量"
    )
    item_count: int | None = Field(default=None, ge=0, description="在库实例数")
    locked_qty: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, description="锁定数量"
    )
    avg_cost: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=4,
        description="移动加权平均成本",
    )


class InventoryQuery(PageQuery):
    """库存分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="配件编码/名称模糊搜索"
    )
    part_id: int | None = Field(default=None, description="配件ID")
    warehouse_id: int | None = Field(default=None, description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    low_stock: bool | None = Field(
        default=None, description="true 只看低于安全库存的记录（库存预警）"
    )


class InventoryVO(AuditVO):
    """库存详情。"""

    id: int = Field(description="主键")
    part_id: int = Field(description="配件ID")
    warehouse_id: int = Field(description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    quantity: Decimal = Field(description="当前数量")
    item_count: int = Field(description="在库实例数")
    locked_qty: Decimal = Field(description="锁定数量")
    avg_cost: Decimal = Field(description="移动加权平均成本")
    last_in_at: datetime | None = Field(default=None, description="最后入库时间")
    last_out_at: datetime | None = Field(default=None, description="最后出库时间")


class InventoryDetailVO(InventoryVO):
    """库存详情（带配件/仓库/库位名称，供列表展示，由服务层 join 填充）。"""

    part_code: str | None = Field(default=None, description="配件编码")
    part_name: str | None = Field(default=None, description="配件名称")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str | None = Field(default=None, description="基本单位")
    safety_stock: Decimal | None = Field(default=None, description="安全库存")
    max_stock: Decimal | None = Field(default=None, description="最高库存")
    warehouse_name: str | None = Field(default=None, description="仓库名")
    location_code: str | None = Field(default=None, description="库位编码")


# ---------------------------------------------------------------- 库存流水（只读）
class InventoryTransactionCreate(SchemaBase):
    """追加一条库存流水。"""

    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    warehouse_id: int = Field(description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    biz_type: str = Field(
        max_length=20,
        description="业务类型：IN/OUT/TRANSFER_IN/TRANSFER_OUT/ADJUST_IN/ADJUST_OUT",
    )
    change_qty: Decimal = Field(max_digits=12, decimal_places=2, description="变动数量")
    before_qty: Decimal = Field(
        max_digits=12, decimal_places=2, description="变动前数量"
    )
    after_qty: Decimal = Field(
        max_digits=12, decimal_places=2, description="变动后数量"
    )
    unit_cost: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4, description="单位成本"
    )
    ref_type: str = Field(
        max_length=20, description="单据类型：INBOUND/OUTBOUND/TRANSFER/STOCKTAKE"
    )
    ref_id: int | None = Field(default=None, description="关联单据ID")
    ref_no: str | None = Field(default=None, max_length=50, description="关联单号")
    batch_no: str | None = Field(default=None, max_length=50, description="批次号")
    scan_code: str | None = Field(
        default=None, max_length=100, description="扫码原始编码"
    )
    operator_id: int | None = Field(default=None, description="操作人ID")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class InventoryTransactionQuery(PageQuery):
    """库存流水分页查询条件。"""

    part_id: int | None = Field(default=None, description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    warehouse_id: int | None = Field(default=None, description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
    biz_type: str | None = Field(default=None, max_length=20, description="业务类型")
    ref_type: str | None = Field(default=None, max_length=20, description="单据类型")
    ref_id: int | None = Field(default=None, description="关联单据ID")
    ref_no: str | None = Field(default=None, max_length=50, description="关联单号")
    start_time: datetime | None = Field(default=None, description="创建时间起（含）")
    end_time: datetime | None = Field(default=None, description="创建时间止（含）")


class InventoryTransactionVO(ReadOnlyAuditVO):
    """库存流水详情。"""

    id: int = Field(description="主键")
    part_id: int = Field(description="配件ID")
    inventory_item_id: int | None = Field(default=None, description="库存件实例ID")
    warehouse_id: int = Field(description="仓库ID")
    location_id: int | None = Field(default=None, description="库位ID")
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
    remark: str | None = Field(default=None, description="备注")
