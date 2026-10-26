"""用户表 sys_user。"""

from sqlalchemy import BigInteger, Index, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import AuditMixin
from app.models.enums import Role


class SysUser(Base, AuditMixin):
    """系统用户。"""

    __tablename__ = "sys_user"
    __table_args__ = (
        Index("uk_username", "username", unique=True),
        {"comment": "用户表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="登录名")
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希"
    )
    real_name: Mapped[str | None] = mapped_column(String(50), comment="姓名")
    phone: Mapped[str | None] = mapped_column(String(20), comment="电话")
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=Role.READONLY,
        server_default=Role.READONLY,
        comment="角色：admin/keeper/purchaser/leader/readonly",
    )
    default_warehouse_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="默认仓库ID"
    )
    status: Mapped[int] = mapped_column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="1启用 0停用",
    )
