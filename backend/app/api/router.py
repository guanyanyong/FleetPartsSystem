"""API 汇总路由。

各业务模块在 `app/api/v1/` 下实现后在注册区补充 include_router，
路径前缀由 `settings.API_V1_PREFIX`（默认 /api/v1）统一控制。
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    inbound,
    inventory,
    outbound,
    part,
    report,
    scan,
    stocktake,
    supplier,
    transfer,
    user,
    vehicle,
    warehouse,
    work_order,
)

api_router = APIRouter()

# ---------------- 认证 ----------------
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# ---------------- 用户 ----------------
api_router.include_router(user.router, prefix="/users", tags=["用户"])

# ---------------- 配件 ----------------
api_router.include_router(
    part.category_router, prefix="/part-categories", tags=["配件分类"]
)
api_router.include_router(part.router, prefix="/parts", tags=["配件"])

# ---------------- 入库 ----------------
api_router.include_router(inbound.router, prefix="/inbound-orders", tags=["入库"])

# ---------------- 出库 ----------------
api_router.include_router(outbound.router, prefix="/outbound-orders", tags=["出库"])

# ---------------- 库存 ----------------
api_router.include_router(inventory.router, prefix="/inventory", tags=["库存"])
api_router.include_router(
    inventory.item_router, prefix="/inventory-items", tags=["库存件"]
)

# ---------------- 盘点 ----------------
api_router.include_router(stocktake.router, prefix="/stocktake-orders", tags=["盘点"])

# ---------------- 扫码 ----------------
api_router.include_router(scan.router, prefix="/scan", tags=["扫码"])

# ---------------- 调拨 ----------------
api_router.include_router(transfer.router, prefix="/transfer-orders", tags=["调拨"])

# ---------------- 车型与车辆 ----------------
api_router.include_router(vehicle.model_router, prefix="/vehicle-models", tags=["车型"])
api_router.include_router(vehicle.router, prefix="/vehicles", tags=["车辆"])

# ---------------- 供应商 ----------------
api_router.include_router(supplier.router, prefix="/suppliers", tags=["供应商"])

# ---------------- 仓库与库位 ----------------
api_router.include_router(warehouse.router, prefix="/warehouses", tags=["仓库"])
api_router.include_router(
    warehouse.location_router, prefix="/warehouse-locations", tags=["库位"]
)

# ---------------- 维修工单 ----------------
api_router.include_router(work_order.router, prefix="/work-orders", tags=["维修工单"])

# ---------------- 报表 ----------------
api_router.include_router(report.router, prefix="/reports", tags=["报表"])

__all__ = ["api_router"]
