"""盘点单 stocktake_order 与盘点单明细 stocktake_order_item。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import StocktakeStatus


class StocktakeOrder(Base, AuditMixin):
    """盘点单主表。"""

    __tablename__ = "stocktake_order"
    __table_args__ = (
        Index("uk_order_no", "order_no", unique=True),
        {"comment": "盘点单主表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="盘点单号"
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="盘点仓库ID"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=StocktakeStatus.DRAFT,
        server_default=text("1"),
        comment="1草稿 2盘点中 3已完成 4作废",
    )
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="盘点人ID")
    audit_user_id: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    stocktake_at: Mapped[datetime | None] = mapped_column(DateTime, comment="盘点时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")


class StocktakeOrderItem(Base, AuditMixin):
    """盘点单明细。"""

    __tablename__ = "stocktake_order_item"
    __table_args__ = (
        Index("idx_order", "order_id"),
        Index("idx_part", "part_id"),
        {"comment": "盘点单明细表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="盘点单ID"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="库存件实例ID"
    )
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="库位ID")
    book_qty: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="账面数量"
    )
    actual_qty: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="实盘数量"
    )
    diff_qty: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="差异数量"
    )
    scan_code: Mapped[str | None] = mapped_column(String(100), comment="扫码原始编码")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
