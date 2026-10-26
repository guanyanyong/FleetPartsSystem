"""盘点单服务 / 接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 数量归一化（两位小数）与差异方向（盘盈为正、盘亏为负）；
- 实盘数量校验：负数、逐件追踪必须为整数、库存件只能 0 / 1；
- 非逐件追踪盘盈 / 盘亏的库存数量与 ADJUST_IN / ADJUST_OUT 流水；
- 逐件追踪盘亏（实例标记已盘亏、item_count 扣减）与盘盈（补建实例 + 二维码）；
- VO 扩展字段（配件、库存件、库位、仓库名称）；
- 请求 Schema 校验与 8 个接口路由注册。

完整事务流程（库存行锁、并发取号、状态流转、数据库落库）需要 MySQL 环境，
不在单元测试范围内。
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    StocktakeOrder,
    StocktakeOrderItem,
    WarehouseLocation,
)
from app.models.enums import (
    BizType,
    InventoryItemStatus,
    RefType,
    StocktakeStatus,
)
from app.schemas.stocktake import (
    StocktakeOrderItemUpdate,
    StocktakeOrderQuery,
    StocktakeScanRequest,
)
from app.services import stocktake_service as stocktake

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


def _order() -> StocktakeOrder:
    return StocktakeOrder(
        id=10,
        order_no="ST20261023000001",
        warehouse_id=2,
        status=StocktakeStatus.COUNTING,
        operator_id=7,
        is_deleted=0,
        created_at=NOW,
    )


def _line(**overrides: object) -> StocktakeOrderItem:
    values: dict[str, object] = {
        "id": 100,
        "order_id": 10,
        "part_id": 1,
        "inventory_item_id": None,
        "location_id": 3,
        "book_qty": Decimal("10.00"),
        "actual_qty": Decimal("8.00"),
        "diff_qty": Decimal("-2.00"),
        "scan_code": None,
        "remark": None,
        "is_deleted": 0,
        "created_at": NOW,
    }
    values.update(overrides)
    return StocktakeOrderItem(**values)


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
        unit_cost=Decimal("12.5000"),
        status=status,
        is_deleted=0,
        created_at=NOW,
    )


class _FakeSession:
    """只实现盘点差异落库用到的 add / flush，便于断言生成的对象。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    def transactions(self) -> list[InventoryTransaction]:
        return [obj for obj in self.added if isinstance(obj, InventoryTransaction)]

    def created_items(self) -> list[InventoryItem]:
        return [obj for obj in self.added if isinstance(obj, InventoryItem)]


# ---------------------------------------------------------------- 数量计算
def test_qty_rounds_half_up_and_defaults_to_zero() -> None:
    assert stocktake._qty(Decimal("1.005")) == Decimal("1.01")
    assert stocktake._qty(None) == Decimal("0.00")


def test_calc_diff_uses_surplus_positive_shortage_negative() -> None:
    assert stocktake._calc_diff(Decimal(12), Decimal(10)) == Decimal("2.00")
    assert stocktake._calc_diff(Decimal(8), Decimal(10)) == Decimal("-2.00")


# ---------------------------------------------------------------- 实盘数量校验
def test_normalize_actual_qty_allows_fraction_for_untracked_part() -> None:
    assert stocktake._normalize_actual_qty(_part(), Decimal("2.50")) == Decimal("2.50")


def test_normalize_actual_qty_rejects_negative() -> None:
    with pytest.raises(BizException) as exc_info:
        stocktake._normalize_actual_qty(_part(), Decimal(-1))
    assert exc_info.value.code == 400


def test_normalize_actual_qty_rejects_fraction_for_tracked_part() -> None:
    with pytest.raises(BizException) as exc_info:
        stocktake._normalize_actual_qty(_part(track_by_item=1), Decimal("1.5"))
    assert exc_info.value.code == 400


@pytest.mark.parametrize("actual_qty", [Decimal(0), Decimal(1)])
def test_normalize_actual_qty_allows_zero_or_one_for_inventory_item(
    actual_qty: Decimal,
) -> None:
    assert (
        stocktake._normalize_actual_qty(
            _part(track_by_item=1),
            actual_qty,
            inventory_item_id=30,
        )
        == actual_qty
    )


def test_normalize_actual_qty_rejects_two_for_inventory_item() -> None:
    with pytest.raises(BizException) as exc_info:
        stocktake._normalize_actual_qty(
            _part(track_by_item=1),
            Decimal(2),
            inventory_item_id=30,
        )
    assert exc_info.value.code == 400


