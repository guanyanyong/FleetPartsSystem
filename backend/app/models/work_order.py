"""维修工单 work_order 与工单领料关联 work_order_part。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, Text, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import RepairType, WorkOrderStatus


class WorkOrder(Base, AuditMixin):
    """维修工单。"""

    __tablename__ = "work_order"
    __table_args__ = (
        Index("uk_order_no", "order_no", unique=True),
        Index("idx_vehicle", "vehicle_id"),
        Index("idx_status", "status"),
        {"comment": "维修工单表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    order_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="工单号")
    vehicle_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="车辆ID"
    )
    repair_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RepairType.REPAIR,
        server_default=RepairType.REPAIR,
        comment="MAINTENANCE/REPAIR/ACCIDENT",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="故障描述")
    repair_man_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="维修负责人ID"
    )
    in_at: Mapped[datetime | None] = mapped_column(DateTime, comment="进厂时间")
    out_at: Mapped[datetime | None] = mapped_column(DateTime, comment="出厂时间")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=WorkOrderStatus.WAITING,
        server_default=text("1"),
        comment="1待修 2维修中 3已完工 4已结算",
    )
    total_parts_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="配件总成本"
    )
    total_labor_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="工时费"
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")


class WorkOrderPart(Base, AuditMixin):
    """工单领料记录（关联出库明细）。"""

    __tablename__ = "work_order_part"
    __table_args__ = (
        Index("idx_work_order", "work_order_id"),
        Index("idx_outbound_item", "outbound_item_id"),
        {"comment": "工单领料关联表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    work_order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="工单ID"
    )
    outbound_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="出库明细ID"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=0, server_default=text("0.00"), comment="数量"
    )
    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), default=0, server_default=text("0.00"), comment="成本"
    )
