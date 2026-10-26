"""仓库与库位 Schema（warehouse、warehouse_location）。"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, SchemaBase

__all__ = [
    "WarehouseCreate",
    "WarehouseLocationCreate",
    "WarehouseLocationQuery",
    "WarehouseLocationUpdate",
    "WarehouseLocationVO",
    "WarehouseQuery",
    "WarehouseUpdate",
    "WarehouseVO",
]


# ---------------------------------------------------------------- 仓库
class WarehouseCreate(SchemaBase):
    """新增仓库。"""

    name: str = Field(min_length=1, max_length=50, description="仓库名")
    address: str | None = Field(default=None, max_length=255, description="地址")
    keeper_id: int | None = Field(default=None, description="负责人ID")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class WarehouseUpdate(SchemaBase):
    """编辑仓库。"""

    name: str | None = Field(
        default=None, min_length=1, max_length=50, description="仓库名"
    )
    address: str | None = Field(default=None, max_length=255, description="地址")
    keeper_id: int | None = Field(default=None, description="负责人ID")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class WarehouseQuery(PageQuery):
    """仓库分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="仓库名模糊搜索"
    )
    keeper_id: int | None = Field(default=None, description="负责人ID")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class WarehouseVO(AuditVO):
    """仓库详情。"""

    id: int = Field(description="主键")
    name: str = Field(description="仓库名")
    address: str | None = Field(default=None, description="地址")
    keeper_id: int | None = Field(default=None, description="负责人ID")
    status: int = Field(description="1启用 0停用")


# ---------------------------------------------------------------- 库位
class WarehouseLocationCreate(SchemaBase):
    """新增库位。"""

    warehouse_id: int = Field(description="仓库ID")
    location_code: str = Field(min_length=1, max_length=50, description="库位编码")
    location_qrcode: str | None = Field(
        default=None, max_length=255, description="库位二维码内容"
    )
    remark: str | None = Field(default=None, max_length=100, description="备注")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class WarehouseLocationUpdate(SchemaBase):
    """编辑库位。"""

    warehouse_id: int | None = Field(default=None, description="仓库ID")
    location_code: str | None = Field(
        default=None, min_length=1, max_length=50, description="库位编码"
    )
    location_qrcode: str | None = Field(
        default=None, max_length=255, description="库位二维码内容"
    )
    remark: str | None = Field(default=None, max_length=100, description="备注")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class WarehouseLocationQuery(PageQuery):
    """库位分页查询条件。"""

    warehouse_id: int | None = Field(default=None, description="仓库ID")
    keyword: str | None = Field(
        default=None, max_length=50, description="库位编码模糊搜索"
    )
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class WarehouseLocationVO(AuditVO):
    """库位详情。"""

    id: int = Field(description="主键")
    warehouse_id: int = Field(description="仓库ID")
    location_code: str = Field(description="库位编码")
    location_qrcode: str | None = Field(default=None, description="库位二维码内容")
    remark: str | None = Field(default=None, description="备注")
    status: int = Field(description="1启用 0停用")
