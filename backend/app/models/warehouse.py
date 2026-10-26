"""仓库表 warehouse 与库位表 warehouse_location。"""

from sqlalchemy import BigInteger, Index, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin


class Warehouse(Base, AuditMixin):
    """仓库。"""

    __tablename__ = "warehouse"
    __table_args__ = ({"comment": "仓库表"},)

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="仓库名")
    address: Mapped[str | None] = mapped_column(String(255), comment="地址")
    keeper_id: Mapped[int | None] = mapped_column(BigInteger, comment="负责人ID")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )


class WarehouseLocation(Base, AuditMixin):
    """库位。"""

    __tablename__ = "warehouse_location"
    __table_args__ = (
        Index("uk_warehouse_location", "warehouse_id", "location_code", unique=True),
        {"comment": "库位表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="仓库ID"
    )
    location_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="库位编码"
    )
    location_qrcode: Mapped[str | None] = mapped_column(
        String(255), comment="库位二维码内容"
    )
    remark: Mapped[str | None] = mapped_column(String(100), comment="备注")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )
