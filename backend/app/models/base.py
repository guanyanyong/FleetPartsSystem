"""模型公共 Mixin：审计字段。

- `AuditMixin`：可编辑表使用，包含 created_by / created_at / updated_by / updated_at / is_deleted
- `ReadOnlyMixin`：只读表（inventory_transaction、operation_log）使用，仅 created_by / created_at
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["AuditMixin", "ReadOnlyMixin"]


class AuditMixin:
    """完整审计字段（写法与 docs/database-design.md 第三节一致）。"""

    created_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="创建人ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="更新人ID"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True, comment="更新时间"
    )
    is_deleted: Mapped[int] = mapped_column(
        TINYINT,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="0正常 1删除",
    )


class ReadOnlyMixin:
    """只读表审计字段。"""

    created_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="创建人ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间",
    )
