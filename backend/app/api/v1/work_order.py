"""维修工单接口：分页、新建、详情、编辑、开始维修、完工、结算、领料记录。

权限（见 docs/backend-requirements.md 11.2）：
- 查询：所有已登录用户
- 写操作：admin / keeper
审计字段 created_by / updated_by 由服务层取当前登录用户，前端无需提交。
状态机：1待修 → 2维修中 → 3已完工 → 4已结算，非法流转返回业务码 3001。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, CurrentUserId, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderDetailVO,
    WorkOrderPartVO,
    WorkOrderQuery,
    WorkOrderSettle,
    WorkOrderUpdate,
    WorkOrderVO,
)
from app.services import work_order_service

__all__ = ["router"]

router = APIRouter()

# 工单写操作：管理员 / 库管
WorkOrderWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


@router.get(
    "",
    response_model=ApiResponse[PageResult[WorkOrderVO]],
    summary="维修工单分页列表",
)
async def list_work_orders(
    db: DbSession,
    query: Annotated[WorkOrderQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持工单号关键字、车辆、维修类型、负责人、状态、创建时间筛选。"""
    return success(data=await work_order_service.list_work_orders(db, query))


@router.post(
    "",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="新建维修工单",
)
async def create_work_order(
    payload: WorkOrderCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WorkOrderWriteUser,
) -> dict:
    """工单号由后端生成（WO + yyyyMMdd + 6 位流水），创建后为待修状态。"""
    return success(
        data=await work_order_service.create_work_order(db, payload, current_user_id),
        message="创建成功",
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="维修工单详情",
)
async def get_work_order(order_id: int, db: DbSession, _: CurrentUser) -> dict:
    """详情包含领料记录（parts）。"""
    return success(data=await work_order_service.get_work_order(db, order_id))


@router.put(
    "/{order_id}",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="编辑维修工单",
)
async def update_work_order(
    order_id: int,
    payload: WorkOrderUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WorkOrderWriteUser,
) -> dict:
    """已完工 / 已结算不可编辑；状态、配件成本、工时费不支持在本接口修改。"""
    return success(
        data=await work_order_service.update_work_order(
            db, order_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.post(
    "/{order_id}/start",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="开始维修",
)
async def start_work_order(
    order_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WorkOrderWriteUser,
) -> dict:
    """待修 → 维修中；其它状态返回 3001。"""
    return success(
        data=await work_order_service.start_work_order(db, order_id, current_user_id),
        message="已开始维修",
    )


@router.post(
    "/{order_id}/finish",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="完工",
)
async def finish_work_order(
    order_id: int,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WorkOrderWriteUser,
) -> dict:
    """维修中 → 已完工，同时汇总 work_order_part.cost 到配件总成本。"""
    return success(
        data=await work_order_service.finish_work_order(db, order_id, current_user_id),
        message="已完工",
    )


@router.post(
    "/{order_id}/settle",
    response_model=ApiResponse[WorkOrderDetailVO],
    summary="结算",
)
async def settle_work_order(
    order_id: int,
    payload: WorkOrderSettle,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: WorkOrderWriteUser,
) -> dict:
    """已完工 → 已结算，请求体填写工时费 totalLaborCost。"""
    return success(
        data=await work_order_service.settle_work_order(
            db, order_id, payload, current_user_id
        ),
        message="已结算",
    )


@router.get(
    "/{order_id}/parts",
    response_model=ApiResponse[list[WorkOrderPartVO]],
    summary="工单领料记录",
)
async def list_work_order_parts(
    order_id: int,
    db: DbSession,
    _: CurrentUser,
) -> dict:
    """返回该工单的全部领料记录（出库审核通过时由出库服务写入）。"""
    return success(data=await work_order_service.list_work_order_parts(db, order_id))
