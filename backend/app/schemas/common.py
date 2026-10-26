"""通用 Schema：分页请求、分页响应、统一响应与审计字段 Mixin。

约定：
- 所有 Schema 继承 `SchemaBase`，其 `model_config` 打开 `from_attributes`，
  因此 `*VO` 可以直接 `XxxVO.model_validate(orm_obj)`。
- 字段名与数据库列名保持一致（snake_case），与 `app/models` 一一对应。
- 统一响应复用 `app.core.response.ApiResponse`，保证响应模型只有一份定义。
"""

import builtins
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from app.core.response import SUCCESS_CODE, SUCCESS_MESSAGE, ApiResponse

T = TypeVar("T")

__all__ = [
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
    "ApiResponse",
    "AuditVO",
    "JsonDecimal",
    "PageQuery",
    "PageResponse",
    "PageResult",
    "ReadOnlyAuditVO",
    "SchemaBase",
]

# 金额/数量/换算率统一按数值输出。
# Pydantic v2 默认把 Decimal 序列化为字符串（"35.50"），前端表单与图表需要数字，
# 故 VO 中的 Decimal 字段统一使用该别名；请求体仍用 Decimal 做精度校验。
JsonDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


class SchemaBase(BaseModel):
    """所有 Schema 的基类。

    - `from_attributes=True`：允许直接从 SQLAlchemy 模型实例构造 VO
    - `alias_generator`：统一生成 camelCase 别名，响应输出 `userInfo` / `pageSize`
    - `populate_by_name=True`：字段名（snake_case）与别名（camelCase）都能赋值，
      服务层用 snake_case 构造、前端用 camelCase 提交均可
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=AliasGenerator(
            validation_alias=to_camel,
            serialization_alias=to_camel,
        ),
    )


class AuditVO(SchemaBase):
    """可编辑表的审计字段，对应 `app.models.base.AuditMixin`。"""

    created_by: int | None = Field(default=None, description="创建人ID")
    created_at: datetime = Field(description="创建时间")
    updated_by: int | None = Field(default=None, description="更新人ID")
    updated_at: datetime | None = Field(default=None, description="更新时间")
    is_deleted: int = Field(default=0, description="0正常 1删除")


class ReadOnlyAuditVO(SchemaBase):
    """只读表（inventory_transaction、operation_log）的审计字段。"""

    created_by: int | None = Field(default=None, description="创建人ID")
    created_at: datetime = Field(description="创建时间")


class PageQuery(SchemaBase):
    """分页请求参数。"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页条数")


class PageResult(SchemaBase, Generic[T]):
    """分页响应数据，作为 `ApiResponse.data` 使用。"""

    # 字段名 list 会遮蔽内建 list，注解里用 builtins.list 避免歧义
    list: builtins.list[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(default=0, ge=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, description="每页条数")


class PageResponse(ApiResponse[PageResult[T]], Generic[T]):
    """分页接口的完整响应：{"code": 200, "message": "success", "data": {...}}。"""
