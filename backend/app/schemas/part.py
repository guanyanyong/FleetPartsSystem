"""配件相关 Schema（part_category、part、part_vehicle_model、part_unit_conversion）。"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.schemas.common import AuditVO, JsonDecimal, PageQuery, SchemaBase

__all__ = [
    "PartCategoryCreate",
    "PartCategoryQuery",
    "PartCategoryTreeVO",
    "PartCategoryUpdate",
    "PartCategoryVO",
    "PartCreate",
    "PartQuery",
    "PartUnitConversionAdd",
    "PartUnitConversionCreate",
    "PartUnitConversionQuery",
    "PartUnitConversionUpdate",
    "PartUnitConversionVO",
    "PartUpdate",
    "PartVO",
    "PartVehicleModelAdd",
    "PartVehicleModelCreate",
    "PartVehicleModelDetailVO",
    "PartVehicleModelQuery",
    "PartVehicleModelUpdate",
    "PartVehicleModelVO",
]


# ---------------------------------------------------------------- 配件分类
class PartCategoryCreate(SchemaBase):
    """新增配件分类。"""

    name: str = Field(min_length=1, max_length=50, description="分类名")
    parent_id: int | None = Field(default=None, description="父分类ID")
    sort: int | None = Field(default=0, ge=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class PartCategoryUpdate(SchemaBase):
    """编辑配件分类。"""

    name: str | None = Field(
        default=None, min_length=1, max_length=50, description="分类名"
    )
    parent_id: int | None = Field(default=None, description="父分类ID")
    sort: int | None = Field(default=None, ge=0, description="排序")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class PartCategoryQuery(PageQuery):
    """配件分类分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="分类名模糊搜索"
    )
    parent_id: int | None = Field(default=None, description="父分类ID")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class PartCategoryVO(AuditVO):
    """配件分类详情。"""

    id: int = Field(description="主键")
    name: str = Field(description="分类名")
    parent_id: int | None = Field(default=None, description="父分类ID")
    sort: int | None = Field(default=None, description="排序")
    status: int = Field(description="1启用 0停用")


class PartCategoryTreeVO(PartCategoryVO):
    """分类树节点（GET /part-categories/tree）。"""

    children: list[PartCategoryTreeVO] = Field(
        default_factory=list, description="子分类"
    )


