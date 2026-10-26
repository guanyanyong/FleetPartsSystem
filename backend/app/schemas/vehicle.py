"""车型与车辆 Schema（vehicle_model、vehicle）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, SchemaBase

__all__ = [
    "VehicleCreate",
    "VehicleModelCreate",
    "VehicleModelQuery",
    "VehicleModelUpdate",
    "VehicleModelVO",
    "VehicleQuery",
    "VehicleUpdate",
    "VehicleVO",
]


# ---------------------------------------------------------------- 车型
class VehicleModelCreate(SchemaBase):
    """新增车型。"""

    brand: str = Field(min_length=1, max_length=50, description="品牌")
    model_name: str = Field(min_length=1, max_length=100, description="型号")
    tonnage: str | None = Field(default=None, max_length=20, description="吨位/座位")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class VehicleModelUpdate(SchemaBase):
    """编辑车型。"""

    brand: str | None = Field(
        default=None, min_length=1, max_length=50, description="品牌"
    )
    model_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="型号"
    )
    tonnage: str | None = Field(default=None, max_length=20, description="吨位/座位")
    remark: str | None = Field(default=None, max_length=255, description="备注")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class VehicleModelQuery(PageQuery):
    """车型分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="品牌/型号模糊搜索"
    )
    brand: str | None = Field(default=None, max_length=50, description="品牌")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class VehicleModelVO(AuditVO):
    """车型详情。"""

    id: int = Field(description="主键")
    brand: str = Field(description="品牌")
    model_name: str = Field(description="型号")
    tonnage: str | None = Field(default=None, description="吨位/座位")
    remark: str | None = Field(default=None, description="备注")
    status: int = Field(description="1启用 0停用")


# ---------------------------------------------------------------- 车辆
class VehicleCreate(SchemaBase):
    """新增车辆。"""

    plate_no: str = Field(min_length=1, max_length=20, description="车牌号，唯一")
    model_id: int | None = Field(default=None, description="车型ID")
    vin: str | None = Field(default=None, max_length=50, description="车架号")
    engine_no: str | None = Field(default=None, max_length=50, description="发动机号")
    purchase_date: date | None = Field(default=None, description="购置日期")
    department: str | None = Field(
        default=None, max_length=50, description="所属车队/部门"
    )
    status: int = Field(default=1, ge=1, le=4, description="1在用 2维修 3停用 4报废")
    mileage: int | None = Field(default=0, ge=0, description="当前里程")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class VehicleUpdate(SchemaBase):
    """编辑车辆。"""

    plate_no: str | None = Field(
        default=None, min_length=1, max_length=20, description="车牌号，唯一"
    )
    model_id: int | None = Field(default=None, description="车型ID")
    vin: str | None = Field(default=None, max_length=50, description="车架号")
    engine_no: str | None = Field(default=None, max_length=50, description="发动机号")
    purchase_date: date | None = Field(default=None, description="购置日期")
    department: str | None = Field(
        default=None, max_length=50, description="所属车队/部门"
    )
    status: int | None = Field(
        default=None, ge=1, le=4, description="1在用 2维修 3停用 4报废"
    )
    mileage: int | None = Field(default=None, ge=0, description="当前里程")
    remark: str | None = Field(default=None, max_length=255, description="备注")


class VehicleQuery(PageQuery):
    """车辆分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="车牌号/车架号/发动机号模糊搜索"
    )
    model_id: int | None = Field(default=None, description="车型ID")
    department: str | None = Field(
        default=None, max_length=50, description="所属车队/部门"
    )
    status: int | None = Field(
        default=None, ge=1, le=4, description="1在用 2维修 3停用 4报废"
    )


class VehicleVO(AuditVO):
    """车辆详情。"""

    id: int = Field(description="主键")
    plate_no: str = Field(description="车牌号")
    model_id: int | None = Field(default=None, description="车型ID")
    brand: str | None = Field(default=None, description="品牌（车型扩展字段）")
    model_name: str | None = Field(default=None, description="型号（车型扩展字段）")
    vin: str | None = Field(default=None, description="车架号")
    engine_no: str | None = Field(default=None, description="发动机号")
    purchase_date: date | None = Field(default=None, description="购置日期")
    department: str | None = Field(default=None, description="所属车队/部门")
    status: int = Field(description="1在用 2维修 3停用 4报废")
    mileage: int | None = Field(default=None, description="当前里程")
    remark: str | None = Field(default=None, description="备注")
