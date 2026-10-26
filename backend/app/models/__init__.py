"""SQLAlchemy 模型包。

导入本包即把所有表注册到 `Base.metadata`（25 张表）。
注意：SQLAlchemy 只在模型类被导入时注册表，新增模型后必须在这里补充导入。
"""

from app.models.inbound import InboundOrder, InboundOrderItem
from app.models.inventory import Inventory
from app.models.inventory_item import InventoryItem
from app.models.inventory_transaction import InventoryTransaction
from app.models.operation_log import OperationLog
from app.models.outbound import OutboundOrder, OutboundOrderItem
from app.models.part import (
    Part,
    PartCategory,
    PartUnitConversion,
    PartVehicleModel,
)
from app.models.stock_alert import StockAlert
from app.models.stocktake import StocktakeOrder, StocktakeOrderItem
from app.models.supplier import Supplier
from app.models.transfer import TransferOrder, TransferOrderItem
from app.models.user import SysUser
from app.models.vehicle import Vehicle, VehicleModel
from app.models.warehouse import Warehouse, WarehouseLocation
from app.models.work_order import WorkOrder, WorkOrderPart

__all__ = [
    "InboundOrder",
    "InboundOrderItem",
    "Inventory",
    "InventoryItem",
    "InventoryTransaction",
    "OperationLog",
    "OutboundOrder",
    "OutboundOrderItem",
    "Part",
    "PartCategory",
    "PartUnitConversion",
    "PartVehicleModel",
    "StockAlert",
    "StocktakeOrder",
    "StocktakeOrderItem",
    "Supplier",
    "SysUser",
    "TransferOrder",
    "TransferOrderItem",
    "Vehicle",
    "VehicleModel",
    "Warehouse",
    "WarehouseLocation",
    "WorkOrder",
    "WorkOrderPart",
]
