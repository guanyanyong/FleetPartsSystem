"""baseline：现有数据库结构基线（不执行任何 DDL）。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-22

说明：
- 线上库已有 25 张业务表，本迁移只用于建立 alembic 版本基线。
- 首次接入执行 `alembic stamp head`（或 `alembic upgrade head`），
  只会创建/更新 alembic_version 表，不会创建或删除任何业务表。
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """基线迁移：无操作。"""


def downgrade() -> None:
    """基线回退：无操作（不会删表）。"""
