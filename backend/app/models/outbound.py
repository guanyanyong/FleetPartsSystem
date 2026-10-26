"""出库单 outbound_order 与出库单明细 outbound_order_item。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import OrderStatus, OutboundType


class OutboundOrder(Base, AuditMixin):
    """出库单主表。"""

    __tablename__ = "outbound_order"
    __table_args__ = (
        Index("uk_order_no", "order_no", unique=True),
        Index("idx_status", "status"),
        Index("idx_vehicle", "vehicle_id"),
        {"comment": "出库单主表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="出库单号"
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="出库仓库ID"
    )
    outbound_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OutboundType.REPAIR,
        server_default=OutboundType.REPAIR,
        comment="REPAIR/SALE/RETURN/TRANSFER/SCRAP",
    )
    vehicle_id: Mapped[int | None] = mapped_column(BigInteger, comment="关联车辆ID")
    work_order_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联维修工单ID"
    )
    receiver_id: Mapped[int | None] = mapped_column(BigInteger, comment="领用人ID")
    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="总金额"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=OrderStatus.DRAFT,
        server_default=text("1"),
        comment="1草稿 2待审 3已出库 4作废",
    )
    scan_mode: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="是否扫码模式",
    )
    scanner_id: Mapped[int | None] = mapped_column(BigInteger, comment="扫码操作人ID")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="经办人ID")
    audit_user_id: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    audit_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    outbound_at: Mapped[datetime | None] = mapped_column(DateTime, comment="出库时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")


class OutboundOrderItem(Base, AuditMixin):
    """出库单明细。"""

    __tablename__ = "outbound_order_item"
    __table_args__ = (
        Index("idx_order", "order_id"),
        Index("idx_part", "part_id"),
        Index("idx_inventory_item", "inventory_item_id"),
        Index("idx_scan_code", "scan_code"),
        {"comment": "出库单明细表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="出库单ID"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="库存件实例ID"
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="数量"
    )
    unit: Mapped[str | None] = mapped_column(String(20), comment="单位")
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), default=0, server_default=text("0.0000"), comment="单位成本"
    )
    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="金额"
    )
    batch_no: Mapped[str | None] = mapped_column(String(50), comment="批次号")
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="库位ID")
    scan_code: Mapped[str | None] = mapped_column(String(100), comment="扫码原始编码")
    scan_type: Mapped[str | None] = mapped_column(
        String(20), comment="BARCODE/QRCODE/MANUAL"
    )
    scan_at: Mapped[datetime | None] = mapped_column(DateTime, comment="扫码时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
