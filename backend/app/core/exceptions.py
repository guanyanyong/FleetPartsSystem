"""自定义业务异常与全局异常处理器。"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import error_response


class BizException(Exception):
    """业务异常：code 为业务错误码（见需求文档错误码约定）。"""

    def __init__(
        self, code: int = 400, message: str = "业务处理失败", data: Any = None
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


async def biz_exception_handler(request: Request, exc: BizException):
    """业务异常：HTTP 200 + body.code 为业务错误码，便于前端统一处理。"""
    logger.warning(
        "业务异常 | {} {} | code={} | message={}",
        request.method,
        request.url.path,
        exc.code,
        exc.message,
    )
    return error_response(
        code=exc.code, message=exc.message, data=exc.data, status_code=200
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常：统一转换为 code=400。"""
    errors = exc.errors()
    if errors:
        first = errors[0]
        location = ".".join(
            str(item) for item in first.get("loc", ()) if item != "body"
        )
        message = (
            f"{location}: {first.get('msg', '参数校验失败')}"
            if location
            else first.get("msg", "参数校验失败")
        )
    else:
        message = "参数校验失败"

    logger.warning(
        "参数校验失败 | {} {} | {}", request.method, request.url.path, errors
    )
    return error_response(
        code=400,
        message=message,
        data=None if not errors else errors,
        status_code=200,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常：保留原 HTTP 状态码（401/403/404 等），body 使用统一结构。"""
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    logger.warning(
        "HTTP 异常 | {} {} | status={} | {}",
        request.method,
        request.url.path,
        exc.status_code,
        message,
    )
    return error_response(
        code=exc.status_code,
        message=message,
        data=None,
        status_code=exc.status_code,
    )


async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常：记录完整堆栈，对外只返回通用提示。"""
    logger.opt(exception=exc).error(
        "未捕获异常 | {} {} | {}",
        request.method,
        request.url.path,
        exc,
    )
    return error_response(
        code=500, message="服务器内部错误", data=None, status_code=500
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器（在 create_app 中调用）。"""
    app.add_exception_handler(BizException, biz_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)


__all__ = [
    "BizException",
    "biz_exception_handler",
    "global_exception_handler",
    "http_exception_handler",
    "register_exception_handlers",
    "validation_exception_handler",
]
