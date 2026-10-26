"""loguru 日志配置：接管标准库 logging（含 uvicorn 日志）。"""

import logging
import sys
from typing import Any

from loguru import logger

from app.core.config import settings

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 需要接管的标准库 logger
_INTERCEPTED_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "sqlalchemy.engine",
)


class InterceptHandler(logging.Handler):
    """把标准库 logging 的记录转发到 loguru。"""

    def emit(
        self, record: logging.LogRecord
    ) -> None:  # pragma: no cover - 由运行期触发
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 向上追溯调用栈，定位真正的日志输出位置
        frame: Any = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """初始化日志：控制台 + 文件（按天切割、保留 30 天），可重复调用。"""
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = settings.LOG_LEVEL.upper()

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=LOG_FORMAT,
        colorize=True,
        backtrace=settings.APP_DEBUG,
        diagnose=settings.APP_DEBUG,
        enqueue=True,
    )
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=log_level,
        format=LOG_FORMAT,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=settings.APP_DEBUG,
        diagnose=settings.APP_DEBUG,
    )
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=LOG_FORMAT,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.APP_DEBUG,
    )

    # 接管标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in _INTERCEPTED_LOGGERS:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    logger.info(
        "日志初始化完成 | env={} | level={} | dir={}",
        settings.APP_ENV,
        log_level,
        log_dir,
    )


__all__ = ["InterceptHandler", "setup_logging"]
