"""FastAPI 应用入口。

启动：uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.response import success
from app.db.session import dispose_engine

# 日志先于一切初始化，保证启动过程日志可被采集
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动/关闭钩子。"""
    logger.info(
        "应用启动 | {} v{} | env={} | debug={}",
        settings.APP_NAME,
        __version__,
        settings.APP_ENV,
        settings.APP_DEBUG,
    )
    yield
    await dispose_engine()
    logger.info("应用已关闭，数据库连接池已释放")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    docs_enabled = not settings.is_production

    application = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="车队配件库存管理系统 API",
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # ---------------- 跨域 ----------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    # ---------------- 异常处理 ----------------
    register_exception_handlers(application)

    # ---------------- 路由注册 ----------------
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ---------------- 健康检查（非业务接口） ----------------
    @application.get("/health", tags=["system"], summary="健康检查")
    async def health() -> dict:
        return success(
            data={
                "status": "ok",
                "name": settings.APP_NAME,
                "version": __version__,
                "env": settings.APP_ENV,
            }
        )

    return application


app: FastAPI = create_app()
