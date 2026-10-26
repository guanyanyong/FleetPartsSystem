"""认证业务逻辑：登录校验与 token 签发。"""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.security import create_access_token, verify_password
from app.models import SysUser
from app.models.enums import UserStatus
from app.schemas.auth import AuthUserVO, LoginRequest, LoginVO

__all__ = ["authenticate", "build_user_info", "login", "logout"]


async def authenticate(db: AsyncSession, username: str, password: str) -> SysUser:
    """校验账号密码，返回启用的用户。

    用户不存在与密码错误返回同一提示，避免暴露登录名是否已注册。
    """
    stmt = select(SysUser).where(
        SysUser.username == username,
        SysUser.is_deleted == 0,
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise BizException(code=401, message="用户名或密码错误")
    if user.status != UserStatus.ENABLED:
        raise BizException(code=403, message="该账号已停用，请联系管理员")
    return user


def build_user_info(user: SysUser) -> AuthUserVO:
    """把 ORM 用户转换为登录 / 当前用户响应里的 `userInfo`。"""
    return AuthUserVO.model_validate(user)


async def login(db: AsyncSession, payload: LoginRequest) -> LoginVO:
    """账号密码登录，成功返回 token 与用户信息。"""
    user = await authenticate(db, payload.username, payload.password)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    logger.info(
        "用户登录成功 | id={} | username={} | role={}",
        user.id,
        user.username,
        user.role,
    )
    return LoginVO(
        token=token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_info=build_user_info(user),
    )


async def logout(user: SysUser) -> None:
    """登出：JWT 无状态，服务端只记录日志，token 由前端丢弃。"""
    logger.info("用户退出登录 | id={} | username={}", user.id, user.username)
