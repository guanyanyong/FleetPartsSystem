"""认证接口：登录、当前用户、登出。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.core.response import ApiResponse, success
from app.schemas.auth import AuthUserVO, LoginRequest, LoginVO
from app.services import auth_service

__all__ = ["router"]

router = APIRouter()


@router.post("/login", response_model=ApiResponse[LoginVO], summary="登录")
async def login(payload: LoginRequest, db: DbSession) -> dict:
    """账号密码登录，成功返回 JWT 与用户信息。"""
    return success(data=await auth_service.login(db, payload))


@router.get("/me", response_model=ApiResponse[AuthUserVO], summary="当前登录用户")
async def current_user_info(user: CurrentUser) -> dict:
    """获取当前 token 对应用户信息。"""
    return success(data=auth_service.build_user_info(user))


@router.post("/logout", response_model=ApiResponse[None], summary="登出")
async def logout(user: CurrentUser) -> dict:
    """登出（JWT 无状态，服务端仅记录日志，token 由前端丢弃）。"""
    await auth_service.logout(user)
    return success(message="退出成功")
