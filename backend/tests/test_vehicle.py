"""车型 / 车辆服务与接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 车辆 VO 扩展字段（车型品牌 / 型号）；
- 编辑时显式 null 的参数校验；
- 车牌号、品牌+车型名称唯一性校验；
- 车型仍有车辆引用时禁止删除、无引用时逻辑删除；
- 请求 Schema 校验与 9 个接口路由注册。

完整事务流程（分页 SQL、数据库落库）需要 MySQL 环境，不在单元测试范围内。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import Vehicle, VehicleModel
from app.models.enums import CommonStatus, VehicleStatus
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleModelUpdate,
    VehicleQuery,
    VehicleUpdate,
)
from app.services import vehicle_service as vehicle

NOW = datetime(2026, 10, 23, 10, 0, 0)


# ---------------------------------------------------------------- 构造内存对象
def _vehicle_model() -> VehicleModel:
    return VehicleModel(
        id=3,
        brand="东风",
        model_name="天锦 KR",
        tonnage="8T",
        status=CommonStatus.ENABLED,
        is_deleted=0,
        created_at=NOW,
    )


def _vehicle() -> Vehicle:
    return Vehicle(
        id=10,
        plate_no="京A12345",
        model_id=3,
        vin="LGAX1234567890",
        engine_no="ISD180",
        department="一车队",
        status=VehicleStatus.IN_USE,
        mileage=12000,
        is_deleted=0,
        created_at=NOW,
    )


class _FakeResult:
    """模拟 AsyncResult 的最小接口。"""

    def __init__(self, scalar: object = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> object:
        return self._scalar

    def scalar_one(self) -> object:
        return self._scalar


class _FakeDb:
    """只实现主数据服务用到的 get / execute / commit。"""

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


# ---------------------------------------------------------------- VO 扩展字段
def test_to_vehicle_vo_fills_model_display_fields() -> None:
    vo = vehicle._to_vehicle_vo(_vehicle(), _vehicle_model())
    assert vo.plate_no == "京A12345"
    assert vo.brand == "东风"
    assert vo.model_name == "天锦 KR"


def test_to_vehicle_vo_tolerates_missing_model() -> None:
    vo = vehicle._to_vehicle_vo(_vehicle(), None)
    assert vo.model_id == 3
    assert vo.brand is None
    assert vo.model_name is None


# ---------------------------------------------------------------- 参数校验
def test_reject_null_raises_400() -> None:
    with pytest.raises(BizException) as exc_info:
        vehicle._reject_null({"plate_no": None}, {"plate_no": "车牌号"})
    assert exc_info.value.code == 400
    assert "车牌号" in exc_info.value.message


def test_reject_null_ignores_absent_field() -> None:
    vehicle._reject_null({"remark": None}, {"plate_no": "车牌号"})


# ---------------------------------------------------------------- 唯一性校验
@pytest.mark.asyncio
async def test_ensure_plate_no_available_rejects_duplicate() -> None:
    with pytest.raises(BizException) as exc_info:
        await vehicle._ensure_plate_no_available(_FakeDb(exists=True), "京A12345")
    assert exc_info.value.code == 409


@pytest.mark.asyncio
async def test_ensure_plate_no_available_passes_when_absent() -> None:
    await vehicle._ensure_plate_no_available(_FakeDb(exists=False), "京A12345")


@pytest.mark.asyncio
async def test_ensure_model_name_available_rejects_duplicate() -> None:
    with pytest.raises(BizException) as exc_info:
        await vehicle._ensure_model_name_available(
            _FakeDb(exists=True), "东风", "天锦 KR"
        )
    assert exc_info.value.code == 409


@pytest.mark.asyncio
async def test_create_vehicle_rejects_duplicated_plate() -> None:
    payload = VehicleCreate(plate_no="京A12345")
    with pytest.raises(BizException) as exc_info:
        await vehicle.create_vehicle(_FakeDb(exists=True), payload, 7)
    assert exc_info.value.code == 409
    assert "车牌号" in exc_info.value.message


@pytest.mark.asyncio
async def test_update_vehicle_rejects_null_plate() -> None:
    db = _FakeDb(exists=False, obj=_vehicle())
    with pytest.raises(BizException) as exc_info:
        await vehicle.update_vehicle(db, 10, VehicleUpdate(plate_no=None), 7)
    assert exc_info.value.code == 400


# ---------------------------------------------------------------- 删除保护
@pytest.mark.asyncio
async def test_delete_vehicle_model_blocked_by_vehicles() -> None:
    db = _FakeDb(exists=True, obj=_vehicle_model())
    with pytest.raises(BizException) as exc_info:
        await vehicle.delete_vehicle_model(db, 3, 7)
    assert exc_info.value.code == 409
    assert "车辆" in exc_info.value.message
    assert db.committed == 0


@pytest.mark.asyncio
async def test_delete_vehicle_model_marks_deleted() -> None:
    model = _vehicle_model()
    db = _FakeDb(exists=False, obj=model)
    await vehicle.delete_vehicle_model(db, 3, 7)
    assert model.is_deleted == 1
    assert model.updated_by == 7
    assert db.committed == 1


# ---------------------------------------------------------------- 请求 Schema
def test_vehicle_create_requires_plate_no() -> None:
    with pytest.raises(ValidationError):
        VehicleCreate(plate_no="")


def test_vehicle_query_defaults_and_status_range() -> None:
    query = VehicleQuery()
    assert query.page == 1
    assert query.page_size == 20
    with pytest.raises(ValidationError):
        VehicleQuery(status=5)


def test_vehicle_model_update_allows_partial_fields() -> None:
    payload = VehicleModelUpdate(tonnage="10T")
    assert payload.model_dump(exclude_unset=True) == {"tonnage": "10T"}


# ---------------------------------------------------------------- 路由注册
def test_vehicle_routes_registered() -> None:
    """确认车型 4 个、车辆 5 个接口均已注册。"""
    paths = app.openapi()["paths"]

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    model_prefix = "/api/v1/vehicle-models"
    assert methods(model_prefix) == {"GET", "POST"}
    assert methods(f"{model_prefix}/{{model_id}}") == {"DELETE", "PUT"}

    prefix = "/api/v1/vehicles"
    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{vehicle_id}}") == {"DELETE", "GET", "PUT"}
