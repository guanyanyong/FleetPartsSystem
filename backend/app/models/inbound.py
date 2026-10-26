"""入库单 inbound_order 与入库单明细 inbound_order_item。"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import InboundType, OrderStatus


class InboundOrder(Base, AuditMixin):
    """入库单主表。"""

    __tablename__ = "inbound_order"
    __table_args__ = (
        Index("uk_order_no", "order_no", unique=True),
        Index("idx_status", "status"),
        {"comment": "入库单主表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="入库单号"
    )
    supplier_id: Mapped[int | None] = mapped_column(BigInteger, comment="供应商ID")
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="入库仓库ID"
    )
    inbound_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InboundType.PURCHASE,
        server_default=InboundType.PURCHASE,
        comment="PURCHASE/RETURN/TRANSFER/ADJUST",
    )
    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="总金额"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=OrderStatus.DRAFT,
        server_default=text("1"),
        comment="1草稿 2待审 3已入库 4作废",
    )
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="经办人ID")
    audit_user_id: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    audit_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    inbound_at: Mapped[datetime | None] = mapped_column(DateTime, comment="入库时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")


class InboundOrderItem(Base, AuditMixin):
    """入库单明细。"""

    __tablename__ = "inbound_order_item"
    __table_args__ = (
        Index("idx_order", "order_id"),
        Index("idx_part", "part_id"),
        {"comment": "入库单明细表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="入库单ID"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="数量"
    )
    unit: Mapped[str | None] = mapped_column(String(20), comment="单位")
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        server_default=text("0.0000"),
        comment="单价",
    )
    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="金额"
    )
    batch_no: Mapped[str | None] = mapped_column(String(50), comment="批次号")
    production_date: Mapped[date | None] = mapped_column(Date, comment="生产日期")
    expire_date: Mapped[date | None] = mapped_column(Date, comment="到期日期")
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="库位ID")
    track_by_item: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="是否逐件追踪",
    )
    generate_item_qty: Mapped[int | None] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        comment="本次生成实例数量",
    )
    generated: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="是否已生成实例",
    )
    scan_code: Mapped[str | None] = mapped_column(String(100), comment="扫码原始编码")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
