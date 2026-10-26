"""FastAPI 依赖注入：数据库会话、当前登录用户、角色校验。

统一在这里导出 `DbSession` / `CurrentUser` / `CurrentUserId` 等 Annotated 别名，
路由层直接使用，避免每个模块重复写 Depends(...)。
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models import SysUser
from app.models.enums import Role, UserStatus

__all__ = [
    "CurrentUser",
    "CurrentUserId",
    "DbSession",
    "bearer_scheme",
    "get_current_user",
    "get_current_user_id",
    "get_db",
    "require_role",
]

# auto_error=False：缺少 token 时由本模块统一返回 401（而不是 Starlette 默认的 403）
bearer_scheme: HTTPBearer = HTTPBearer(
    auto_error=False,
    description="Authorization: Bearer <access token>",
)

_UNAUTHORIZED_HEADERS: dict[str, str] = {"WWW-Authenticate": "Bearer"}


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers=_UNAUTHORIZED_HEADERS,
    )


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> SysUser:
    """解析 Bearer token 并返回当前登录用户。"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("未登录或登录已过期")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise _unauthorized("登录凭证无效或已过期")

    raw_user_id = payload.get("uid", payload.get("sub"))
    try:
        user_id = int(raw_user_id)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _unauthorized("登录凭证无效或已过期") from None

    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise _unauthorized("用户不存在或已删除")
    if user.status != UserStatus.ENABLED:
        raise _unauthorized("用户已停用")
    return user


async def get_current_user_id(
    user: Annotated[SysUser, Depends(get_current_user)],
) -> int:
    """当前用户 ID，供 Service 层填充 created_by / updated_by。"""
    return user.id


def require_role(roles: list[str]) -> Callable[..., Awaitable[SysUser]]:
    """生成角色校验依赖：`admin` 拥有全部权限。

    用法：`Depends(require_role([Role.ADMIN, Role.KEEPER]))`
    """
    allowed: set[str] = set(roles) | {Role.ADMIN}

    async def checker(
        user: Annotated[SysUser, Depends(get_current_user)],
    ) -> SysUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限执行该操作",
            )
        return user

    return checker


# 常用依赖别名
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[SysUser, Depends(get_current_user)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
