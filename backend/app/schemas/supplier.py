"""供应商 Schema（supplier）。"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, SchemaBase

__all__ = ["SupplierCreate", "SupplierQuery", "SupplierUpdate", "SupplierVO"]


class SupplierCreate(SchemaBase):
    """新增供应商。"""

    name: str = Field(min_length=1, max_length=100, description="供应商名称")
    contact: str | None = Field(default=None, max_length=50, description="联系人")
    phone: str | None = Field(default=None, max_length=20, description="电话")
    address: str | None = Field(default=None, max_length=255, description="地址")
    main_category: str | None = Field(
        default=None, max_length=100, description="主营品类"
    )
    payment_term: str | None = Field(default=None, max_length=50, description="账期")
    status: int = Field(default=1, ge=0, le=1, description="1合作 0停用")


class SupplierUpdate(SchemaBase):
    """编辑供应商。"""

    name: str | None = Field(
        default=None, min_length=1, max_length=100, description="供应商名称"
    )
    contact: str | None = Field(default=None, max_length=50, description="联系人")
    phone: str | None = Field(default=None, max_length=20, description="电话")
    address: str | None = Field(default=None, max_length=255, description="地址")
    main_category: str | None = Field(
        default=None, max_length=100, description="主营品类"
    )
    payment_term: str | None = Field(default=None, max_length=50, description="账期")
    status: int | None = Field(default=None, ge=0, le=1, description="1合作 0停用")


class SupplierQuery(PageQuery):
    """供应商分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=100, description="名称/联系人/电话模糊搜索"
    )
    main_category: str | None = Field(
        default=None, max_length=100, description="主营品类"
    )
    status: int | None = Field(default=None, ge=0, le=1, description="1合作 0停用")


class SupplierVO(AuditVO):
    """供应商详情。"""

    id: int = Field(description="主键")
    name: str = Field(description="供应商名称")
    contact: str | None = Field(default=None, description="联系人")
    phone: str | None = Field(default=None, description="电话")
    address: str | None = Field(default=None, description="地址")
    main_category: str | None = Field(default=None, description="主营品类")
    payment_term: str | None = Field(default=None, description="账期")
    status: int = Field(description="1合作 0停用")
