"""调拨单服务 / 接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 数量归一化（两位小数）与移动加权平均成本重算；
- 明细数量校验：必须大于 0、逐件追踪必须指定实例且数量为 1、非逐件追踪不能指定实例；
- 调出成本提取：优先精确匹配实例 / 库位，缺失时回退实例成本；
- 确认调出扣减库存、流水写入、逐件追踪实例置为在途（锁定）、库存不足拦截；
- 确认调入增加库存、成本按调出成本重算、实例回填仓库 / 库位并恢复在库；
- VO 扩展字段（配件、库存件、库位、仓库名称）；
- 请求 Schema 校验与 6 个接口路由注册。

完整事务流程（库存行锁、并发取号、状态流转、数据库落库）需要 MySQL 环境，
不在单元测试范围内。
"""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import (
    Inventory,
    InventoryItem,
    Part,
    TransferOrder,
    TransferOrderItem,
    WarehouseLocation,
)
from app.models.enums import (
    BizType,
    InventoryItemStatus,
    RefType,
    TransferStatus,
)
from app.schemas.transfer import (
    TransferOrderItemCreate,
    TransferOrderQuery,
)
from app.services import transfer_service as transfer

NOW = datetime(2026, 10, 23, 10, 0, 0)


# ---------------------------------------------------------------- 构造内存对象
def _part(track_by_item: int = 0) -> Part:
    """构造配件主数据（仅内存对象，不落库）。"""
    return Part(
        id=1,
        part_code="P001",
        part_name="机油滤清器",
        spec="4L",
        unit="个",
        track_by_item=track_by_item,
        is_deleted=0,
        created_at=NOW,
    )


def _order() -> TransferOrder:
    return TransferOrder(
        id=10,
        order_no="TR20261023000001",
        from_warehouse_id=2,
        to_warehouse_id=5,
        status=TransferStatus.DRAFT,
        operator_id=7,
        is_deleted=0,
        created_at=NOW,
    )


def _line(**overrides: object) -> TransferOrderItem:
    values: dict[str, object] = {
        "id": 100,
        "order_id": 10,
        "part_id": 1,
        "inventory_item_id": None,
        "quantity": Decimal("2.00"),
        "from_location_id": 3,
        "to_location_id": 4,
        "batch_no": None,
        "remark": None,
        "is_deleted": 0,
        "created_at": NOW,
    }
    values.update(overrides)
    return TransferOrderItem(**values)


def _inventory(
    quantity: Decimal = Decimal("10.00"),
    item_count: int = 2,
) -> Inventory:
    return Inventory(
        id=20,
        part_id=1,
        warehouse_id=2,
        location_id=3,
        quantity=quantity,
        item_count=item_count,
        locked_qty=Decimal("0.00"),
        avg_cost=Decimal("12.5000"),
        is_deleted=0,
        created_at=NOW,
    )


def _inventory_item(
    status: int = InventoryItemStatus.IN_STOCK,
) -> InventoryItem:
    return InventoryItem(
        id=30,
        item_code="IT20261023000001",
        qrcode="IT20261023000001",
        part_id=1,
        warehouse_id=2,
        location_id=3,
        batch_no="B202610",
        unit_cost=Decimal("12.5000"),
        status=status,
        is_deleted=0,
        created_at=NOW,
    )


