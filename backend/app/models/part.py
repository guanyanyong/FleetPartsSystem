"""配件相关表：part_category、part、part_vehicle_model、part_unit_conversion。"""

from decimal import Decimal

from sqlalchemy import BigInteger, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin


class PartCategory(Base, AuditMixin):
    """配件分类（树形，parent_id 为父分类）。"""

    __tablename__ = "part_category"
    __table_args__ = ({"comment": "配件分类表"},)

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类名")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, comment="父分类ID")
    sort: Mapped[int | None] = mapped_column(
        Integer, default=0, server_default=text("0"), comment="排序"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )


class Part(Base, AuditMixin):
    """配件主数据。"""

    __tablename__ = "part"
    __table_args__ = (
        Index("uk_part_code", "part_code", unique=True),
        Index("idx_category", "category_id"),
        Index("idx_track", "track_by_item"),
        {"comment": "配件表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="配件业务编码"
    )
    part_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="配件名称"
    )
    category_id: Mapped[int | None] = mapped_column(BigInteger, comment="分类ID")
    spec: Mapped[str | None] = mapped_column(String(100), comment="规格型号")
    brand: Mapped[str | None] = mapped_column(String(50), comment="品牌")
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="个",
        server_default="个",
        comment="基本单位",
    )
    is_general: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="是否通用件 1是 0否",
    )
    safety_stock: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=0,
        server_default=text("0.00"),
        comment="安全库存",
    )
    max_stock: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        default=0,
        server_default=text("0.00"),
        comment="最高库存",
    )
    shelf_life_days: Mapped[int | None] = mapped_column(
        Integer, default=0, server_default=text("0"), comment="保质期天数，0为无"
    )
    track_by_item: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="是否按件追踪，1是则入库逐件生成二维码",
    )
    scan_enabled: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="是否允许扫码出库",
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )


class PartVehicleModel(Base, AuditMixin):
    """配件与车型适配关系（多对多中间表）。"""

    __tablename__ = "part_vehicle_model"
    __table_args__ = (
        Index("uk_part_model", "part_id", "model_id", unique=True),
        {"comment": "配件车型适配表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    model_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="车型ID")
    remark: Mapped[str | None] = mapped_column(String(100), comment="备注")


class PartUnitConversion(Base, AuditMixin):
    """配件单位换算。"""

    __tablename__ = "part_unit_conversion"
    __table_args__ = (
        Index("idx_part", "part_id"),
        {"comment": "配件单位换算表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    from_unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="源单位")
    to_unit: Mapped[str] = mapped_column(String(20), nullable=False, comment="目标单位")
    rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, comment="换算率"
    )
