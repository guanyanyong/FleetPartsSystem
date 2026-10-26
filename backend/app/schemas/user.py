"""用户 Schema（sys_user）。

注意：VO 中不包含 `password_hash`，密码只在写入时以明文传入、由服务层哈希。
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import AuditVO, PageQuery, SchemaBase

__all__ = [
    "UserCreate",
    "UserPasswordUpdate",
    "UserQuery",
    "UserStatusUpdate",
    "UserUpdate",
    "UserVO",
]


class UserCreate(SchemaBase):
    """新增用户。"""

    username: str = Field(min_length=1, max_length=50, description="登录名，唯一")
    password: str = Field(min_length=6, max_length=128, description="初始密码（明文）")
    real_name: str | None = Field(default=None, max_length=50, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="电话")
    role: str = Field(
        default="readonly",
        max_length=20,
        description="角色：admin/keeper/purchaser/leader/readonly",
    )
    default_warehouse_id: int | None = Field(default=None, description="默认仓库ID")
    status: int = Field(default=1, ge=0, le=1, description="1启用 0停用")


class UserUpdate(SchemaBase):
    """编辑用户（全部字段可选，仅更新传入字段）。"""

    username: str | None = Field(
        default=None, min_length=1, max_length=50, description="登录名，唯一"
    )
    real_name: str | None = Field(default=None, max_length=50, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="电话")
    role: str | None = Field(
        default=None,
        max_length=20,
        description="角色：admin/keeper/purchaser/leader/readonly",
    )
    default_warehouse_id: int | None = Field(default=None, description="默认仓库ID")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")


class UserPasswordUpdate(SchemaBase):
    """重置密码（PUT /users/{id}/password）。"""

    password: str = Field(min_length=6, max_length=128, description="新密码（明文）")


class UserStatusUpdate(SchemaBase):
    """启用/停用（PUT /users/{id}/status）。"""

    status: int = Field(ge=0, le=1, description="1启用 0停用")


class UserQuery(PageQuery):
    """用户分页查询条件。"""

    keyword: str | None = Field(
        default=None, max_length=50, description="用户名/姓名/电话模糊搜索"
    )
    role: str | None = Field(default=None, max_length=20, description="角色")
    status: int | None = Field(default=None, ge=0, le=1, description="1启用 0停用")
    default_warehouse_id: int | None = Field(default=None, description="默认仓库ID")


class UserVO(AuditVO):
    """用户详情（不含密码哈希）。"""

    id: int = Field(description="主键")
    username: str = Field(description="登录名")
    real_name: str | None = Field(default=None, description="姓名")
    phone: str | None = Field(default=None, description="电话")
    role: str = Field(description="角色：admin/keeper/purchaser/leader/readonly")
    default_warehouse_id: int | None = Field(default=None, description="默认仓库ID")
    status: int = Field(description="1启用 0停用")