# ---------------------------------------------------------------- 配件
class PartCreate(SchemaBase):
    """新增配件。"""

    part_code: str = Field(
        min_length=1, max_length=50, description="配件业务编码，唯一"
    )
    part_name: str = Field(min_length=1, max_length=100, description="配件名称")
    category_id: int | None = Field(default=None, description="分类ID")
    spec: str | None = Field(default=None, max_length=100, description="规格型号")
    brand: str | None = Field(default=None, max_length=50, description="品牌")
    unit: str = Field(default="个", min_length=1, max_length=20, description="基本单位")
    is_general: int = Field(default=0, ge=0, le=1, description="是否通用件 1是 0否")
    safety_stock: Decimal | None = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="安全库存",
    )
    max_stock: Decimal | None = Field(
        default=Decimal(0),
        ge=0,
        max_digits=12,
        decimal_places=2,
        description="最高库存",
    )
    shelf_life_days: int | None = Field(
        default=0, ge=0, description="保质期天数，0为无"
    )
    track_by_item: int = Field(
        default=0, ge=0, le=1, description="是否按件追踪，1是则入库逐件生成二维码"
    )
    scan_enabled: int = Field(default=1, ge=0, le=1, description="是否允许扫码出库")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class PartUpdate(SchemaBase):
    """编辑配件。"""

    part_code: str | None = Field(
        default=None, min_length=1, max_length=50, description="配件业务编码，唯一"
    )
    part_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="配件名称"
    )
    category_id: int | None = Field(default=None, description="分类ID")
    spec: str | None = Field(default=None, max_length=100, description="规格型号")
    brand: str | None = Field(default=None, max_length=50, description="品牌")
    unit: str | None = Field(
        default=None, min_length=1, max_length=20, description="基本单位"
    )
    is_general: int | None = Field(
        default=None, ge=0, le=1, description="是否通用件 1是 0否"
    )
    safety_stock: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, description="安全库存"
    )
    max_stock: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, description="最高库存"
    )
    shelf_life_days: int | None = Field(
        default=None, ge=0, description="保质期天数，0为无"
    )
    track_by_item: int | None = Field(
        default=None, ge=0, le=1, description="是否按件追踪"
    )
    scan_enabled: int | None = Field(
        default=None, ge=0, le=1, description="是否允许扫码出库"
    )
    remark: str | None = Field(default=None, max_length=255, description="备注")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class PartQuery(PageQuery):
    """配件分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="配件编码/名称/规格模糊搜索"
    )
    part_code: str | None = Field(default=None, max_length=50, description="配件编码")
    category_id: int | None = Field(default=None, description="分类ID")
    brand: str | None = Field(default=None, max_length=50, description="品牌")
    is_general: int | None = Field(default=None, ge=0, le=1, description="是否通用件")
    track_by_item: int | None = Field(
        default=None, ge=0, le=1, description="是否按件追踪"
    )
    scan_enabled: int | None = Field(
        default=None, ge=0, le=1, description="是否允许扫码出库"
    )
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class PartVO(AuditVO):
    """配件详情。"""

    id: int = Field(description="主键")
    part_code: str = Field(description="配件业务编码")
    part_name: str = Field(description="配件名称")
    category_id: int | None = Field(default=None, description="分类ID")
    spec: str | None = Field(default=None, description="规格型号")
    brand: str | None = Field(default=None, description="品牌")
    unit: str = Field(description="基本单位")
    is_general: int = Field(description="是否通用件 1是 0否")
    safety_stock: JsonDecimal | None = Field(default=None, description="安全库存")
    max_stock: JsonDecimal | None = Field(default=None, description="最高库存")
    shelf_life_days: int | None = Field(default=None, description="保质期天数，0为无")
    track_by_item: int = Field(description="是否按件追踪")
    scan_enabled: int = Field(description="是否允许扫码出库")
    remark: str | None = Field(default=None, description="备注")
    status: int = Field(description="1启用 0停用")
    category_name: str | None = Field(default=None, description="分类名称（扩展字段）")
    stock_quantity: JsonDecimal = Field(
        default=Decimal(0), description="当前库存合计，跨仓库（扩展字段）"
    )


# ---------------------------------------------------------------- 配件车型适配
class PartVehicleModelCreate(SchemaBase):
    """添加适配车型（POST /parts/{id}/models）。"""

    part_id: int = Field(description="配件ID")
    model_id: int = Field(description="车型ID")
    remark: str | None = Field(default=None, max_length=100, description="备注")


class PartVehicleModelUpdate(SchemaBase):
    """编辑适配关系。"""

    model_id: int | None = Field(default=None, description="车型ID")
    remark: str | None = Field(default=None, max_length=100, description="备注")


class PartVehicleModelQuery(PageQuery):
    """适配车型分页查询条件。"""

    part_id: int | None = Field(default=None, description="配件ID")
    model_id: int | None = Field(default=None, description="车型ID")


class PartVehicleModelVO(AuditVO):
    """适配车型详情。"""

    id: int = Field(description="主键")
    part_id: int = Field(description="配件ID")
    model_id: int = Field(description="车型ID")
    remark: str | None = Field(default=None, description="备注")


class PartVehicleModelAdd(SchemaBase):
    """添加适配车型（POST /parts/{id}/models），part_id 取自路径。"""

    model_id: int = Field(description="车型ID")
    remark: str | None = Field(default=None, max_length=100, description="备注")


class PartVehicleModelDetailVO(PartVehicleModelVO):
    """适配车型（含车型基础信息，GET /parts/{id}/models）。"""

    brand: str | None = Field(default=None, description="品牌")
    model_name: str | None = Field(default=None, description="型号")
    tonnage: str | None = Field(default=None, description="吨位/座位")
    model_status: int | None = Field(default=None, description="车型状态 1启用 0停用")


# ---------------------------------------------------------------- 配件单位换算
class PartUnitConversionCreate(SchemaBase):
    """新增单位换算。"""

    part_id: int = Field(description="配件ID")
    from_unit: str = Field(min_length=1, max_length=20, description="源单位")
    to_unit: str = Field(min_length=1, max_length=20, description="目标单位")
    rate: Decimal = Field(gt=0, max_digits=12, decimal_places=4, description="换算率")


class PartUnitConversionUpdate(SchemaBase):
    """编辑单位换算。"""

    from_unit: str | None = Field(
        default=None, min_length=1, max_length=20, description="源单位"
    )
    to_unit: str | None = Field(
        default=None, min_length=1, max_length=20, description="目标单位"
    )
    rate: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=4, description="换算率"
    )


class PartUnitConversionQuery(PageQuery):
    """单位换算分页查询条件。"""

    part_id: int | None = Field(default=None, description="配件ID")
    from_unit: str | None = Field(default=None, max_length=20, description="源单位")
    to_unit: str | None = Field(default=None, max_length=20, description="目标单位")


class PartUnitConversionVO(AuditVO):
    """单位换算详情。"""

    id: int = Field(description="主键")
    part_id: int = Field(description="配件ID")
    from_unit: str = Field(description="源单位")
    to_unit: str = Field(description="目标单位")
    rate: JsonDecimal = Field(description="换算率")


class PartUnitConversionAdd(SchemaBase):
    """新增单位换算（POST /parts/{id}/units），part_id 取自路径。"""

    from_unit: str = Field(min_length=1, max_length=20, description="源单位")
    to_unit: str = Field(min_length=1, max_length=20, description="目标单位")
    rate: Decimal = Field(gt=0, max_digits=12, decimal_places=4, description="换算率")
