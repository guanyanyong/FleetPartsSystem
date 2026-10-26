"""库存查询接口：库存汇总、低库存预警、库存件（含编辑）与库存件流水。

路由前缀（见 docs/backend-requirements.md 9.5）：
- `/api/v1/inventory`：库存汇总分页、低库存预警
- `/api/v1/inventory-items`：库存件分页、详情、流水、编辑资料

权限：查询接口所有已登录用户可访问；编辑库存件资料仅管理员 / 库管可操作
（见 docs/backend-requirements.md 11.2）。入库 / 出库 / 调拨 / 盘点数量变动
仍由对应单据接口完成，这里只允许改仓库 / 库位等资料。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.response import ApiResponse, success
from app.models import SysUser
from app.models.enums import Role
from app.schemas.common import PageResult
from app.schemas.inventory import (
    InventoryDetailVO,
    InventoryQuery,
    InventoryTransactionQuery,
    InventoryTransactionVO,
)
from app.schemas.inventory_item import (
    InventoryItemDetailVO,
    InventoryItemQuery,
    InventoryItemUpdate,
)
from app.services import inventory_service

__all__ = ["item_router", "router"]

# /api/v1/inventory：库存汇总与预警
router = APIRouter()
# /api/v1/inventory-items：库存件实例
item_router = APIRouter()

# 库存件写操作：管理员 / 库管
InventoryWriteUser = Annotated[
    SysUser,
    Depends(require_role([Role.ADMIN, Role.KEEPER])),
]


# ---------------------------------------------------------------- 库存汇总
@router.get(
    "",
    response_model=ApiResponse[PageResult[InventoryDetailVO]],
    summary="库存汇总分页",
)
async def list_inventory(
    db: DbSession,
    query: Annotated[InventoryQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """按配件 + 仓库 + 库位汇总分页。

    支持配件编码/名称关键字、配件、仓库、库位筛选；`lowStock=true` 时只返回
    可用数量（quantity - lockedQty）低于安全库存的记录，供列表低库存高亮。
    """
    return success(data=await inventory_service.list_inventory(db, query))


@router.get(
    "/warning",
    response_model=ApiResponse[PageResult[InventoryDetailVO]],
    summary="低库存预警",
)
async def list_inventory_warnings(
    db: DbSession,
    query: Annotated[InventoryQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """低库存预警分页。

    只返回维护了安全库存（`safetyStock > 0`）且可用数量低于安全库存的记录，
    按缺口数量倒序；支持与库存列表相同的配件/仓库/库位筛选。
    """
    return success(data=await inventory_service.list_inventory_warnings(db, query))


# ---------------------------------------------------------------- 库存件
@item_router.get(
    "",
    response_model=ApiResponse[PageResult[InventoryItemDetailVO]],
    summary="库存件分页列表",
)
async def list_inventory_items(
    db: DbSession,
    query: Annotated[InventoryItemQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """库存件实例分页。

    支持库存件编码 / 二维码 / 序列号 / 批次号关键字，以及配件、仓库、库位、
    状态、车辆、工单、批次、到期日（临期）筛选。
    """
    return success(data=await inventory_service.list_inventory_items(db, query))


@item_router.get(
    "/{item_id}",
    response_model=ApiResponse[InventoryItemDetailVO],
    summary="库存件详情",
)
async def get_inventory_item(
    item_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    _: CurrentUser,
) -> dict:
    """库存件详情（含配件、仓库、库位与状态文案），不存在返回 404。"""
    return success(data=await inventory_service.get_inventory_item(db, item_id))


@item_router.put(
    "/{item_id}",
    response_model=ApiResponse[InventoryItemDetailVO],
    summary="编辑库存件",
)
async def update_inventory_item(
    item_id: Annotated[int, Path(ge=1)],
    payload: InventoryItemUpdate,
    db: DbSession,
    user: InventoryWriteUser,
) -> dict:
    """编辑库存件资料（仅更新传入字段）。

    可改：仓库 / 库位、批次号、序列号、生产日期、到期日期、单位成本、备注。
    不可改：库存件编码、二维码、数量、状态、所属配件、车辆 / 工单关联
    （均由入库 / 出库 / 调拨 / 盘点单据维护）。

    仓库 / 库位变更按「单件调拨」记账：同步库存汇总并写 TRANSFER_OUT /
    TRANSFER_IN 流水；仅「在库」实例可调整位置，否则返回 2002 / 2003 / 2004。
    """
    return success(
        data=await inventory_service.update_inventory_item(
            db,
            item_id,
            payload,
            user.id,
        )
    )


@item_router.get(
    "/{item_id}/transactions",
    response_model=ApiResponse[PageResult[InventoryTransactionVO]],
    summary="库存件流水",
)
async def list_inventory_item_transactions(
    item_id: Annotated[int, Path(ge=1)],
    db: DbSession,
    query: Annotated[InventoryTransactionQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """单个库存件的库存流水（只读，按创建时间倒序）。

    路径中的库存件 ID 优先，查询参数中的 `inventoryItemId` 会被忽略；
    可按业务类型、单据类型/单号、时间范围进一步筛选。
    """
    return success(
        data=await inventory_service.list_inventory_item_transactions(
            db, item_id, query
        )
    )
