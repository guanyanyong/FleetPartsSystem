"""用户管理接口（增删改查 + 重置密码 + 启用/停用）。

权限：读接口对已登录用户开放（便于各业务下拉框选人），写接口仅 admin。
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.user import (
    UserCreate,
    UserPasswordUpdate,
    UserQuery,
    UserStatusUpdate,
    UserUpdate,
    UserVO,
)
from app.services import user_service

__all__ = ["router"]

router = APIRouter()

# 写操作仅管理员
AdminUser = Annotated[SysUser, Depends(require_role([Role.ADMIN]))]


@router.get("", response_model=ApiResponse[PageResult[UserVO]], summary="用户分页列表")
async def list_users(
    db: DbSession,
    query: Annotated[UserQuery, Depends()],
    _: Annotated[SysUser, Depends(require_role([Role.ADMIN, Role.LEADER]))],
) -> dict:
    """分页查询用户，支持用户名/姓名/电话关键字、角色、状态筛选。"""
    return success(data=await user_service.list_users(db, query))


@router.get("/{user_id}", response_model=ApiResponse[UserVO], summary="用户详情")
async def get_user(user_id: int, db: DbSession, _: AdminUser) -> dict:
    return success(data=await user_service.get_user(db, user_id))


@router.post("", response_model=ApiResponse[UserVO], summary="新增用户")
async def create_user(
    payload: UserCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: AdminUser,
) -> dict:
    return success(data=await user_service.create_user(db, payload, current_user_id))


@router.put("/{user_id}", response_model=ApiResponse[UserVO], summary="编辑用户")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: AdminUser,
) -> dict:
    return success(
        data=await user_service.update_user(db, user_id, payload, current_user_id)
    )


@router.delete("/{user_id}", response_model=ApiResponse[None], summary="逻辑删除用户")
async def delete_user(
    user_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: AdminUser,
) -> dict:
    await user_service.delete_user(db, user_id, current_user_id)
    return success(message="删除成功")


@router.put(
    "/{user_id}/password",
    response_model=ApiResponse[None],
    summary="重置密码",
)
async def reset_password(
    user_id: int,
    payload: UserPasswordUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: AdminUser,
) -> dict:
    await user_service.reset_password(db, user_id, payload.password, current_user_id)
    return success(message="密码重置成功")


@router.put(
    "/{user_id}/status", response_model=ApiResponse[UserVO], summary="启用/停用"
)
async def set_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: AdminUser,
) -> dict:
    return success(
        data=await user_service.set_status(db, user_id, payload.status, current_user_id)
    )
