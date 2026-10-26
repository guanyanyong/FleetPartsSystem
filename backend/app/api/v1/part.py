"""配件与配件分类接口：分类树、配件增删改查、适配车型、单位换算。

权限：
- 读接口对所有已登录用户开放（入库/出库/工单/报表都需要选配件）
- 写接口限 admin / keeper
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.part import (
    PartCategoryCreate,
    PartCategoryTreeVO,
    PartCategoryUpdate,
    PartCategoryVO,
    PartCreate,
    PartQuery,
    PartUnitConversionAdd,
    PartUnitConversionVO,
    PartUpdate,
    PartVehicleModelAdd,
    PartVehicleModelDetailVO,
    PartVO,
)
from app.services import part_service

__all__ = ["category_router", "router"]

# /api/v1/part-categories：配件分类
category_router = APIRouter()
# /api/v1/parts：配件主体
router = APIRouter()

# 主数据写操作：管理员 / 库管
PartWriteUser = Annotated[SysUser, Depends(require_role([Role.ADMIN, Role.KEEPER]))]


# ---------------------------------------------------------------- 配件分类
@category_router.get(
    "/tree",
    response_model=ApiResponse[list[PartCategoryTreeVO]],
    summary="配件分类树",
)
async def list_category_tree(
    db: DbSession,
    _: CurrentUser,
    status: Annotated[
        int | None,
        Query(ge=0, le=1, description="1启用 0停用，不传返回全部"),
    ] = None,
) -> dict:
    """返回根分类列表，children 递归嵌套，按 sort、id 升序。"""
    return success(data=await part_service.list_category_tree(db, status))


@category_router.post(
    "",
    response_model=ApiResponse[PartCategoryVO],
    summary="新增配件分类",
)
async def create_category(
    payload: PartCategoryCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    return success(
        data=await part_service.create_category(db, payload, current_user_id),
        message="新增成功",
    )


@category_router.put(
    "/{category_id}",
    response_model=ApiResponse[PartCategoryVO],
    summary="编辑配件分类",
)
async def update_category(
    category_id: int,
    payload: PartCategoryUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    return success(
        data=await part_service.update_category(
            db, category_id, payload, current_user_id
        ),
        message="更新成功",
    )


@category_router.delete(
    "/{category_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除配件分类",
)
async def delete_category(
    category_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    """存在子分类或已关联配件时返回 409。"""
    await part_service.delete_category(db, category_id, current_user_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 配件
@router.get("", response_model=ApiResponse[PageResult[PartVO]], summary="配件分页列表")
async def list_parts(
    db: DbSession,
    query: Annotated[PartQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持编码/名称/规格关键字、分类、品牌、追踪方式、状态筛选。"""
    return success(data=await part_service.list_parts(db, query))


@router.post("", response_model=ApiResponse[PartVO], summary="新增配件")
async def create_part(
    payload: PartCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    """`partCode` 重复返回业务码 1001。"""
    return success(
        data=await part_service.create_part(db, payload, current_user_id),
        message="新增成功",
    )


@router.get("/{part_id}", response_model=ApiResponse[PartVO], summary="配件详情")
async def get_part(part_id: int, db: DbSession, _: CurrentUser) -> dict:
    return success(data=await part_service.get_part(db, part_id))


@router.put("/{part_id}", response_model=ApiResponse[PartVO], summary="编辑配件")
async def update_part(
    part_id: int,
    payload: PartUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    return success(
        data=await part_service.update_part(db, part_id, payload, current_user_id),
        message="更新成功",
    )


@router.delete(
    "/{part_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除配件",
)
async def delete_part(
    part_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    await part_service.delete_part(db, part_id, current_user_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 适配车型
@router.get(
    "/{part_id}/models",
    response_model=ApiResponse[list[PartVehicleModelDetailVO]],
    summary="配件适配车型",
)
async def list_part_models(part_id: int, db: DbSession, _: CurrentUser) -> dict:
    return success(data=await part_service.list_part_models(db, part_id))


@router.post(
    "/{part_id}/models",
    response_model=ApiResponse[PartVehicleModelDetailVO],
    summary="添加适配车型",
)
async def add_part_model(
    part_id: int,
    payload: PartVehicleModelAdd,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    """车型已适配返回 409；历史删除过的关系会被恢复复用。"""
    return success(
        data=await part_service.add_part_model(db, part_id, payload, current_user_id),
        message="添加成功",
    )


@router.delete(
    "/{part_id}/models/{model_id}",
    response_model=ApiResponse[None],
    summary="移除适配车型",
)
async def delete_part_model(
    part_id: int,
    model_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    """路径中的 modelId 为车型ID（part_vehicle_model.model_id）。"""
    await part_service.delete_part_model(db, part_id, model_id, current_user_id)
    return success(message="删除成功")


# ---------------------------------------------------------------- 单位换算
@router.get(
    "/{part_id}/units",
    response_model=ApiResponse[list[PartUnitConversionVO]],
    summary="配件单位换算",
)
async def list_unit_conversions(part_id: int, db: DbSession, _: CurrentUser) -> dict:
    return success(data=await part_service.list_unit_conversions(db, part_id))


@router.post(
    "/{part_id}/units",
    response_model=ApiResponse[PartUnitConversionVO],
    summary="新增单位换算",
)
async def create_unit_conversion(
    part_id: int,
    payload: PartUnitConversionAdd,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    """源/目标单位相同返回 400，重复换算返回 409。"""
    return success(
        data=await part_service.create_unit_conversion(
            db, part_id, payload, current_user_id
        ),
        message="新增成功",
    )


@router.delete(
    "/{part_id}/units/{conversion_id}",
    response_model=ApiResponse[None],
    summary="删除单位换算",
)
async def delete_unit_conversion(
    part_id: int,
    conversion_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: PartWriteUser,
) -> dict:
    await part_service.delete_unit_conversion(
        db, part_id, conversion_id, current_user_id
    )
    return success(message="删除成功")
