"""SQLAlchemy 2.0 声明式基类。

所有模型（app/models/*.py）继承 Base；Alembic 迁移以 Base.metadata 为 target_metadata。
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 统一约束命名，保证 Alembic 自动生成迁移脚本时名称稳定
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """全局 Declarative Base。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        columns = ", ".join(
            f"{column.name}={getattr(self, column.name, None)!r}"
            for column in self.__table__.columns
        )
        return f"<{self.__class__.__name__}({columns})>"


__all__ = ["NAMING_CONVENTION", "Base"]
