"""Alembic 迁移环境（async + asyncmy）。

防误删策略（三层保护）：
1. `include_object`：库里存在、模型未声明的表/索引一律忽略，
   autogenerate 不会生成 `op.drop_table` / `op.drop_index`。
2. `process_revision_directives`：autogenerate 结果里若仍出现删表/删列，直接抛错，
   不会写进迁移脚本。
3. `app/db/migration_guard.py`：执行迁移时在 SQL 层面拦截 DROP TABLE / TRUNCATE 等语句，
   即使有人手写删表迁移也无法执行。

确需破坏性变更时，先设置 `ALEMBIC_ALLOW_DESTRUCTIVE=1` 再执行，并做好备份。
"""

import asyncio
from collections.abc import Iterator
from logging.config import fileConfig

from alembic import context
from alembic.operations import ops
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401  必须导入：否则 Base.metadata 为空，autogenerate 会生成 drop_table
from app.core.config import settings
from app.db.base import Base
from app.db.migration_guard import (
    DestructiveMigrationBlocked,
    allow_destructive,
    install_destructive_guard,
)

config = context.config

# 连接串统一来自 .env；% 需转义以兼容 ConfigParser 插值
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(
    object_, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """忽略数据库里多出来的对象，避免 autogenerate 生成 DROP。"""
    return not (reflected and compare_to is None)


def _walk_ops(container) -> Iterator[object]:
    """递归遍历迁移操作树（ModifyTableOps 等容器）。"""
    for op in container.ops:
        yield op
        nested = getattr(op, "ops", None)
        if nested:
            yield from _walk_ops(op)


def process_revision_directives(context_, revision, directives) -> None:
    """autogenerate 出现删表/删列时中止，防止生成破坏性迁移脚本。"""
    if not directives:
        return
    upgrade_ops = getattr(directives[0], "upgrade_ops", None)
    if upgrade_ops is None:
        return

    blocked = [
        type(op).__name__
        for op in _walk_ops(upgrade_ops)
        if isinstance(op, (ops.DropTableOp, ops.DropColumnOp))
    ]
    if blocked and not allow_destructive():
        raise DestructiveMigrationBlocked(
            "autogenerate 检测到破坏性操作，已中止且未生成迁移脚本："
            f"{sorted(set(blocked))}。\n"
            "请确认这些表/字段是否真的需要删除；确认无误后设置 "
            "ALEMBIC_ALLOW_DESTRUCTIVE=1 重新执行。"
        )


def _common_config() -> dict[str, object]:
    return {
        "target_metadata": target_metadata,
        "include_object": include_object,
        "process_revision_directives": process_revision_directives,
        "compare_type": True,
        # 关闭注释比对：SQLAlchemy 反射 MySQL 的
        # `datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '...'`
        # 时会丢掉 COMMENT，autogenerate 会误判成“注释有变化”，
        # 执行后反而会把 ON UPDATE CURRENT_TIMESTAMP 抹掉。
        "autogenerate_plugins": [
            "alembic.autogenerate.*",
            "~alembic.autogenerate.comments",
        ],
    }


def run_migrations_offline() -> None:
    """离线模式：仅输出 SQL，不连接数据库。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_common_config(),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, **_common_config())

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 执行迁移前的最后一道防线：拦截 DROP TABLE / TRUNCATE 等语句
    install_destructive_guard(connectable.sync_engine)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
