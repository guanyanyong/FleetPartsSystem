"""车型与车辆接口：车型增删改查分页 + 车辆增删改查分页。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户（入库/出库/工单/报表都需要选车型、车辆）
- 写操作：admin / keeper
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleModelCreate,
    VehicleModelQuery,
    VehicleModelUpdate,
    VehicleModelVO,
    VehicleQuery,
    VehicleUpdate,
    VehicleVO,
)
from app.services import vehicle_service

__all__ = ["model_router", "router"]

# /api/v1/vehicle-models：车型
model_router = APIRouter()
# /api/v1/vehicles：车辆
router = APIRouter()

# 主数据写操作：管理员 / 库管
VehicleWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


# ---------------------------------------------------------------- 车型
@model_router.get(
    "",
    response_model=ApiResponse[PageResult[VehicleModelVO]],
    summary="车型分页列表",
)
async def list_vehicle_models(
    db: DbSession,
    query: Annotated[VehicleModelQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持品牌/型号关键字、品牌、状态筛选。"""
    return success(data=await vehicle_service.list_vehicle_models(db, query))


@model_router.post("", response_model=ApiResponse[VehicleModelVO], summary="新增车型")
async def create_vehicle_model(
    payload: VehicleModelCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    """同一品牌下车型名称不允许重复（409）。"""
    return success(
        data=await vehicle_service.create_vehicle_model(db, payload, current_user_id),
        message="新增成功",
    )


@model_router.put(
    "/{model_id}",
    response_model=ApiResponse[VehicleModelVO],
    summary="编辑车型",
)
async def update_vehicle_model(
    model_id: int,
    payload: VehicleModelUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    return success(
        data=await vehicle_service.update_vehicle_model(
            db, model_id, payload, current_user_id
        ),
        message="更新成功",
    )


@model_router.delete(
    "/{model_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除车型",
)
async def delete_vehicle_model(
    model_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    """该车型下仍有车辆时返回 409。"""
    await vehicle_service.delete_vehicle_model(db, model_id, current_user_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 车辆
@router.get(
    "", response_model=ApiResponse[PageResult[VehicleVO]], summary="车辆分页列表"
)
async def list_vehicles(
    db: DbSession,
    query: Annotated[VehicleQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持车牌号/车架号/发动机号关键字、车型、部门、状态筛选。"""
    return success(data=await vehicle_service.list_vehicles(db, query))


@router.post("", response_model=ApiResponse[VehicleVO], summary="新增车辆")
async def create_vehicle(
    payload: VehicleCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    """车牌号唯一，重复返回 409。"""
    return success(
        data=await vehicle_service.create_vehicle(db, payload, current_user_id),
        message="新增成功",
    )


@router.get("/{vehicle_id}", response_model=ApiResponse[VehicleVO], summary="车辆详情")
async def get_vehicle(vehicle_id: int, db: DbSession, _: CurrentUser) -> dict:
    """详情包含车型品牌 / 型号。"""
    return success(data=await vehicle_service.get_vehicle(db, vehicle_id))


@router.put("/{vehicle_id}", response_model=ApiResponse[VehicleVO], summary="编辑车辆")
async def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    return success(
        data=await vehicle_service.update_vehicle(
            db, vehicle_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.delete(
    "/{vehicle_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除车辆",
)
async def delete_vehicle(
    vehicle_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: VehicleWriteUser,
) -> dict:
    """已存在维修工单 / 出库单 / 装用配件时返回 409。"""
    await vehicle_service.delete_vehicle(db, vehicle_id, current_user_id)
    return success(message="删除成功")
