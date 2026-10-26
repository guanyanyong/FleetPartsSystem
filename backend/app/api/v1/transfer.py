"""调拨单接口：分页、新建、详情、确认调出、确认调入、作废。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户
- 写操作：admin / keeper
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.transfer import (
    TransferOrderCreate,
    TransferOrderDetailVO,
    TransferOrderQuery,
    TransferOrderVO,
)
from app.services import transfer_service

__all__ = ["router"]

router = APIRouter()

# 调拨单写操作：管理员 / 库管
TransferWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


@router.get(
    "",
    response_model=ApiResponse[PageResult[TransferOrderVO]],
    summary="调拨单分页列表",
)
async def list_transfer_orders(
    db: DbSession,
    query: Annotated[TransferOrderQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持单号/备注关键字、调出/调入仓库、状态、经办人、创建时间筛选。"""
    return success(data=await transfer_service.list_transfer_orders(db, query))


@router.post(
    "",
    response_model=ApiResponse[TransferOrderDetailVO],
    summary="新建调拨单",
)
async def create_transfer_order(
    payload: TransferOrderCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: TransferWriteUser,
) -> dict:
    """单号由后端生成（TR + yyyyMMdd + 6 位流水），创建后为草稿状态。

    调出 / 调入仓库不能相同；按件追踪的配件明细必须指定库存件实例且数量为 1；
    同一库存件不能被其它未完成的调拨单重复占用（返回 2004）。
    """
    return success(
        data=await transfer_service.create_transfer_order(db, payload, current_user_id),
        message="创建成功",
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[TransferOrderDetailVO],
    summary="调拨单详情",
)
async def get_transfer_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    _: CurrentUser,
) -> dict:
    return success(data=await transfer_service.get_transfer_order(db, order_id))


@router.post(
    "/{order_id}/transfer-out",
    response_model=ApiResponse[TransferOrderDetailVO],
    summary="确认调出",
)
async def transfer_out(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: TransferWriteUser,
) -> dict:
    """1 草稿 / 2 待审 → 3 已调出：扣减调出仓库库存并写 TRANSFER_OUT 流水。

    逐件追踪的库存件实例同时置为锁定（在途）；库存不足返回 2001，
    库存件不可调出返回 2002 / 2003 / 2004，状态不允许返回 3001。
    """
    return success(
        data=await transfer_service.transfer_out(db, order_id, current_user_id),
        message="已确认调出",
    )


@router.post(
    "/{order_id}/transfer-in",
    response_model=ApiResponse[TransferOrderDetailVO],
    summary="确认调入",
)
async def transfer_in(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: TransferWriteUser,
) -> dict:
    """3 已调出 → 4 已调入：增加调入仓库库存并写 TRANSFER_IN 流水。

    按调出时记录的成本重算移动加权平均成本；逐件追踪实例回填目标仓库 / 库位
    并恢复为在库；非已调出状态返回 3001，实例状态异常返回 409。
    """
    return success(
        data=await transfer_service.transfer_in(db, order_id, current_user_id),
        message="已确认调入",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[TransferOrderDetailVO],
    summary="作废调拨单",
)
async def cancel_transfer_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: TransferWriteUser,
) -> dict:
    """1 草稿 / 2 待审 → 5 作废，不调整库存；其它状态返回 3001。

    已调出的单据库存已扣减，必须完成调入，不允许作废。
    """
    return success(
        data=await transfer_service.cancel_transfer_order(
            db, order_id, current_user_id
        ),
        message="作废成功",
    )
