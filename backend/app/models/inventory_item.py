"""库存件实例表 inventory_item（核心新增表）。"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import InventoryItemStatus


class InventoryItem(Base, AuditMixin):
    """逐件追踪的最小库存单元，qrcode 唯一，扫码入口。"""

    __tablename__ = "inventory_item"
    __table_args__ = (
        Index("uk_item_code", "item_code", unique=True),
        Index("uk_qrcode", "qrcode", unique=True),
        Index("idx_part_status", "part_id", "status"),
        Index("idx_warehouse_location", "warehouse_id", "location_id"),
        Index("idx_vehicle", "vehicle_id"),
        Index("idx_batch", "batch_no"),
        {"comment": "库存件实例表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    item_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="库存件唯一编码"
    )
    qrcode: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="二维码内容"
    )
    qrcode_image: Mapped[str | None] = mapped_column(
        String(255), comment="二维码图片路径"
    )
    part_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属配件ID"
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="当前仓库ID"
    )
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="当前库位ID")
    batch_no: Mapped[str | None] = mapped_column(String(50), comment="批次号")
    serial_no: Mapped[str | None] = mapped_column(
        String(100), comment="序列号/出厂编号"
    )
    production_date: Mapped[date | None] = mapped_column(Date, comment="生产日期")
    expire_date: Mapped[date | None] = mapped_column(Date, comment="到期日期")
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        server_default=text("0.0000"),
        comment="该件入库成本",
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=InventoryItemStatus.IN_STOCK,
        server_default=text("1"),
        comment="1在库 2锁定 3已出库 4已报废 5已盘亏",
    )
    inbound_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="来源入库明细ID"
    )
    outbound_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="出库明细ID"
    )
    vehicle_id: Mapped[int | None] = mapped_column(BigInteger, comment="装到哪台车")
    work_order_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联维修工单"
    )
    in_at: Mapped[datetime | None] = mapped_column(DateTime, comment="入库时间")
    out_at: Mapped[datetime | None] = mapped_column(DateTime, comment="出库时间")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
