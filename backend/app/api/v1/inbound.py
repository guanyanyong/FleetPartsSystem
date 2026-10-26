"""入库单接口：分页、新建、详情、编辑草稿、提交审核、审核入库、作废。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户
- 写操作：admin / keeper / purchaser
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.inbound import (
    InboundOrderCreate,
    InboundOrderDetailVO,
    InboundOrderQuery,
    InboundOrderUpdate,
    InboundOrderVO,
)
from app.services import inbound_service

__all__ = ["router"]

router = APIRouter()

# 入库单写操作：管理员 / 库管 / 采购
InboundWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER, Role.PURCHASER])),
]


@router.get(
    "",
    response_model=ApiResponse[PageResult[InboundOrderVO]],
    summary="入库单分页列表",
)
async def list_inbound_orders(
    db: DbSession,
    query: Annotated[InboundOrderQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持单号/备注关键字、供应商、仓库、类型、状态、经办人、创建时间筛选。"""
    return success(data=await inbound_service.list_inbound_orders(db, query))


@router.post(
    "",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="新建入库单",
)
async def create_inbound_order(
    payload: InboundOrderCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: InboundWriteUser,
) -> dict:
    """单号由后端生成（IN + yyyyMMdd + 6 位流水），创建后为草稿状态。"""
    return success(
        data=await inbound_service.create_inbound_order(db, payload, current_user_id),
        message="创建成功",
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="入库单详情",
)
async def get_inbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    _: CurrentUser,
) -> dict:
    return success(data=await inbound_service.get_inbound_order(db, order_id))


@router.put(
    "/{order_id}",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="编辑入库单（仅草稿）",
)
async def update_inbound_order(
    order_id: Annotated[int, Path(ge=1)],
    payload: InboundOrderUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: InboundWriteUser,
) -> dict:
    """传 items 时整体替换原明细；非草稿状态返回业务码 3001。"""
    return success(
        data=await inbound_service.update_inbound_order(
            db, order_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.post(
    "/{order_id}/submit",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="提交审核",
)
async def submit_inbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: InboundWriteUser,
) -> dict:
    """1 草稿 → 2 待审；明细为空返回 400，非草稿返回 3001。"""
    return success(
        data=await inbound_service.submit_inbound_order(db, order_id, current_user_id),
        message="提交成功",
    )


@router.post(
    "/{order_id}/approve",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="审核入库",
)
async def approve_inbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: InboundWriteUser,
) -> dict:
    """2 待审 → 3 已入库：写库存、生成库存件与二维码、记库存流水。

    非待审状态返回 3001；逐件追踪配件数量非整数返回 400；编码用尽/并发冲突返回 409。
    """
    return success(
        data=await inbound_service.approve_inbound_order(db, order_id, current_user_id),
        message="入库成功",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[InboundOrderDetailVO],
    summary="作废入库单",
)
async def cancel_inbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: InboundWriteUser,
) -> dict:
    """草稿/待审 → 4 作废；已入库返回 3001。"""
    return success(
        data=await inbound_service.cancel_inbound_order(db, order_id, current_user_id),
        message="作废成功",
    )
