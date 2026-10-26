"""供应商服务与接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 名称唯一性校验（仅比较未删除数据）；
- 编辑时显式 null 的参数校验；
- 已产生入库单的供应商禁止删除、无关联时逻辑删除；
- 请求 Schema 校验与 5 个接口路由注册。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import Supplier
from app.schemas.supplier import SupplierCreate, SupplierQuery, SupplierUpdate
from app.services import supplier_service as supplier

NOW = datetime(2026, 10, 23, 10, 0, 0)


def _supplier() -> Supplier:
    return Supplier(
        id=5,
        name="东风配件供应站",
        contact="张三",
        phone="13800000000",
        main_category="滤清器",
        payment_term="月结30天",
        status=1,
        is_deleted=0,
        created_at=NOW,
    )


class _FakeResult:
    """模拟 AsyncResult 的最小接口。"""

    def __init__(self, scalar: object = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> object:
        return self._scalar


class _FakeDb:
    """只实现供应商服务用到的 get / execute / commit。"""

    def __init__(self, *, exists: bool, obj: object = None) -> None:
        self._exists = exists
        self._obj = obj
        self.committed = 0

    async def get(self, model: object, pk: int) -> object:
        return self._obj

    async def execute(self, stmt: object) -> _FakeResult:
        return _FakeResult(1 if self._exists else None)

    async def commit(self) -> None:
        self.committed += 1

    async def refresh(self, obj: object) -> None:
        return None


# ---------------------------------------------------------------- 唯一性校验
@pytest.mark.asyncio
async def test_ensure_name_available_rejects_duplicate() -> None:
    with pytest.raises(BizException) as exc_info:
        await supplier._ensure_name_available(_FakeDb(exists=True), "东风配件供应站")
    assert exc_info.value.code == 409
    assert "供应商名称" in exc_info.value.message


@pytest.mark.asyncio
async def test_ensure_name_available_passes_when_absent() -> None:
    await supplier._ensure_name_available(_FakeDb(exists=False), "东风配件供应站")


@pytest.mark.asyncio
async def test_create_supplier_rejects_duplicated_name() -> None:
    payload = SupplierCreate(name="东风配件供应站")
    with pytest.raises(BizException) as exc_info:
        await supplier.create_supplier(_FakeDb(exists=True), payload, 7)
    assert exc_info.value.code == 409


# ---------------------------------------------------------------- 编辑校验
@pytest.mark.asyncio
async def test_update_supplier_rejects_null_name() -> None:
    db = _FakeDb(exists=False, obj=_supplier())
    with pytest.raises(BizException) as exc_info:
        await supplier.update_supplier(db, 5, SupplierUpdate(name=None), 7)
    assert exc_info.value.code == 400


def test_reject_null_ignores_optional_fields() -> None:
    supplier._reject_null({"address": None}, {"name": "供应商名称"})


# ---------------------------------------------------------------- 删除保护
@pytest.mark.asyncio
async def test_delete_supplier_blocked_by_inbound_order() -> None:
    db = _FakeDb(exists=True, obj=_supplier())
    with pytest.raises(BizException) as exc_info:
        await supplier.delete_supplier(db, 5, 7)
    assert exc_info.value.code == 409
    assert "入库单" in exc_info.value.message
    assert db.committed == 0


@pytest.mark.asyncio
async def test_delete_supplier_marks_deleted() -> None:
    entity = _supplier()
    db = _FakeDb(exists=False, obj=entity)
    await supplier.delete_supplier(db, 5, 7)
    assert entity.is_deleted == 1
    assert entity.updated_by == 7
    assert db.committed == 1


# ---------------------------------------------------------------- 请求 Schema
def test_supplier_create_requires_name() -> None:
    with pytest.raises(ValidationError):
        SupplierCreate(name="")


def test_supplier_query_defaults_and_status_range() -> None:
    query = SupplierQuery()
    assert query.page == 1
    assert query.page_size == 20
    assert query.keyword is None
    with pytest.raises(ValidationError):
        SupplierQuery(status=2)


# ---------------------------------------------------------------- 路由注册
def test_supplier_routes_registered() -> None:
    """确认供应商 5 个接口已注册。"""
    paths = app.openapi()["paths"]

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    prefix = "/api/v1/suppliers"
    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{supplier_id}}") == {"DELETE", "GET", "PUT"}