class _FakeSession:
    """只实现库存写库用到的 add，便于断言生成的流水对象。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


# ---------------------------------------------------------------- 数量与成本
def test_qty_keeps_two_decimals() -> None:
    """数量统一保留两位小数，None 视为 0。"""
    assert transfer._qty(None) == Decimal("0.00")
    assert transfer._qty(3) == Decimal("3.00")
    assert transfer._qty(Decimal("2.5")) == Decimal("2.50")
    assert transfer._qty(Decimal("1.005")) == Decimal("1.01")


def test_calc_avg_cost_recalculates_weighted_average() -> None:
    """移动加权平均：(10×10 + 10×20) ÷ 20 = 15。"""
    avg = transfer._calc_avg_cost(
        Decimal("10.00"), Decimal("10.0000"), Decimal("10.00"), Decimal("20.0000")
    )
    assert avg == Decimal("15.0000")


def test_calc_avg_cost_returns_zero_when_total_empty() -> None:
    """调入后总数量为 0 时成本归零，避免除零。"""
    assert transfer._calc_avg_cost(
        Decimal("0.00"), Decimal("0.0000"), Decimal("0.00"), Decimal("5.0000")
    ) == Decimal("0.0000")


def test_normalize_quantity_rejects_non_positive() -> None:
    with pytest.raises(BizException) as exc:
        transfer._normalize_quantity(_part(), Decimal(0), inventory_item_id=None)
    assert exc.value.code == 400


def test_normalize_quantity_tracked_requires_instance() -> None:
    with pytest.raises(BizException) as exc:
        transfer._normalize_quantity(
            _part(track_by_item=1), Decimal(1), inventory_item_id=None
        )
    assert exc.value.code == 400
    assert "库存件" in exc.value.message


def test_normalize_quantity_tracked_only_one_piece() -> None:
    """逐件追踪一条明细只能调拨一个库存件，数量必须为 1。"""
    assert transfer._normalize_quantity(
        _part(track_by_item=1), Decimal("1.00"), inventory_item_id=30
    ) == Decimal("1.00")
    with pytest.raises(BizException) as exc:
        transfer._normalize_quantity(
            _part(track_by_item=1), Decimal("2.00"), inventory_item_id=30
        )
    assert exc.value.code == 400


def test_normalize_quantity_untracked_rejects_instance() -> None:
    with pytest.raises(BizException) as exc:
        transfer._normalize_quantity(_part(), Decimal(1), inventory_item_id=30)
    assert exc.value.code == 400
    assert "不按件追踪" in exc.value.message


def test_normalize_quantity_untracked_accepts_any_positive() -> None:
    assert transfer._normalize_quantity(
        _part(), Decimal("12.345"), inventory_item_id=None
    ) == Decimal("12.35")


def test_transfer_unit_cost_prefers_exact_match() -> None:
    """成本按 配件 + 调出库位 + 实例 精确匹配，缺失时回退实例成本。"""
    costs = {
        (1, 3, 30): Decimal("20.0000"),
        (1, 3, None): Decimal("15.0000"),
    }
    assert transfer._transfer_unit_cost(
        costs, _line(inventory_item_id=30), None
    ) == Decimal("20.0000")
    assert transfer._transfer_unit_cost(costs, _line(), None) == Decimal("15.0000")
    assert transfer._transfer_unit_cost(
        {}, _line(inventory_item_id=30), _inventory_item()
    ) == Decimal("12.5000")
    assert transfer._transfer_unit_cost({}, _line(), None) == Decimal("0.0000")


# ---------------------------------------------------------------- 确认调出
@pytest.mark.asyncio
async def test_apply_transfer_out_deducts_untracked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非逐件追踪：按 配件 + 调出库位 扣减库存并写 TRANSFER_OUT 流水。"""
    inventory = _inventory()

    async def fake_lock(db, cache, *, part_id, warehouse_id, location_id):
        assert (part_id, warehouse_id, location_id) == (1, 2, 3)
        return inventory

    monkeypatch.setattr(transfer, "_lock_inventory_row", fake_lock)

    db = _FakeSession()
    order = _order()
    item = _line()
    await transfer._apply_transfer_out(db, order, [item], {1: _part()}, {}, 7, NOW)

    assert inventory.quantity == Decimal("8.00")
    assert inventory.item_count == 2
    assert inventory.last_out_at == NOW
    assert inventory.updated_by == 7
    assert len(db.added) == 1

    txn = db.added[0]
    assert txn.biz_type == BizType.TRANSFER_OUT
    assert txn.ref_type == RefType.TRANSFER
    assert txn.ref_id == order.id
    assert txn.ref_no == order.order_no
    assert txn.warehouse_id == 2
    assert txn.location_id == 3
    assert txn.inventory_item_id is None
    assert txn.change_qty == Decimal("-2.00")
    assert txn.before_qty == Decimal("10.00")
    assert txn.after_qty == Decimal("8.00")
    assert txn.unit_cost == Decimal("12.5000")


@pytest.mark.asyncio
async def test_apply_transfer_out_locks_tracked_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """逐件追踪：实例置为锁定（在途），并扣减在库实例数。"""
    inventory = _inventory(item_count=2)
    instance = _inventory_item()

    async def fake_lock(db, cache, *, part_id, warehouse_id, location_id):
        return inventory

    monkeypatch.setattr(transfer, "_lock_inventory_row", fake_lock)

    db = _FakeSession()
    item = _line(inventory_item_id=30, quantity=Decimal("1.00"))
    await transfer._apply_transfer_out(
        db, _order(), [item], {1: _part(track_by_item=1)}, {30: instance}, 7, NOW
    )

    assert instance.status == InventoryItemStatus.LOCKED
    assert instance.updated_by == 7
    assert inventory.quantity == Decimal("9.00")
    assert inventory.item_count == 1
    assert db.added[0].inventory_item_id == 30
    assert db.added[0].scan_code == "IT20261023000001"
    assert db.added[0].batch_no == "B202610"


