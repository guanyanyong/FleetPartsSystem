"""认证 Schema：登录请求与登录响应。

认证模块没有增删改查，因此不提供 Create/Update/Query/VO 四类，
只保留登录请求、登录响应以及 `GET /auth/me` 复用的用户信息 VO。
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import SchemaBase

__all__ = ["AuthUserVO", "LoginRequest", "LoginVO"]


class LoginRequest(SchemaBase):
    """登录请求体。"""

    username: str = Field(min_length=1, max_length=50, description="登录名")
    password: str = Field(min_length=1, max_length=128, description="密码（明文）")


class AuthUserVO(SchemaBase):
    """登录响应中的用户信息，对应文档中的 userInfo。"""

    id: int = Field(description="用户ID")
    username: str = Field(description="登录名")
    real_name: str | None = Field(default=None, description="姓名")
    role: str = Field(description="角色：admin/keeper/purchaser/leader/readonly")
    default_warehouse_id: int | None = Field(default=None, description="默认仓库ID")


class LoginVO(SchemaBase):
    """登录响应 data。"""

    token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", max_length=20, description="token 类型")
    expires_in: int = Field(default=0, ge=0, description="过期秒数")
    user_info: AuthUserVO = Field(description="当前用户信息")
