"""库存预警表 stock_alert。"""

from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import StockAlertStatus


class StockAlert(Base, AuditMixin):
    """库存预警记录（低库存/高库存/临期）。"""

    __tablename__ = "stock_alert"
    __table_args__ = ({"comment": "库存预警表"},)

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="仓库ID"
    )
    alert_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="LOW/HIGH/EXPIRING"
    )
    current_qty: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="当前数量"
    )
    threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="阈值"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=StockAlertStatus.UNHANDLED,
        server_default=text("1"),
        comment="1未处理 2已处理",
    )
