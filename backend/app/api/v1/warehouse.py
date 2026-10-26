"""仓库与库位接口：仓库增删改查分页 + 库位增删改查分页。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户（入库/出库/调拨/盘点都需要选仓库、库位）
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
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseLocationCreate,
    WarehouseLocationQuery,
    WarehouseLocationUpdate,
    WarehouseLocationVO,
    WarehouseQuery,
    WarehouseUpdate,
    WarehouseVO,
)
from app.services import warehouse_service

__all__ = ["location_router", "router"]

# /api/v1/warehouses：仓库
router = APIRouter()
# /api/v1/warehouse-locations：库位
location_router = APIRouter()

# 主数据写操作：管理员 / 库管
WarehouseWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


# ---------------------------------------------------------------- 仓库
@router.get(
    "", response_model=ApiResponse[PageResult[WarehouseVO]], summary="仓库分页列表"
)
async def list_warehouses(
    db: DbSession,
    query: Annotated[WarehouseQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持仓库名关键字、负责人、状态筛选。"""
    return success(data=await warehouse_service.list_warehouses(db, query))


@router.post("", response_model=ApiResponse[WarehouseVO], summary="新增仓库")
async def create_warehouse(
    payload: WarehouseCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    """仓库名不允许重复（409），负责人必须是已存在的用户。"""
    return success(
        data=await warehouse_service.create_warehouse(db, payload, current_user_id),
        message="新增成功",
    )


@router.get(
    "/{warehouse_id}",
    response_model=ApiResponse[WarehouseVO],
    summary="仓库详情",
)
async def get_warehouse(warehouse_id: int, db: DbSession, _: CurrentUser) -> dict:
    return success(data=await warehouse_service.get_warehouse(db, warehouse_id))


@router.put(
    "/{warehouse_id}",
    response_model=ApiResponse[WarehouseVO],
    summary="编辑仓库",
)
async def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    return success(
        data=await warehouse_service.update_warehouse(
            db, warehouse_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.delete(
    "/{warehouse_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除仓库",
)
async def delete_warehouse(
    warehouse_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    """仓库下仍有库位 / 库存 / 库存件时返回 409。"""
    await warehouse_service.delete_warehouse(db, warehouse_id, current_user_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 库位
@location_router.get(
    "",
    response_model=ApiResponse[PageResult[WarehouseLocationVO]],
    summary="库位分页列表",
)
async def list_warehouse_locations(
    db: DbSession,
    query: Annotated[WarehouseLocationQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持按仓库筛选（warehouseId），以及库位编码关键字、状态筛选。"""
    return success(data=await warehouse_service.list_warehouse_locations(db, query))


@location_router.post(
    "",
    response_model=ApiResponse[WarehouseLocationVO],
    summary="新增库位",
)
async def create_warehouse_location(
    payload: WarehouseLocationCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    """仓库内库位编码唯一，重复返回 409。"""
    return success(
        data=await warehouse_service.create_warehouse_location(
            db, payload, current_user_id
        ),
        message="新增成功",
    )


@location_router.put(
    "/{location_id}",
    response_model=ApiResponse[WarehouseLocationVO],
    summary="编辑库位",
)
async def update_warehouse_location(
    location_id: int,
    payload: WarehouseLocationUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    return success(
        data=await warehouse_service.update_warehouse_location(
            db, location_id, payload, current_user_id
        ),
        message="更新成功",
    )


@location_router.delete(
    "/{location_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除库位",
)
async def delete_warehouse_location(
    location_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WarehouseWriteUser,
) -> dict:
    """该库位仍有库存或库存件时返回 409。"""
    await warehouse_service.delete_warehouse_location(db, location_id, current_user_id)
    return success(message="删除成功")
