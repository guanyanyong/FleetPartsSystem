"""迁移破坏性 SQL 拦截器。

目的：即使迁移脚本里写了删表语句，也绝不允许在数据库上真正执行。

- 默认拦截：DROP TABLE / DROP DATABASE / DROP SCHEMA / DROP VIEW /
  TRUNCATE / ALTER TABLE ... DROP ...
- 确认要执行破坏性变更时，显式设置环境变量后再跑：
  PowerShell:  $env:ALEMBIC_ALLOW_DESTRUCTIVE = "1"
  bash:        export ALEMBIC_ALLOW_DESTRUCTIVE=1

注意：模块放在 app/db 下而不是 alembic/ 下，避免与第三方 alembic 包同名冲突。
"""

import logging
import os
import re

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("alembic.destructive_guard")

# 只匹配语句开头的破坏性 DDL，避免误伤普通 DML
DESTRUCTIVE_SQL_PATTERN = re.compile(
    r"^\s*(?:"
    r"DROP\s+(?:TABLE|DATABASE|SCHEMA|VIEW)"
    r"|TRUNCATE\b"
    r"|ALTER\s+TABLE\s+\S+\s+DROP\b"
    r")",
    re.IGNORECASE,
)


class DestructiveMigrationBlocked(RuntimeError):
    """迁移中包含被禁止的破坏性语句时抛出。"""


def allow_destructive() -> bool:
    """是否已显式允许破坏性迁移（默认否）。"""
    return os.getenv("ALEMBIC_ALLOW_DESTRUCTIVE", "0") == "1"


def install_destructive_guard(engine: Engine) -> None:
    """在 SQLAlchemy Engine 上挂载破坏性 SQL 拦截器。"""
    if allow_destructive():
        logger.warning(
            "ALEMBIC_ALLOW_DESTRUCTIVE=1，已关闭破坏性 SQL 拦截，请确认这是你想要的"
        )
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _block_destructive_sql(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        if DESTRUCTIVE_SQL_PATTERN.match(statement):
            raise DestructiveMigrationBlocked(
                "已阻止破坏性 SQL 执行（如确需执行，请设置 ALEMBIC_ALLOW_DESTRUCTIVE=1）：\n"
                f"{statement.strip()[:500]}"
            )


__all__ = [
    "DESTRUCTIVE_SQL_PATTERN",
    "DestructiveMigrationBlocked",
    "allow_destructive",
    "install_destructive_guard",
]
