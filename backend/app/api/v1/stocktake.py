"""盘点单接口：分页、新建、详情、开始盘点、扫码、录入实盘、完成、作废。

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
from app.schemas.stocktake import (
    StocktakeOrderCreate,
    StocktakeOrderDetailVO,
    StocktakeOrderItemUpdate,
    StocktakeOrderItemVO,
    StocktakeOrderQuery,
    StocktakeOrderVO,
    StocktakeScanRequest,
)
from app.services import stocktake_service

__all__ = ["router"]

router = APIRouter()

# 盘点单写操作：管理员 / 库管
StocktakeWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


@router.get(
    "",
    response_model=ApiResponse[PageResult[StocktakeOrderVO]],
    summary="盘点单分页列表",
)
async def list_stocktake_orders(
    db: DbSession,
    query: Annotated[StocktakeOrderQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """支持单号/备注关键字、仓库、状态、盘点人、创建时间筛选。"""
    return success(data=await stocktake_service.list_stocktake_orders(db, query))


@router.post(
    "",
    response_model=ApiResponse[StocktakeOrderDetailVO],
    summary="新建盘点单",
)
async def create_stocktake_order(
    payload: StocktakeOrderCreate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """单号由后端生成（ST + yyyyMMdd + 6 位流水），创建后为草稿状态。

    不传 items 时按仓库现有库存自动生成快照（账面数量冻结）；
    传 items 时以库存 / 库存件为准冻结账面，前端提交的 book_qty 不采信。
    """
    return success(
        data=await stocktake_service.create_stocktake_order(
            db, payload, current_user_id
        ),
        message="创建成功",
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[StocktakeOrderDetailVO],
    summary="盘点单详情",
)
async def get_stocktake_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    _: CurrentUser,
) -> dict:
    return success(data=await stocktake_service.get_stocktake_order(db, order_id))


@router.post(
    "/{order_id}/start",
    response_model=ApiResponse[StocktakeOrderDetailVO],
    summary="开始盘点",
)
async def start_stocktake_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """1 草稿 → 2 盘点中；非草稿返回 3001，明细为空返回 400。"""
    return success(
        data=await stocktake_service.start_stocktake_order(
            db, order_id, current_user_id
        ),
        message="已开始盘点",
    )


@router.post(
    "/{order_id}/scan",
    response_model=ApiResponse[StocktakeOrderItemVO],
    summary="扫码盘点",
)
async def scan_stocktake_item(
    order_id: Annotated[int, Path(ge=1)],
    payload: StocktakeScanRequest,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """扫库存件二维码 / 编码，命中明细则标记为已盘（实盘 1 件）。

    仅盘点中状态可扫码（否则 3001）；扫码内容无法识别返回 4001；
    库存件不在库返回 2002；重复扫码返回 409。
    """
    return success(
        data=await stocktake_service.scan_stocktake_item(
            db, order_id, payload, current_user_id
        ),
        message="扫码成功",
    )


@router.put(
    "/{order_id}/items/{item_id}",
    response_model=ApiResponse[StocktakeOrderItemVO],
    summary="修改实盘数量",
)
async def update_stocktake_item(
    order_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    payload: StocktakeOrderItemUpdate,
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """手工录入实盘数量；仅盘点中状态可修改（否则 3001）。

    逐件追踪的库存件明细只能是 0 或 1，其它逐件追踪明细必须为整数。
    """
    return success(
        data=await stocktake_service.update_stocktake_item(
            db, order_id, item_id, payload, current_user_id
        ),
        message="更新成功",
    )


@router.post(
    "/{order_id}/finish",
    response_model=ApiResponse[StocktakeOrderDetailVO],
    summary="完成盘点",
)
async def finish_stocktake_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """2 盘点中 → 3 已完成：按差异调整库存并写 ADJUST_IN / ADJUST_OUT 流水。

    盘盈增加库存（逐件追踪补建带二维码的库存件实例），盘亏扣减库存
    （逐件追踪实例标记为已盘亏）；非盘点中状态返回 3001，
    任一行库存不足 / 库存件状态变更返回 409。
    """
    return success(
        data=await stocktake_service.finish_stocktake_order(
            db, order_id, current_user_id
        ),
        message="盘点完成",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[StocktakeOrderDetailVO],
    summary="作废盘点单",
)
async def cancel_stocktake_order(
    order_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    current_user_id: CurrentUserId,
    _: StocktakeWriteUser,
) -> dict:
    """草稿 / 盘点中 → 4 作废，不调整库存；其它状态返回 3001。"""
    return success(
        data=await stocktake_service.cancel_stocktake_order(
            db, order_id, current_user_id
        ),
        message="作废成功",
    )
