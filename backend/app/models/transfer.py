"""调拨单 transfer_order 与调拨单明细 transfer_order_item。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import TransferStatus


class TransferOrder(Base, AuditMixin):
    """调拨单主表。"""

    __tablename__ = "transfer_order"
    __table_args__ = (
        Index("uk_order_no", "order_no", unique=True),
        {"comment": "调拨单主表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="调拨单号"
    )
    from_warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="调出仓库ID"
    )
    to_warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="调入仓库ID"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=TransferStatus.DRAFT,
        server_default=text("1"),
        comment="1草稿 2待审 3已调出 4已调入 5作废",
    )
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="经办人ID")
    audit_user_id: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    transfer_at: Mapped[datetime | None] = mapped_column(DateTime, comment="调拨时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")


class TransferOrderItem(Base, AuditMixin):
    """调拨单明细。"""

    __tablename__ = "transfer_order_item"
    __table_args__ = (
        Index("idx_order", "order_id"),
        Index("idx_part", "part_id"),
        {"comment": "调拨单明细表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="调拨单ID"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="库存件实例ID"
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="数量"
    )
    from_location_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="调出库位ID"
    )
    to_location_id: Mapped[int | None] = mapped_column(BigInteger, comment="调入库位ID")
    batch_no: Mapped[str | None] = mapped_column(String(50), comment="批次号")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
