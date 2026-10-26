"""维修工单服务与接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 金额归一化、维修类型校验；
- VO 扩展字段（车牌号、负责人姓名、配件展示字段）；
- 工单号自动生成（WO + yyyyMMdd + 6 位流水）与创建时的主数据校验；
- 状态机流转：待修 → 维修中 → 已完工（汇总配件成本）→ 已结算（填写工时费）；
- 非法流转返回 3001，编辑接口不允许绕过状态机修改状态 / 金额；
- 请求 Schema 校验与 8 个接口路由注册。

完整事务流程（行锁、并发取号、数据库落库）需要 MySQL 环境，不在单元测试范围内。
"""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import Part, SysUser, Vehicle, WorkOrder, WorkOrderPart
from app.models.enums import CommonStatus, RepairType, WorkOrderStatus
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderQuery,
    WorkOrderSettle,
    WorkOrderUpdate,
)
from app.services import work_order_service as work_order

NOW = datetime(2026, 10, 23, 10, 0, 0)


# ---------------------------------------------------------------- 构造内存对象
def _vehicle() -> Vehicle:
    return Vehicle(
        id=3,
        plate_no="京A12345",
        model_id=1,
        status=1,
        mileage=12000,
        is_deleted=0,
        created_at=NOW,
    )


def _user(status: int = CommonStatus.ENABLED) -> SysUser:
    return SysUser(
        id=7,
        username="keeper",
        password_hash="hash",
        real_name="李四",
        role="keeper",
        status=status,
        is_deleted=0,
        created_at=NOW,
    )


def _order(status: int = WorkOrderStatus.WAITING) -> WorkOrder:
    return WorkOrder(
        id=10,
        order_no="WO20261023000001",
        vehicle_id=3,
        repair_type=RepairType.REPAIR,
        description="更换机油",
        repair_man_id=7,
        in_at=NOW,
        status=status,
        total_parts_cost=Decimal("0.00"),
        total_labor_cost=Decimal("0.00"),
        is_deleted=0,
        created_at=NOW,
    )


