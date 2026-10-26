"""扫码统一入口：库存件扫码识别。

权限：所有已登录用户（入库、出库、盘点、库存查询都会用到扫码）。
扫码失败按业务错误码返回（HTTP 200 + body.code）：
- 2003 已出库 / 2004 已锁定 / 2002 已报废或已盘亏 / 4001 无法识别
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession
from app.core.response import ApiResponse, success
from app.schemas.inventory_item import ScanQuery, ScanResultVO
from app.services import inventory_item_service

__all__ = ["router"]

router = APIRouter()


@router.get(
    "/inventory-item",
    response_model=ApiResponse[ScanResultVO],
    summary="扫码查询库存件",
)
async def scan_inventory_item(
    db: DbSession,
    query: Annotated[ScanQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """按二维码内容或库存件编码查询库存件。

    `code` 支持 `QR:` 前缀与首尾空白；成功返回配件、仓库、库位、成本与状态文案，
    前端可直接把返回结果追加为出库/盘点明细。失败时 `data` 为 null，
    `code` 为 2002/2003/2004/4001。
    """
    return success(
        data=await inventory_item_service.scan_inventory_item(db, query.code)
    )
