"""出库单接口：分页、新建、详情、编辑草稿、提交审核、审核出库、作废。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户
- 新建 / 编辑 / 提交 / 作废：admin / keeper
- 审核出库：admin / keeper / leader
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.outbound import (
    OutboundOrderCreate,
    OutboundOrderDetailVO,
    OutboundOrderQuery,
    OutboundOrderUpdate,
    OutboundOrderVO,
)
from app.services import outbound_service

__all__ = ["router"]

router = APIRouter()

# 出库单写操作：管理员 / 库管
OutboundWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]
# 审核出库：管理员 / 库管 / 主管
OutboundApproveUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER, Role.LEADER])),
]


@router.get(
    "",
    response_model=ApiResponse[PageResult[OutboundOrderVO]],
    summary="出库单分页列表",
)
async def list_outbound_orders(
    db: DbSession,
    query: Annotated[OutboundOrderQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持单号/备注关键字、仓库、类型、车辆、工单、领用人、状态、创建时间筛选。"""
    return success(data=await outbound_service.list_outbound_orders(db, query))


@router.post(
    "",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="新建出库单",
)
async def create_outbound_order(
    payload: OutboundOrderCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: OutboundWriteUser,
) -> dict:
    """单号由后端生成（OUT + yyyyMMdd + 6 位流水），创建后为草稿状态。

    按件追踪的配件可在明细中直接指定 `inventory_item_id`（扫码出库），
    此时数量必须为 1，库位/批次/成本以库存件实例为准。
    """
    return success(
        data=await outbound_service.create_outbound_order(db, payload, current_user_id),
        message="创建成功",
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="出库单详情",
)
async def get_outbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    _: CurrentUser,
) -> dict:
    return success(data=await outbound_service.get_outbound_order(db, order_id))


@router.put(
    "/{order_id}",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="编辑出库单（仅草稿）",
)
async def update_outbound_order(
    order_id: Annotated[int, Path(ge=1)],
    payload: OutboundOrderUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: OutboundWriteUser,
) -> dict:
    """传 items 时整体替换原明细；非草稿状态返回业务码 3001。"""
    return success(
        data=await outbound_service.update_outbound_order(
            db, order_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.post(
    "/{order_id}/submit",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="提交审核",
)
async def submit_outbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: OutboundWriteUser,
) -> dict:
    """1 草稿 → 2 待审；明细为空、库存件不可用返回 400，非草稿返回 3001。"""
    return success(
        data=await outbound_service.submit_outbound_order(
            db, order_id, current_user_id
        ),
        message="提交成功",
    )


@router.post(
    "/{order_id}/approve",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="审核出库",
)
async def approve_outbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: OutboundApproveUser,
) -> dict:
    """2 待审 → 3 已出库：扣减库存、库存件置为已出库、记流水、关联工单领料。

    非待审状态返回 3001；库存不足返回 2001；库存件已出库/被占用返回
    2003 / 2004；同一库存件重复出库、按件追踪未指定实例返回 400。
    """
    return success(
        data=await outbound_service.approve_outbound_order(
            db, order_id, current_user_id
        ),
        message="出库成功",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[OutboundOrderDetailVO],
    summary="作废出库单",
)
async def cancel_outbound_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: OutboundWriteUser,
) -> dict:
    """草稿/待审 → 4 作废；已出库返回 3001。"""
    return success(
        data=await outbound_service.cancel_outbound_order(
            db, order_id, current_user_id
        ),
        message="作废成功",
    )