@pytest.mark.asyncio
async def test_apply_transfer_out_rejects_insufficient_stock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """库存不足时抛 2001，且不修改库存数量。"""
    inventory = _inventory(quantity=Decimal("1.00"))

    async def fake_lock(db, cache, *, part_id, warehouse_id, location_id):
        return inventory

    monkeypatch.setattr(transfer, "_lock_inventory_row", fake_lock)

    db = _FakeSession()
    with pytest.raises(BizException) as exc:
        await transfer._apply_transfer_out(
            db, _order(), [_line()], {1: _part()}, {}, 7, NOW
        )

    assert exc.value.code == transfer.INSUFFICIENT_STOCK
    assert inventory.quantity == Decimal("1.00")
    assert db.added == []


@pytest.mark.asyncio
async def test_apply_transfer_out_rejects_missing_inventory_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """调出仓库 / 库位没有库存行时抛 2001。"""

    async def fake_lock(db, cache, *, part_id, warehouse_id, location_id):
        return None

    monkeypatch.setattr(transfer, "_lock_inventory_row", fake_lock)

    with pytest.raises(BizException) as exc:
        await transfer._apply_transfer_out(
            _FakeSession(), _order(), [_line()], {1: _part()}, {}, 7, NOW
        )
    assert exc.value.code == transfer.INSUFFICIENT_STOCK


# ---------------------------------------------------------------- 确认调入
@pytest.mark.asyncio
async def test_apply_transfer_in_restocks_tracked_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """逐件追踪：库存增加、成本按调出成本重算、实例回到目标仓库 / 库位。"""
    inventory = _inventory(quantity=Decimal("10.00"), item_count=2)
    instance = _inventory_item(status=InventoryItemStatus.LOCKED)

    async def fake_lock(
        db, cache, *, part_id, warehouse_id, location_id, current_user_id
    ):
        assert (part_id, warehouse_id, location_id) == (1, 5, 4)
        return inventory

    monkeypatch.setattr(transfer, "_lock_or_create_inventory", fake_lock)

    db = _FakeSession()
    order = _order()
    order.status = TransferStatus.OUT_DONE
    item = _line(inventory_item_id=30, quantity=Decimal("1.00"))
    costs = {(1, 3, 30): Decimal("20.0000")}
    await transfer._apply_transfer_in(
        db, order, [item], {1: _part(track_by_item=1)}, {30: instance}, costs, 7, NOW
    )

    # (10×12.5 + 1×20) ÷ 11 = 13.1818
    assert inventory.quantity == Decimal("11.00")
    assert inventory.avg_cost == Decimal("13.1818")
    assert inventory.item_count == 3
    assert inventory.last_in_at == NOW
    assert instance.warehouse_id == 5
    assert instance.location_id == 4
    assert instance.status == InventoryItemStatus.IN_STOCK
    assert instance.updated_by == 7

    txn = db.added[0]
    assert txn.biz_type == BizType.TRANSFER_IN
    assert txn.ref_type == RefType.TRANSFER
    assert txn.ref_id == order.id
    assert txn.warehouse_id == 5
    assert txn.location_id == 4
    assert txn.inventory_item_id == 30
    assert txn.change_qty == Decimal("1.00")
    assert txn.before_qty == Decimal("10.00")
    assert txn.after_qty == Decimal("11.00")
    assert txn.unit_cost == Decimal("20.0000")


