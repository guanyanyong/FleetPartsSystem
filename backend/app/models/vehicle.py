"""车型表 vehicle_model 与车辆表 vehicle。"""

from datetime import date

from sqlalchemy import BigInteger, Date, Index, Integer, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin


class VehicleModel(Base, AuditMixin):
    """车型。"""

    __tablename__ = "vehicle_model"
    __table_args__ = ({"comment": "车型表"},)

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    brand: Mapped[str] = mapped_column(String(50), nullable=False, comment="品牌")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="型号")
    tonnage: Mapped[str | None] = mapped_column(String(20), comment="吨位/座位")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )


class Vehicle(Base, AuditMixin):
    """车辆。"""

    __tablename__ = "vehicle"
    __table_args__ = (
        Index("uk_plate_no", "plate_no", unique=True),
        Index("idx_model", "model_id"),
        {"comment": "车辆表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    plate_no: Mapped[str] = mapped_column(String(20), nullable=False, comment="车牌号")
    model_id: Mapped[int | None] = mapped_column(BigInteger, comment="车型ID")
    vin: Mapped[str | None] = mapped_column(String(50), comment="车架号")
    engine_no: Mapped[str | None] = mapped_column(String(50), comment="发动机号")
    purchase_date: Mapped[date | None] = mapped_column(Date, comment="购置日期")
    department: Mapped[str | None] = mapped_column(String(50), comment="所属车队/部门")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1在用 2维修 3停用 4报废",
    )
    mileage: Mapped[int | None] = mapped_column(
        Integer, default=0, server_default=text("0"), comment="当前里程"
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
