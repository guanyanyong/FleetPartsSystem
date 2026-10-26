"""操作日志表 operation_log（只读）。"""

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import ReadOnlyMixin


class OperationLog(Base, ReadOnlyMixin):
    """操作日志，只追加不修改。"""

    __tablename__ = "operation_log"
    __table_args__ = (
        Index("idx_user_time", "user_id", "created_at"),
        Index("idx_ref", "ref_type", "ref_id"),
        {"comment": "操作日志表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, comment="操作人ID")
    module: Mapped[str | None] = mapped_column(String(50), comment="模块")
    action: Mapped[str | None] = mapped_column(String(50), comment="动作")
    ref_type: Mapped[str | None] = mapped_column(String(20), comment="关联类型")
    ref_id: Mapped[int | None] = mapped_column(BigInteger, comment="关联ID")
    scan_code: Mapped[str | None] = mapped_column(String(100), comment="扫码原始编码")
    content: Mapped[str | None] = mapped_column(Text, comment="内容")
    ip: Mapped[str | None] = mapped_column(String(50), comment="IP")