def _part() -> Part:
    return Part(
        id=1,
        part_code="P001",
        part_name="机油滤清器",
        spec="0986AF1",
        unit="个",
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
    """只实现工单服务用到的 get / execute / add / commit。"""

    def __init__(
        self,
        *,
        get_map: dict[tuple[object, int], object] | None = None,
        scalar: object = None,
    ) -> None:
        self.get_map = get_map or {}
        self.scalar = scalar
        self.added: list[object] = []
        self.committed = 0

    async def get(self, model: object, pk: int) -> object:
        return self.get_map.get((model, pk))

    async def execute(self, stmt: object) -> _FakeResult:
        return _FakeResult(self.scalar)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        return None


def _async_return(value: object):
    """构造固定返回值的 async 替身。"""

    async def _inner(*args: object, **kwargs: object) -> object:
        return value

    return _inner


# ---------------------------------------------------------------- 工具函数
def test_money_rounds_half_up_and_defaults_to_zero() -> None:
    assert work_order._money(Decimal("1.005")) == Decimal("1.01")
    assert work_order._money(None) == Decimal("0.00")


@pytest.mark.parametrize(
    "repair_type",
    [RepairType.MAINTENANCE, RepairType.REPAIR, RepairType.ACCIDENT],
)
def test_ensure_repair_type_accepts_documented_values(repair_type: str) -> None:
    work_order._ensure_repair_type(repair_type)


def test_ensure_repair_type_rejects_unknown_value() -> None:
    with pytest.raises(BizException) as exc_info:
        work_order._ensure_repair_type("PAINT")
    assert exc_info.value.code == 400


def test_to_order_vo_fills_display_fields() -> None:
    vo = work_order._to_order_vo(_order(), "京A12345", "李四")
    assert vo.order_no == "WO20261023000001"
    assert vo.plate_no == "京A12345"
    assert vo.repair_man_name == "李四"


def test_to_order_vo_tolerates_missing_joins() -> None:
    vo = work_order._to_order_vo(_order())
    assert vo.plate_no is None
    assert vo.repair_man_name is None


def test_to_part_vo_fills_part_fields() -> None:
    line = WorkOrderPart(
        id=30,
        work_order_id=10,
        part_id=1,
        quantity=Decimal("2.00"),
        cost=Decimal("120.00"),
        is_deleted=0,
        created_at=NOW,
    )
    vo = work_order._to_part_vo(line, _part())
    assert vo.part_code == "P001"
    assert vo.part_name == "机油滤清器"
    assert vo.spec == "0986AF1"
    assert vo.unit == "个"
    assert vo.cost == Decimal("120.00")


# ---------------------------------------------------------------- 创建
@pytest.mark.asyncio
async def test_create_work_order_generates_order_no(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """工单号 = WO + yyyyMMdd + 6 位流水，进厂时间默认当前时间。"""
    monkeypatch.setattr(work_order, "next_sequence", _async_return(7))
    monkeypatch.setattr(work_order, "get_work_order", _async_return("detail"))

    db = _FakeDb(get_map={(Vehicle, 3): _vehicle(), (SysUser, 7): _user()})
    payload = WorkOrderCreate(vehicle_id=3, repair_man_id=7)

    result = await work_order.create_work_order(db, payload, 7)

    assert result == "detail"
    order = db.added[0]
    assert isinstance(order, WorkOrder)
    assert order.order_no.startswith("WO")
    assert order.order_no.endswith("000007")
    assert len(order.order_no) == 16
    assert order.status == WorkOrderStatus.WAITING
    assert order.in_at is not None
    assert order.created_by == 7
    assert db.committed == 1


@pytest.mark.asyncio
async def test_create_work_order_rejects_missing_vehicle() -> None:
    db = _FakeDb(get_map={(SysUser, 7): _user()})
    with pytest.raises(BizException) as exc_info:
        await work_order.create_work_order(db, WorkOrderCreate(vehicle_id=3), 7)
    assert exc_info.value.code == 404
    assert "车辆" in exc_info.value.message


@pytest.mark.asyncio
async def test_create_work_order_rejects_disabled_repair_man() -> None:
    db = _FakeDb(
        get_map={
            (Vehicle, 3): _vehicle(),
            (SysUser, 7): _user(status=CommonStatus.DISABLED),
        }
    )
    with pytest.raises(BizException) as exc_info:
        await work_order.create_work_order(
            db, WorkOrderCreate(vehicle_id=3, repair_man_id=7), 7
        )
    assert exc_info.value.code == 400
    assert "停用" in exc_info.value.message


# ---------------------------------------------------------------- 开始维修
@pytest.mark.asyncio
async def test_start_work_order_moves_to_repairing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order(status=WorkOrderStatus.WAITING)
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(order))
    monkeypatch.setattr(work_order, "get_work_order", _async_return("detail"))

    db = _FakeDb()
    await work_order.start_work_order(db, 10, 7)

    assert order.status == WorkOrderStatus.REPAIRING
    assert order.updated_by == 7
    assert db.committed == 1


@pytest.mark.asyncio
async def test_start_work_order_rejects_non_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        work_order,
        "_get_order_or_404",
        _async_return(_order(status=WorkOrderStatus.FINISHED)),
    )
    with pytest.raises(BizException) as exc_info:
        await work_order.start_work_order(_FakeDb(), 10, 7)
    assert exc_info.value.code == 3001


# ---------------------------------------------------------------- 完工
@pytest.mark.asyncio
async def test_sum_parts_cost_uses_decimal_total() -> None:
    assert await work_order._sum_parts_cost(
        _FakeDb(scalar=Decimal("120.5")), 10
    ) == Decimal("120.50")
    assert await work_order._sum_parts_cost(_FakeDb(scalar=None), 10) == Decimal("0.00")


