"""仓库 / 库位服务与接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 仓库内库位编码唯一性校验；
- 编辑库位时按新仓库重新校验库位编码；
- 仓库仍有库位、库位仍有库存时禁止删除；
- 请求 Schema 校验与 9 个接口路由注册。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import Warehouse, WarehouseLocation
from app.schemas.warehouse import (
    WarehouseLocationCreate,
    WarehouseLocationQuery,
    WarehouseLocationUpdate,
    WarehouseQuery,
)
from app.services import warehouse_service as warehouse

NOW = datetime(2026, 10, 23, 10, 0, 0)


def _warehouse() -> Warehouse:
    return Warehouse(
        id=1,
        name="主仓",
        address="厂区东侧",
        keeper_id=7,
        status=1,
        is_deleted=0,
        created_at=NOW,
    )


def _location() -> WarehouseLocation:
    return WarehouseLocation(
        id=8,
        warehouse_id=1,
        location_code="A-01-01",
        location_qrcode="A-01-01",
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
    """只实现仓库服务用到的 get / execute / commit。"""

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
async def test_location_code_rejects_duplicate_in_same_warehouse() -> None:
    with pytest.raises(BizException) as exc_info:
        await warehouse._ensure_location_code_available(
            _FakeDb(exists=True), 1, "A-01-01"
        )
    assert exc_info.value.code == 409
    assert "库位编码" in exc_info.value.message


@pytest.mark.asyncio
async def test_location_code_passes_when_absent() -> None:
    await warehouse._ensure_location_code_available(_FakeDb(exists=False), 1, "A-01-02")


@pytest.mark.asyncio
async def test_create_location_rejects_duplicated_code() -> None:
    payload = WarehouseLocationCreate(warehouse_id=1, location_code="A-01-01")
    db = _FakeDb(exists=True, obj=_warehouse())
    with pytest.raises(BizException) as exc_info:
        await warehouse.create_warehouse_location(db, payload, 7)
    assert exc_info.value.code == 409


# ---------------------------------------------------------------- 编辑库位
@pytest.mark.asyncio
async def test_update_location_rechecks_code_after_warehouse_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = _location()
    calls: list[tuple[int, str, int | None]] = []

    async def fake_ensure(
        db: object,
        warehouse_id: int,
        location_code: str,
        exclude_id: int | None = None,
    ) -> None:
        calls.append((warehouse_id, location_code, exclude_id))

    monkeypatch.setattr(warehouse, "_ensure_location_code_available", fake_ensure)

    db = _FakeDb(exists=False, obj=location)
    vo = await warehouse.update_warehouse_location(
        db, 8, WarehouseLocationUpdate(warehouse_id=2), 7
    )

    assert calls == [(2, "A-01-01", 8)]
    assert location.warehouse_id == 2
    assert location.updated_by == 7
    assert vo.id == 8


@pytest.mark.asyncio
async def test_update_location_rejects_null_code() -> None:
    db = _FakeDb(exists=False, obj=_location())
    with pytest.raises(BizException) as exc_info:
        await warehouse.update_warehouse_location(
            db, 8, WarehouseLocationUpdate(location_code=None), 7
        )
    assert exc_info.value.code == 400


# ---------------------------------------------------------------- 删除保护
@pytest.mark.asyncio
async def test_delete_warehouse_blocked_by_locations() -> None:
    db = _FakeDb(exists=True, obj=_warehouse())
    with pytest.raises(BizException) as exc_info:
        await warehouse.delete_warehouse(db, 1, 7)
    assert exc_info.value.code == 409
    assert "库位" in exc_info.value.message
    assert db.committed == 0


@pytest.mark.asyncio
async def test_delete_location_blocked_by_inventory() -> None:
    location = _location()
    db = _FakeDb(exists=True, obj=location)
    with pytest.raises(BizException) as exc_info:
        await warehouse.delete_warehouse_location(db, 8, 7)
    assert exc_info.value.code == 409
    assert "库存" in exc_info.value.message
    assert location.is_deleted == 0


@pytest.mark.asyncio
async def test_delete_location_marks_deleted() -> None:
    location = _location()
    db = _FakeDb(exists=False, obj=location)
    await warehouse.delete_warehouse_location(db, 8, 7)
    assert location.is_deleted == 1
    assert location.updated_by == 7
    assert db.committed == 1


# ---------------------------------------------------------------- 请求 Schema
def test_location_create_requires_code() -> None:
    with pytest.raises(ValidationError):
        WarehouseLocationCreate(warehouse_id=1, location_code="")


def test_warehouse_query_defaults_and_status_range() -> None:
    query = WarehouseQuery()
    assert query.page == 1
    assert query.page_size == 20
    with pytest.raises(ValidationError):
        WarehouseQuery(status=2)


def test_location_query_filters_by_warehouse() -> None:
    query = WarehouseLocationQuery(warehouse_id=3)
    assert query.warehouse_id == 3
    assert query.status is None


# ---------------------------------------------------------------- 路由注册
def test_warehouse_routes_registered() -> None:
    """确认仓库 5 个、库位 4 个接口均已注册。"""
    paths = app.openapi()["paths"]

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    prefix = "/api/v1/warehouses"
    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{warehouse_id}}") == {"DELETE", "GET", "PUT"}

    location_prefix = "/api/v1/warehouse-locations"
    assert methods(location_prefix) == {"GET", "POST"}
    assert methods(f"{location_prefix}/{{location_id}}") == {"DELETE", "PUT"}
