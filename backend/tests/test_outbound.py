"""出库单服务 / 接口的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 金额计算与四舍五入；
- 出库类型 / 扫码类型 / 库存件状态校验的错误码；
- 请求 Schema 默认值（金额由后端计算）与 VO 的数值序列化；
- 出库单接口路由是否注册完整。

涉及数据库的完整流程（扣减库存、写流水、工单领料）需要 MySQL 环境，
不在单元测试范围内。
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.core.exceptions import BizException
from app.main import app
from app.models import InventoryItem
from app.models.enums import InventoryItemStatus, OutboundType
from app.schemas.outbound import OutboundOrderItemCreate, OutboundOrderItemVO
from app.services import outbound_service as outbound


def _inventory_item(
    item_code: str = "IT20261022000001",
    status: int = InventoryItemStatus.IN_STOCK,
) -> InventoryItem:
    """构造库存件实例（仅内存对象，不落库）。"""
    return InventoryItem(
        item_code=item_code,
        qrcode=f"QRCODE:{item_code}",
        part_id=1,
        warehouse_id=1,
        status=status,
    )


# ---------------------------------------------------------------- 金额计算
def test_line_amount_rounds_half_up() -> None:
    """3 × 1.005 = 3.015，按四舍五入保留两位小数应为 3.02。"""
    assert outbound._line_amount(Decimal(3), Decimal("1.005")) == Decimal("3.02")


def test_line_amount_keeps_two_decimals() -> None:
    assert outbound._line_amount(Decimal("2.5"), Decimal("12.4")) == Decimal("31.00")


def test_sum_amount_empty_rows() -> None:
    """无明细时总金额为 0.00，避免写库出现 NULL。"""
    assert outbound._sum_amount([]) == Decimal("0.00")


def test_sum_amount_accumulates_rows() -> None:
    rows = [{"amount": Decimal("10.10")}, {"amount": Decimal("0.20")}]
    assert outbound._sum_amount(rows) == Decimal("10.30")


# ---------------------------------------------------------------- 取值校验
@pytest.mark.parametrize(
    "outbound_type",
    [
        OutboundType.REPAIR,
        OutboundType.SALE,
        OutboundType.RETURN,
        OutboundType.TRANSFER,
        OutboundType.SCRAP,
    ],
)
def test_ensure_outbound_type_accepts_known_values(outbound_type: str) -> None:
    outbound._ensure_outbound_type(outbound_type)


def test_ensure_outbound_type_rejects_unknown_value() -> None:
    with pytest.raises(BizException) as exc_info:
        outbound._ensure_outbound_type("UNKNOWN")
    assert exc_info.value.code == 400


@pytest.mark.parametrize("scan_type", [None, "BARCODE", "QRCODE", "MANUAL"])
def test_ensure_scan_type_accepts_known_values(scan_type: str | None) -> None:
    outbound._ensure_scan_type(scan_type)


def test_ensure_scan_type_rejects_unknown_value() -> None:
    with pytest.raises(BizException) as exc_info:
        outbound._ensure_scan_type("RFID")
    assert exc_info.value.code == 400


# ---------------------------------------------------------------- 库存件状态
def test_ensure_item_available_passes_for_in_stock() -> None:
    outbound._ensure_item_available(_inventory_item())


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (InventoryItemStatus.OUT, outbound.ITEM_ALREADY_OUT),
        (InventoryItemStatus.LOCKED, outbound.ITEM_LOCKED),
        (InventoryItemStatus.SCRAPPED, outbound.ITEM_NOT_IN_STOCK),
        (InventoryItemStatus.LOST, outbound.ITEM_NOT_IN_STOCK),
    ],
)
def test_ensure_item_available_rejects_unusable_status(
    status: int, expected_code: int
) -> None:
    item = _inventory_item(status=status)
    with pytest.raises(BizException) as exc_info:
        outbound._ensure_item_available(item)
    assert exc_info.value.code == expected_code
    assert item.item_code in exc_info.value.message


# ---------------------------------------------------------------- Schema
def test_item_create_amount_defaults_to_none() -> None:
    """金额不传时由服务层按 数量 × 单位成本 计算。"""
    item = OutboundOrderItemCreate(part_id=1, quantity=Decimal(1))
    assert item.amount is None
    assert item.unit_cost == Decimal(0)


def test_item_vo_serializes_amount_as_number() -> None:
    """VO 中 Decimal 按数值输出，前端无需再解析字符串。"""
    vo = OutboundOrderItemVO(
        id=1,
        order_id=1,
        part_id=1,
        quantity=Decimal("2.00"),
        unit_cost=Decimal("5.2500"),
        amount=Decimal("10.50"),
        part_name="机油滤清器",
        created_at=datetime(2026, 10, 22, 9, 30, 0),
    )
    data = vo.model_dump(mode="json", by_alias=True)
    assert data["quantity"] == 2.0
    assert data["unitCost"] == 5.25
    assert data["amount"] == 10.5
    assert data["partName"] == "机油滤清器"


# ---------------------------------------------------------------- 路由注册
def test_outbound_routes_registered() -> None:
    """确认出库单接口以 /api/v1/outbound-orders 前缀注册。"""
    paths = app.openapi()["paths"]
    prefix = "/api/v1/outbound-orders"

    def methods(path: str) -> set[str]:
        return {method.upper() for method in paths[path]}

    assert methods(prefix) == {"GET", "POST"}
    assert methods(f"{prefix}/{{order_id}}") == {"GET", "PUT"}
    assert methods(f"{prefix}/{{order_id}}/submit") == {"POST"}
    assert methods(f"{prefix}/{{order_id}}/approve") == {"POST"}
    assert methods(f"{prefix}/{{order_id}}/cancel") == {"POST"}
