"""库存汇总表 inventory。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin


class Inventory(Base, AuditMixin):
    """按 配件 + 仓库 + 库位 汇总的库存。"""

    __tablename__ = "inventory"
    __table_args__ = (
        Index(
            "uk_part_warehouse_location",
            "part_id",
            "warehouse_id",
            "location_id",
            unique=True,
        ),
        {"comment": "库存表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="仓库ID"
    )
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="库位ID")
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0.00"),
        comment="当前数量（汇总）",
    )
    item_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="在库实例数",
    )
    locked_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0.00"),
        comment="锁定数量",
    )
    avg_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        server_default=text("0.0000"),
        comment="移动加权平均成本",
    )
    last_in_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="最后入库时间"
    )
    last_out_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="最后出库时间"
    )
