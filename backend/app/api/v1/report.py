"""报表与首页看板接口。

路由前缀（见 docs/backend-requirements.md 9.12）：
- `/api/v1/reports/dashboard`：首页看板
- `/api/v1/reports/inventory`：库存报表（分页）
- `/api/v1/reports/inventory/export`：库存报表导出 Excel
- `/api/v1/reports/transaction`：库存流水报表（分页）
- `/api/v1/reports/vehicle-cost`：单车维修成本（分页）

权限：均为只读查询，所有已登录用户可访问。
"""

from datetime import datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.core.response import ApiResponse, success
from app.schemas.report import (
    DashboardVO,
    InventoryReportQuery,
    InventoryReportResult,
    TransactionReportQuery,
    TransactionReportResult,
    VehicleCostQuery,
    VehicleCostResult,
)
from app.services import report_service

__all__ = ["router"]

router = APIRouter()

EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ---------------------------------------------------------------- 首页看板
@router.get(
    "/dashboard",
    response_model=ApiResponse[DashboardVO],
    summary="首页看板",
)
async def get_dashboard(db: DbSession, _: CurrentUser) -> dict:
    """首页统计：档案数量、库存金额、低库存、待办与本月出入库金额。"""
    return success(data=await report_service.get_dashboard(db))


# ---------------------------------------------------------------- 库存报表
@router.get(
    "/inventory",
    response_model=ApiResponse[InventoryReportResult],
    summary="库存报表",
)
async def list_inventory_report(
    db: DbSession,
    query: Annotated[InventoryReportQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """库存报表分页：按配件 + 仓库 + 库位汇总，并返回筛选结果合计。"""
    return success(data=await report_service.list_inventory_report(db, query))


@router.get(
    "/inventory/export",
    summary="导出库存报表",
    response_class=Response,
)
async def export_inventory_report(
    db: DbSession,
    query: Annotated[InventoryReportQuery, Depends()],
    _: CurrentUser,
) -> Response:
    """按当前筛选条件导出库存报表 Excel（忽略分页）。"""
    content = await report_service.export_inventory_report(db, query)
    filename = f"库存报表_{datetime.now():%Y%m%d%H%M%S}.xlsx"
    return Response(
        content=content,
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                "attachment; filename=inventory_report.xlsx; "
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


# ---------------------------------------------------------------- 流水报表
@router.get(
    "/transaction",
    response_model=ApiResponse[TransactionReportResult],
    summary="库存流水报表",
)
async def list_transaction_report(
    db: DbSession,
    query: Annotated[TransactionReportQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """库存流水报表分页，并返回筛选条件下各业务类型的数量合计。"""
    return success(data=await report_service.list_transaction_report(db, query))


# ---------------------------------------------------------------- 单车成本
@router.get(
    "/vehicle-cost",
    response_model=ApiResponse[VehicleCostResult],
    summary="单车维修成本",
)
async def list_vehicle_cost_report(
    db: DbSession,
    query: Annotated[VehicleCostQuery, Depends()],
    _: CurrentUser,
) -> dict:
    """按车辆统计已完工 / 已结算工单的配件成本与工时费。"""
    return success(data=await report_service.list_vehicle_cost_report(db, query))
