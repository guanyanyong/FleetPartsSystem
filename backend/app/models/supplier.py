"""供应商表 supplier。"""

from sqlalchemy import BigInteger, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin


class Supplier(Base, AuditMixin):
    """供应商。"""

    __tablename__ = "supplier"
    __table_args__ = ({"comment": "供应商表"},)

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="供应商名称")
    contact: Mapped[str | None] = mapped_column(String(50), comment="联系人")
    phone: Mapped[str | None] = mapped_column(String(20), comment="电话")
    address: Mapped[str | None] = mapped_column(String(255), comment="地址")
    main_category: Mapped[str | None] = mapped_column(String(100), comment="主营品类")
    payment_term: Mapped[str | None] = mapped_column(String(50), comment="账期")
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1合作 0停用",
    )