@pytest.mark.asyncio
async def test_apply_transfer_in_merges_same_target_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一配件调入同一库位的多条明细累加到同一库存行。"""
    inventory = _inventory(quantity=Decimal("0.00"), item_count=0)
    created: list[tuple[int, int, int | None]] = []

    async def fake_lock(
        db, cache, *, part_id, warehouse_id, location_id, current_user_id
    ):
        created.append((part_id, warehouse_id, location_id))
        return inventory

    monkeypatch.setattr(transfer, "_lock_or_create_inventory", fake_lock)

    db = _FakeSession()
    order = _order()
    items = [
        _line(id=100, quantity=Decimal("2.00")),
        _line(id=101, quantity=Decimal("3.00")),
    ]
    await transfer._apply_transfer_in(db, order, items, {1: _part()}, {}, {}, 7, NOW)

    assert created == [(1, 5, 4), (1, 5, 4)]
    assert inventory.quantity == Decimal("5.00")
    assert [txn.change_qty for txn in db.added] == [
        Decimal("2.00"),
        Decimal("3.00"),
    ]
    assert [txn.before_qty for txn in db.added] == [
        Decimal("0.00"),
        Decimal("2.00"),
    ]


@pytest.mark.asyncio
async def test_apply_transfer_in_rejects_tracked_without_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """逐件追踪缺少库存件实例时抛 400，避免汇总数量与在库实例数不一致。"""

    async def fake_lock(db, cache, **kwargs):
        raise AssertionError("校验失败时不应锁定库存行")

    monkeypatch.setattr(transfer, "_lock_or_create_inventory", fake_lock)

    with pytest.raises(BizException) as exc:
        await transfer._apply_transfer_in(
            _FakeSession(),
            _order(),
            [_line(quantity=Decimal("1.00"))],
            {1: _part(track_by_item=1)},
            {},
            {},
            7,
            NOW,
        )
    assert exc.value.code == 400


# ---------------------------------------------------------------- VO 转换
def test_to_order_vo_fills_warehouse_names() -> None:
    vo = transfer._to_order_vo(_order(), "主仓库", "分仓库")

    assert vo.order_no == "TR20261023000001"
    assert vo.status == TransferStatus.DRAFT
    assert vo.from_warehouse_name == "主仓库"
    assert vo.to_warehouse_name == "分仓库"


def test_detail_vo_accepts_order_vo_dump() -> None:
    """详情 VO 由主表 VO 的字段展开构造，明细默认空列表。"""
    from app.schemas.transfer import TransferOrderDetailVO

    detail = TransferOrderDetailVO(
        **transfer._to_order_vo(_order(), "主仓库", "分仓库").model_dump()
    )

    assert detail.order_no == "TR20261023000001"
    assert detail.from_warehouse_name == "主仓库"
    assert detail.items == []


def test_to_item_vo_fills_display_fields() -> None:
    """明细 VO 需要带出配件、库存件编码与库位编码，数量按数值序列化。"""
    vo = transfer._to_item_vo(
        _line(inventory_item_id=30),
        _part(track_by_item=1),
        _inventory_item(),
        WarehouseLocation(
            id=3,
            warehouse_id=2,
            location_code="A-01",
            created_at=NOW,
        ),
        WarehouseLocation(
            id=4,
            warehouse_id=5,
            location_code="B-02",
            created_at=NOW,
        ),
    )
    data = vo.model_dump(mode="json", by_alias=True)

    assert data["partCode"] == "P001"
    assert data["partName"] == "机油滤清器"
    assert data["spec"] == "4L"
    assert data["unit"] == "个"
    assert data["itemCode"] == "IT20261023000001"
    assert data["fromLocationCode"] == "A-01"
    assert data["toLocationCode"] == "B-02"
    assert data["quantity"] == 2.0


def test_to_item_vo_tolerates_missing_joins() -> None:
    """历史明细关联的配件 / 库存件 / 库位被删除时，扩展字段为空但不报错。"""
    vo = transfer._to_item_vo(_line())

    assert vo.part_name is None
    assert vo.item_code is None
    assert vo.from_location_code is None
    assert vo.to_location_code is None


# ---------------------------------------------------------------- 请求 Schema
def test_item_create_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        TransferOrderItemCreate(part_id=1, quantity=Decimal(0))


def test_query_defaults_and_status_range() -> None:
    query = TransferOrderQuery()
    assert query.page == 1
    assert query.page_size == 20
    with pytest.raises(ValidationError):
        TransferOrderQuery(status=6)


# ---------------------------------------------------------------- 路由注册
def test_transfer_routes_registered() -> None:
    """确认调拨单 6 个接口以 /api/v1/transfer-orders 前缀注册。"""
    paths = app.openapi()["paths"]
    prefix = "/api/v1/transfer-orders"

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{order_id}}") == {"GET"}
    for action in ("transfer-out", "transfer-in", "cancel"):
        assert methods(f"{prefix}/{{order_id}}/{action}") == {"POST"}