# ---------------------------------------------------------------- 非逐件追踪差异
def test_apply_untracked_surplus_updates_quantity_and_writes_adjust_in() -> None:
    db = _FakeSession()
    order = _order()
    line = _line(actual_qty=Decimal(12), diff_qty=Decimal(2))
    inventory = _inventory()

    stocktake._apply_untracked_diff(
        db,
        order,
        line,
        inventory,
        Decimal("10.00"),
        Decimal("12.00"),
        Decimal("2.00"),
        7,
    )

    assert inventory.quantity == Decimal("12.00")
    assert inventory.item_count == 2  # 非逐件追踪不改变在库实例数
    transactions = db.transactions()
    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.biz_type == BizType.ADJUST_IN
    assert transaction.ref_type == RefType.STOCKTAKE
    assert transaction.ref_no == order.order_no
    assert transaction.change_qty == Decimal("2.00")
    assert transaction.before_qty == Decimal("10.00")
    assert transaction.after_qty == Decimal("12.00")
    assert transaction.operator_id == 7


def test_apply_untracked_shortage_updates_quantity_and_writes_adjust_out() -> None:
    db = _FakeSession()
    line = _line()
    inventory = _inventory()

    stocktake._apply_untracked_diff(
        db,
        _order(),
        line,
        inventory,
        Decimal("10.00"),
        Decimal("8.00"),
        Decimal("-2.00"),
        7,
    )

    assert inventory.quantity == Decimal("8.00")
    transaction = db.transactions()[0]
    assert transaction.biz_type == BizType.ADJUST_OUT
    assert transaction.change_qty == Decimal("-2.00")
    assert transaction.after_qty == Decimal("8.00")


# ---------------------------------------------------------------- 逐件追踪差异
def test_apply_tracked_loss_marks_instance_lost() -> None:
    db = _FakeSession()
    order = _order()
    inventory = _inventory(quantity=Decimal("2.00"), item_count=2)
    inventory_item = _inventory_item()
    line = _line(
        inventory_item_id=inventory_item.id,
        book_qty=Decimal("1.00"),
        actual_qty=Decimal("0.00"),
        diff_qty=Decimal("-1.00"),
    )

    stocktake._apply_tracked_loss(
        db,
        order,
        line,
        _part(track_by_item=1),
        inventory,
        inventory_item,
        Decimal("2.00"),
        Decimal("1.00"),
        7,
    )

    assert inventory_item.status == InventoryItemStatus.LOST
    assert inventory_item.updated_by == 7
    assert inventory.item_count == 1
    assert inventory.quantity == Decimal("1.00")

    transaction = db.transactions()[0]
    assert transaction.biz_type == BizType.ADJUST_OUT
    assert transaction.inventory_item_id == inventory_item.id
    assert transaction.change_qty == Decimal("-1.00")
    assert transaction.unit_cost == Decimal("12.5000")


def test_apply_tracked_loss_rejects_changed_instance_status() -> None:
    """并发出库后实例状态已变化，盘亏直接报 409 让用户重新盘点。"""
    db = _FakeSession()
    inventory_item = _inventory_item(status=InventoryItemStatus.OUT)

    with pytest.raises(BizException) as exc_info:
        stocktake._apply_tracked_loss(
            db,
            _order(),
            _line(
                inventory_item_id=inventory_item.id,
                book_qty=Decimal("1.00"),
                actual_qty=Decimal("0.00"),
                diff_qty=Decimal("-1.00"),
            ),
            _part(track_by_item=1),
            _inventory(quantity=Decimal("1.00"), item_count=1),
            inventory_item,
            Decimal("1.00"),
            Decimal("0.00"),
            7,
        )

    assert exc_info.value.code == 409
    assert inventory_item.item_code in exc_info.value.message
    assert db.added == []


