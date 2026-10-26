"""统一响应封装。

所有接口（含业务错误）返回结构：
    {"code": 200, "message": "success", "data": ...}
分页数据由 data 承载：
    {"list": [], "total": 100, "page": 1, "pageSize": 20}

字段大小写约定：响应统一 camelCase（如 userInfo、pageSize、createdAt），
由 `SchemaBase` 的 alias_generator 生成序列化别名，本模块负责按别名输出。
"""

from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

T = TypeVar("T")

# 统一成功码
SUCCESS_CODE: int = 200
SUCCESS_MESSAGE: str = "success"


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型，可用于接口的 response_model 声明。"""

    code: int = Field(default=SUCCESS_CODE, description="业务状态码")
    message: str = Field(default=SUCCESS_MESSAGE, description="提示信息")
    data: T | None = Field(default=None, description="业务数据")


def _dump_data(data: Any) -> Any:
    """把 Pydantic 模型（含列表/字典嵌套）按序列化别名（camelCase）展开。"""
    if isinstance(data, BaseModel):
        return data.model_dump(by_alias=True)
    if isinstance(data, (list, tuple)):
        return [_dump_data(item) for item in data]
    if isinstance(data, dict):
        return {key: _dump_data(value) for key, value in data.items()}
    return data


def success(
    data: Any = None,
    message: str = SUCCESS_MESSAGE,
    code: int = SUCCESS_CODE,
) -> dict[str, Any]:
    """构造成功响应字典。"""
    return ApiResponse[Any](
        code=code,
        message=message,
        data=_dump_data(data),
    ).model_dump()


def error(
    code: int = 400,
    message: str = "请求参数错误",
    data: Any = None,
) -> dict[str, Any]:
    """构造错误响应字典。"""
    return ApiResponse[Any](
        code=code,
        message=message,
        data=_dump_data(data),
    ).model_dump()


def success_response(
    data: Any = None,
    message: str = SUCCESS_MESSAGE,
    code: int = SUCCESS_CODE,
    status_code: int = 200,
) -> JSONResponse:
    """直接返回 JSONResponse（用于异常处理器等场景）。"""
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(success(data=data, message=message, code=code)),
    )


def error_response(
    code: int = 400,
    message: str = "请求参数错误",
    data: Any = None,
    status_code: int = 200,
) -> JSONResponse:
    """直接返回 JSONResponse；业务错误默认 HTTP 200，错误码放在 body.code。"""
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error(code=code, message=message, data=data)),
    )


__all__ = [
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
    "ApiResponse",
    "error",
    "error_response",
    "success",
    "success_response",
]
