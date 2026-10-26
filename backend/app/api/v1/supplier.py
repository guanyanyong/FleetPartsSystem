"""供应商接口：分页查询、增删改查。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户（入库需要选供应商）
- 写操作：admin / keeper / purchaser（采购维护供应商主数据）
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.supplier import (
    SupplierCreate,
    SupplierQuery,
    SupplierUpdate,
    SupplierVO,
)
from app.services import supplier_service

__all__ = ["router"]

router = APIRouter()

# 供应商写操作：管理员 / 库管 / 采购
SupplierWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER, Role.PURCHASER])),
]


@router.get(
    "", response_model=ApiResponse[PageResult[SupplierVO]], summary="供应商分页列表"
)
async def list_suppliers(
    db: DbSession,
    query: Annotated[SupplierQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持名称/联系人/电话关键字、主营品类、状态筛选。"""
    return success(data=await supplier_service.list_suppliers(db, query))


@router.post("", response_model=ApiResponse[SupplierVO], summary="新增供应商")
async def create_supplier(
    payload: SupplierCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: SupplierWriteUser,
) -> dict:
    """供应商名称不允许重复（409）。"""
    return success(
        data=await supplier_service.create_supplier(db, payload, current_user_id),
        message="新增成功",
    )


@router.get(
    "/{supplier_id}",
    response_model=ApiResponse[SupplierVO],
    summary="供应商详情",
)
async def get_supplier(supplier_id: int, db: DbSession, _: CurrentUser) -> dict:
    return success(data=await supplier_service.get_supplier(db, supplier_id))


@router.put(
    "/{supplier_id}",
    response_model=ApiResponse[SupplierVO],
    summary="编辑供应商",
)
async def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: SupplierWriteUser,
) -> dict:
    return success(
        data=await supplier_service.update_supplier(
            db, supplier_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.delete(
    "/{supplier_id}",
    response_model=ApiResponse[None],
    summary="逻辑删除供应商",
)
async def delete_supplier(
    supplier_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: SupplierWriteUser,
) -> dict:
    """已存在入库单的供应商不允许删除（409）。"""
    await supplier_service.delete_supplier(db, supplier_id, current_user_id)
    return success(message="删除成功")