@pytest.mark.asyncio
async def test_apply_tracked_gain_creates_instances_with_qrcode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """盘盈 2 件：生成 2 个库存件编码与二维码，汇总数量 / 实例数同步增加。"""
    requested: list[tuple[str, int]] = []

    async def fake_next_sequences(
        db: object,
        biz_type: str,
        count: int,
        *,
        at: datetime | None = None,
    ) -> list[int]:
        requested.append((biz_type, count))
        return [1, 2]

    monkeypatch.setattr(stocktake, "next_sequences", fake_next_sequences)
    monkeypatch.setattr(
        stocktake,
        "generate_item_code",
        lambda seq, at=None: f"IT20261023{seq:06d}",
    )
    monkeypatch.setattr(
        stocktake,
        "qrcode_file_path",
        lambda item_code: Path("uploads") / f"{item_code}.png",
    )
    monkeypatch.setattr(
        stocktake,
        "generate_qrcode",
        lambda item_code, path: f"/uploads/qrcode/{item_code}.png",
    )

    db = _FakeSession()
    order = _order()
    inventory = _inventory(quantity=Decimal("0.00"), item_count=0)
    line = _line(
        book_qty=Decimal("0.00"),
        actual_qty=Decimal("2.00"),
        diff_qty=Decimal("2.00"),
    )
    qr_files: list[Path] = []

    await stocktake._apply_tracked_gain(
        db,
        order,
        line,
        _part(track_by_item=1),
        inventory,
        Decimal("0.00"),
        Decimal("2.00"),
        7,
        NOW,
        qr_files,
    )

    assert requested == [(stocktake.ITEM_CODE_SEQUENCE, 2)]
    created = db.created_items()
    assert [obj.item_code for obj in created] == [
        "IT20261023000001",
        "IT20261023000002",
    ]
    assert all(obj.status == InventoryItemStatus.IN_STOCK for obj in created)
    assert all(obj.qrcode == obj.item_code for obj in created)
    assert created[0].qrcode_image == "/uploads/qrcode/IT20261023000001.png"
    assert created[0].warehouse_id == order.warehouse_id
    assert created[0].location_id == line.location_id
    assert order.order_no in (created[0].remark or "")
    assert len(qr_files) == 2

    assert inventory.quantity == Decimal("2.00")
    assert inventory.item_count == 2
    transaction = db.transactions()[0]
    assert transaction.biz_type == BizType.ADJUST_IN
    assert transaction.change_qty == Decimal("2.00")
    assert transaction.inventory_item_id is None


# ---------------------------------------------------------------- VO 转换
def test_to_order_vo_fills_warehouse_name() -> None:
    vo = stocktake._to_order_vo(_order(), "主仓库")

    assert vo.order_no == "ST20261023000001"
    assert vo.status == StocktakeStatus.COUNTING
    assert vo.warehouse_name == "主仓库"


def test_to_item_vo_fills_display_fields() -> None:
    """明细 VO 需要带出配件、库存件编码与库位编码，数量按数值序列化。"""
    vo = stocktake._to_item_vo(
        _line(inventory_item_id=30),
        _part(track_by_item=1),
        _inventory_item(),
        WarehouseLocation(
            id=3,
            warehouse_id=2,
            location_code="A-01",
            created_at=NOW,
        ),
    )
    data = vo.model_dump(mode="json", by_alias=True)

    assert data["partCode"] == "P001"
    assert data["partName"] == "机油滤清器"
    assert data["spec"] == "4L"
    assert data["unit"] == "个"
    assert data["itemCode"] == "IT20261023000001"
    assert data["locationCode"] == "A-01"
    assert data["bookQty"] == 10.0
    assert data["actualQty"] == 8.0
    assert data["diffQty"] == -2.0


def test_to_item_vo_tolerates_missing_joins() -> None:
    """历史明细关联的库存件 / 库位被删除时，扩展字段为空但不报错。"""
    vo = stocktake._to_item_vo(_line())

    assert vo.item_code is None
    assert vo.location_code is None
    assert vo.part_name is None


# ---------------------------------------------------------------- 请求 Schema
def test_scan_request_rejects_blank_code() -> None:
    with pytest.raises(ValidationError):
        StocktakeScanRequest(code="")


def test_item_update_accepts_zero_and_rejects_negative() -> None:
    assert StocktakeOrderItemUpdate(actual_qty=Decimal(0)).actual_qty == Decimal(0)
    with pytest.raises(ValidationError):
        StocktakeOrderItemUpdate(actual_qty=Decimal(-1))


def test_query_defaults_and_status_range() -> None:
    query = StocktakeOrderQuery()
    assert query.page == 1
    assert query.page_size == 20
    with pytest.raises(ValidationError):
        StocktakeOrderQuery(status=5)


# ---------------------------------------------------------------- 路由注册
def test_stocktake_routes_registered() -> None:
    """确认盘点单 8 个接口以 /api/v1/stocktake-orders 前缀注册。"""
    paths = app.openapi()["paths"]
    prefix = "/api/v1/stocktake-orders"

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{order_id}}") == {"GET"}
    for action in ("start", "scan", "finish", "cancel"):
        assert methods(f"{prefix}/{{order_id}}/{action}") == {"POST"}
    assert methods(f"{prefix}/{{order_id}}/items/{{item_id}}") == {"PUT"}