@pytest.mark.asyncio
async def test_finish_work_order_sums_parts_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完工时把 work_order_part.cost 汇总到 total_parts_cost 并置为已完工。"""
    order = _order(status=WorkOrderStatus.REPAIRING)
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(order))
    monkeypatch.setattr(work_order, "_sum_parts_cost", _async_return(Decimal("120.50")))
    monkeypatch.setattr(work_order, "get_work_order", _async_return("detail"))

    db = _FakeDb()
    await work_order.finish_work_order(db, 10, 7)

    assert order.total_parts_cost == Decimal("120.50")
    assert order.status == WorkOrderStatus.FINISHED
    assert order.out_at is not None
    assert order.updated_by == 7
    assert db.committed == 1


@pytest.mark.asyncio
async def test_finish_work_order_rejects_non_repairing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        work_order,
        "_get_order_or_404",
        _async_return(_order(status=WorkOrderStatus.WAITING)),
    )
    with pytest.raises(BizException) as exc_info:
        await work_order.finish_work_order(_FakeDb(), 10, 7)
    assert exc_info.value.code == 3001


# ---------------------------------------------------------------- 结算
@pytest.mark.asyncio
async def test_settle_work_order_fills_labor_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order(status=WorkOrderStatus.FINISHED)
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(order))
    monkeypatch.setattr(work_order, "get_work_order", _async_return("detail"))

    db = _FakeDb()
    payload = WorkOrderSettle(total_labor_cost=Decimal(80), remark="月结")
    await work_order.settle_work_order(db, 10, payload, 7)

    assert order.total_labor_cost == Decimal("80.00")
    assert order.status == WorkOrderStatus.SETTLED
    assert order.remark == "月结"
    assert order.updated_by == 7
    assert db.committed == 1


@pytest.mark.asyncio
async def test_settle_work_order_rejects_not_finished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        work_order,
        "_get_order_or_404",
        _async_return(_order(status=WorkOrderStatus.REPAIRING)),
    )
    with pytest.raises(BizException) as exc_info:
        await work_order.settle_work_order(
            _FakeDb(), 10, WorkOrderSettle(total_labor_cost=Decimal(0)), 7
        )
    assert exc_info.value.code == 3001


# ---------------------------------------------------------------- 编辑
@pytest.mark.asyncio
async def test_update_work_order_rejects_status_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """状态只能通过开始维修 / 完工 / 结算变更。"""
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(_order()))
    payload = WorkOrderUpdate(status=WorkOrderStatus.FINISHED)
    with pytest.raises(BizException) as exc_info:
        await work_order.update_work_order(_FakeDb(), 10, payload, 7)
    assert exc_info.value.code == 3001


@pytest.mark.parametrize("field", ["total_parts_cost", "total_labor_cost"])
@pytest.mark.asyncio
async def test_update_work_order_rejects_cost_fields(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(_order()))
    payload = WorkOrderUpdate(**{field: Decimal("10.00")})
    with pytest.raises(BizException) as exc_info:
        await work_order.update_work_order(_FakeDb(), 10, payload, 7)
    assert exc_info.value.code == 400


@pytest.mark.asyncio
async def test_update_work_order_blocked_after_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        work_order,
        "_get_order_or_404",
        _async_return(_order(status=WorkOrderStatus.FINISHED)),
    )
    with pytest.raises(BizException) as exc_info:
        await work_order.update_work_order(
            _FakeDb(), 10, WorkOrderUpdate(description="补录"), 7
        )
    assert exc_info.value.code == 3001


@pytest.mark.asyncio
async def test_update_work_order_updates_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order()
    monkeypatch.setattr(work_order, "_get_order_or_404", _async_return(order))
    monkeypatch.setattr(work_order, "get_work_order", _async_return("detail"))

    db = _FakeDb(get_map={(SysUser, 7): _user()})
    payload = WorkOrderUpdate(description="更换刹车片", repair_man_id=7)
    await work_order.update_work_order(db, 10, payload, 7)

    assert order.description == "更换刹车片"
    assert order.updated_by == 7
    assert db.committed == 1


# ---------------------------------------------------------------- 请求 Schema
def test_settle_requires_non_negative_labor_cost() -> None:
    with pytest.raises(ValidationError):
        WorkOrderSettle(total_labor_cost=Decimal(-1))


def test_settle_accepts_camel_case_alias() -> None:
    payload = WorkOrderSettle.model_validate({"totalLaborCost": 100})
    assert payload.total_labor_cost == Decimal(100)


def test_work_order_query_defaults_and_status_range() -> None:
    query = WorkOrderQuery()
    assert query.page == 1
    assert query.page_size == 20
    with pytest.raises(ValidationError):
        WorkOrderQuery(status=5)


def test_work_order_update_schema_allows_service_side_validation() -> None:
    payload = WorkOrderUpdate(total_parts_cost=Decimal("10.00"))
    assert payload.model_dump(exclude_unset=True) == {
        "total_parts_cost": Decimal("10.00")
    }


# ---------------------------------------------------------------- 路由注册
def test_work_order_routes_registered() -> None:
    """确认维修工单 8 个接口以 /api/v1/work-orders 前缀注册。"""
    paths = app.openapi()["paths"]
    prefix = "/api/v1/work-orders"

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{order_id}}") == {"GET", "PUT"}
    for action in ("start", "finish", "settle"):
        assert methods(f"{prefix}/{{order_id}}/{action}") == {"POST"}
    assert methods(f"{prefix}/{{order_id}}/parts") == {"GET"}
