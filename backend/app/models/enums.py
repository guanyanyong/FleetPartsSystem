"""状态与枚举常量。

对应 docs/database-design.md 第六节「状态机」与 docs/backend-requirements.md 第六节。
数据库中以 TINYINT / VARCHAR 存储，这里使用类常量（而非 Python Enum），
便于与前端数值、字符串直接比对，也方便直接用于 SQL 条件。
"""


class CommonStatus:
    """通用启用状态（status：1启用 0停用）。"""

    DISABLED = 0
    ENABLED = 1


class UserStatus:
    """用户状态。"""

    DISABLED = 0
    ENABLED = 1


class VehicleStatus:
    """车辆状态：1在用 2维修 3停用 4报废。"""

    IN_USE = 1
    REPAIRING = 2
    DISABLED = 3
    SCRAPPED = 4


class InventoryItemStatus:
    """库存件实例状态：1在库 2锁定 3已出库 4已报废 5已盘亏。"""

    IN_STOCK = 1
    LOCKED = 2
    OUT = 3
    SCRAPPED = 4
    LOST = 5


class OrderStatus:
    """入库单 / 出库单状态：1草稿 2待审 3已完成 4作废。"""

    DRAFT = 1
    PENDING = 2
    COMPLETED = 3
    CANCELLED = 4


class TransferStatus:
    """调拨单状态：1草稿 2待审 3已调出 4已调入 5作废。"""

    DRAFT = 1
    PENDING = 2
    OUT_DONE = 3
    IN_DONE = 4
    CANCELLED = 5


class StocktakeStatus:
    """盘点单状态：1草稿 2盘点中 3已完成 4作废。"""

    DRAFT = 1
    COUNTING = 2
    COMPLETED = 3
    CANCELLED = 4


class WorkOrderStatus:
    """维修工单状态：1待修 2维修中 3已完工 4已结算。"""

    WAITING = 1
    REPAIRING = 2
    FINISHED = 3
    SETTLED = 4


class StockAlertStatus:
    """库存预警状态：1未处理 2已处理。"""

    UNHANDLED = 1
    HANDLED = 2


class Role:
    """用户角色（sys_user.role）。"""

    ADMIN = "admin"
    KEEPER = "keeper"
    PURCHASER = "purchaser"
    LEADER = "leader"
    READONLY = "readonly"


class InboundType:
    """入库类型（inbound_order.inbound_type）。"""

    PURCHASE = "PURCHASE"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
    ADJUST = "ADJUST"


class OutboundType:
    """出库类型（outbound_order.outbound_type）。"""

    REPAIR = "REPAIR"
    SALE = "SALE"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
    SCRAP = "SCRAP"


class RepairType:
    """维修类型（work_order.repair_type）。"""

    MAINTENANCE = "MAINTENANCE"
    REPAIR = "REPAIR"
    ACCIDENT = "ACCIDENT"


class BizType:
    """库存流水业务类型（inventory_transaction.biz_type）。"""

    IN = "IN"
    OUT = "OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUST_IN = "ADJUST_IN"
    ADJUST_OUT = "ADJUST_OUT"


class RefType:
    """库存流水关联单据类型（inventory_transaction.ref_type）。"""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    TRANSFER = "TRANSFER"
    STOCKTAKE = "STOCKTAKE"


class AlertType:
    """库存预警类型（stock_alert.alert_type）。"""

    LOW = "LOW"
    HIGH = "HIGH"
    EXPIRING = "EXPIRING"


class ScanType:
    """扫码类型（outbound_order_item.scan_type）。"""

    BARCODE = "BARCODE"
    QRCODE = "QRCODE"
    MANUAL = "MANUAL"


# 库存件状态文案，扫码接口返回 statusText 时使用
INVENTORY_ITEM_STATUS_TEXT: dict[int, str] = {
    InventoryItemStatus.IN_STOCK: "在库",
    InventoryItemStatus.LOCKED: "锁定",
    InventoryItemStatus.OUT: "已出库",
    InventoryItemStatus.SCRAPPED: "已报废",
    InventoryItemStatus.LOST: "已盘亏",
}
