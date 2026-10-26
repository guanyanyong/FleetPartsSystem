"""库存查询与库存件编辑模块的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 库存汇总 / 库存件的 VO 转换（配件、仓库、库位、状态文案）；
- 低库存条件：按可用数量（quantity - locked_qty）与安全库存比较；
- 库存件查询条件拼装（关键字、状态、临期）；
- 编辑库存件：Schema 只允许资料类字段、移动加权平均成本重算、状态可移动校验；
- 库存查询 / 编辑接口路由注册。

涉及数据库的完整查询与写事务需要 MySQL 环境，不在单元测试范围内。
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import BizException
from app.main import app
from app.models import (
    Inventory,
    InventoryItem,
    InventoryTransaction,
    Part,
    Warehouse,
    WarehouseLocation,
)
from app.models.enums import InventoryItemStatus
from app.schemas.inventory import InventoryQuery, InventoryTransactionVO
from app.schemas.inventory_item import InventoryItemQuery, InventoryItemUpdate
from app.services import inventory_service as inventory

NOW = datetime(2026, 10, 23, 12, 0, 0)


# ---------------------------------------------------------------- 构造内存对象
def _part() -> Part:
    """构造配件主数据（仅内存对象，不落库）。"""
    return Part(
        id=1,
        part_code="P001",
        part_name="机油滤清器",
        spec="4L",
        unit="个",
        safety_stock=Decimal("5.00"),
        max_stock=Decimal("50.00"),
        is_deleted=0,
        created_at=NOW,
    )


def _inventory() -> Inventory:
    return Inventory(
        id=10,
        part_id=1,
        warehouse_id=2,
        location_id=3,
        quantity=Decimal("3.00"),
        item_count=2,
        locked_qty=Decimal("1.00"),
        avg_cost=Decimal("12.5000"),
        is_deleted=0,
        created_at=NOW,
    )


def _item(status: int = InventoryItemStatus.IN_STOCK) -> InventoryItem:
    return InventoryItem(
        id=100,
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


# ---------------------------------------------------------------- VO 转换
def test_to_inventory_detail_vo_fills_joined_fields() -> None:
    """库存汇总 VO 需要带出配件、仓库、库位与安全库存。"""
    vo = inventory._to_inventory_detail_vo(
        _inventory(),
        _part(),
        Warehouse(id=2, name="主仓库", created_at=NOW),
        WarehouseLocation(
            id=3,
            warehouse_id=2,
            location_code="A-01",
            created_at=NOW,
        ),
    )

    assert vo.part_code == "P001"
    assert vo.part_name == "机油滤清器"
    assert vo.spec == "4L"
    assert vo.unit == "个"
    assert vo.quantity == Decimal("3.00")
    assert vo.safety_stock == Decimal("5.00")
    assert vo.warehouse_name == "主仓库"
    assert vo.location_code == "A-01"


def test_to_inventory_detail_vo_accepts_missing_location() -> None:
    """仓库级库存（location_id 为空）不报错，库位编码为 None。"""
    vo = inventory._to_inventory_detail_vo(
        _inventory(),
        _part(),
        Warehouse(id=2, name="主仓库", created_at=NOW),
        None,
    )

    assert vo.warehouse_name == "主仓库"
    assert vo.location_code is None


def test_to_inventory_item_detail_vo_fills_status_text() -> None:
    """库存件 VO 需要带出配件信息与中文状态文案。"""
    vo = inventory._to_inventory_item_detail_vo(
        _item(),
        _part(),
        Warehouse(id=2, name="主仓库", created_at=NOW),
        WarehouseLocation(
            id=3,
            warehouse_id=2,
            location_code="A-01",
            created_at=NOW,
        ),
    )

    assert vo.item_code == "IT20261023000001"
    assert vo.part_name == "机油滤清器"
    assert vo.status_text == "在库"
    assert vo.warehouse_name == "主仓库"
    assert vo.location_code == "A-01"


def test_to_inventory_item_detail_vo_tolerates_deleted_part() -> None:
    """配件已逻辑删除（join 不到）时库存件详情仍可展示。"""
    vo = inventory._to_inventory_item_detail_vo(
        _item(InventoryItemStatus.OUT),
        None,
        None,
        None,
    )

    assert vo.part_code is None
    assert vo.status_text == "已出库"
    assert vo.warehouse_name is None


def test_transaction_vo_validates_orm_object() -> None:
    """流水 VO 可直接由 ORM 实例构造，数量与单号保持原值。"""
    transaction = InventoryTransaction(
        id=1,
        part_id=1,
        inventory_item_id=100,
        warehouse_id=2,
        location_id=3,
        biz_type="OUT",
        change_qty=Decimal("-1.00"),
        before_qty=Decimal("3.00"),
        after_qty=Decimal("2.00"),
        ref_type="OUTBOUND",
        ref_id=9,
        ref_no="OUT20261023000001",
        created_at=NOW,
    )

    vo = InventoryTransactionVO.model_validate(transaction)

    assert vo.biz_type == "OUT"
    assert vo.inventory_item_id == 100
    assert vo.ref_no == "OUT20261023000001"
    assert vo.after_qty == Decimal("2.00")


# ---------------------------------------------------------------- 查询条件
def test_low_stock_conditions_use_available_quantity() -> None:
    """低库存判定必须扣减锁定数量，并排除未维护安全库存的配件。"""
    rendered = [
        str(condition)
        for condition in inventory._inventory_conditions(InventoryQuery(low_stock=True))
    ]
    sql = " AND ".join(rendered)

    assert "inventory.quantity - inventory.locked_qty < part.safety_stock" in sql
    assert "part.safety_stock > " in sql
    assert "part.safety_stock IS NOT NULL" in sql


def test_inventory_conditions_skip_low_stock_by_default() -> None:
    """未开启 low_stock 时不附加安全库存条件。"""
    rendered = [
        str(condition)
        for condition in inventory._inventory_conditions(InventoryQuery())
    ]

    assert all("safety_stock" not in condition for condition in rendered)


def test_inventory_conditions_support_keyword_and_filters() -> None:
    """关键字模糊匹配配件编码/名称，并按配件、仓库、库位过滤。"""
    sql = " AND ".join(
        str(condition)
        for condition in inventory._inventory_conditions(
            InventoryQuery(keyword=" 机油 ", part_id=1, warehouse_id=2, location_id=3)
        )
    )

    assert "part.part_code LIKE" in sql
    assert "part.part_name LIKE" in sql
    assert "inventory.part_id = " in sql
    assert "inventory.warehouse_id = " in sql
    assert "inventory.location_id = " in sql
    assert "inventory.is_deleted = " in sql
    assert "part.is_deleted = " in sql


def test_inventory_item_conditions_support_item_filters() -> None:
    """库存件查询支持编码/二维码/序列号/批次号关键字、状态与临期筛选。"""
    sql = " AND ".join(
        str(condition)
        for condition in inventory._inventory_item_conditions(
            InventoryItemQuery(
                keyword="IT2026",
                part_id=1,
                warehouse_id=2,
                location_id=3,
                status=InventoryItemStatus.IN_STOCK,
                batch_no=" B2026 ",
                expire_before=date(2026, 12, 31),
            )
        )
    )

    assert "inventory_item.item_code LIKE" in sql
    assert "inventory_item.qrcode LIKE" in sql
    assert "inventory_item.serial_no LIKE" in sql
    assert "inventory_item.batch_no LIKE" in sql
    assert "inventory_item.status = " in sql
    assert "inventory_item.batch_no = " in sql
    assert "inventory_item.expire_date IS NOT NULL" in sql
    assert "inventory_item.expire_date <= " in sql


# ---------------------------------------------------------------- 编辑库存件
def test_inventory_item_update_schema_only_allows_profile_fields() -> None:
    """编辑库存件只接收资料类字段：编码 / 二维码 / 数量 / 状态都不在 Schema 内。"""
    fields = set(InventoryItemUpdate.model_fields)

    assert fields == {
        "warehouse_id",
        "location_id",
        "batch_no",
        "serial_no",
        "production_date",
        "expire_date",
        "unit_cost",
        "remark",
    }
    assert not fields & set(inventory.LOCKED_EDIT_FIELDS)


def test_inventory_item_update_schema_accepts_partial_camel_case_payload() -> None:
    """前端 camelCase 提交可用，未被提交的字段不会出现在 exclude_unset 结果里。"""
    payload = InventoryItemUpdate.model_validate(
        {"warehouseId": 5, "locationId": None, "batchNo": "B2026"}
    )

    assert payload.model_dump(exclude_unset=True) == {
        "warehouse_id": 5,
        "location_id": None,
        "batch_no": "B2026",
    }
    assert InventoryItemUpdate().model_dump(exclude_unset=True) == {}


def test_inventory_item_update_schema_rejects_negative_cost() -> None:
    """单位成本不能为负数（前端表单与后端校验保持一致）。"""
    with pytest.raises(ValidationError):
        InventoryItemUpdate(unit_cost=Decimal("-0.0001"))


def test_shift_avg_cost_moves_weighted_average() -> None:
    """单件成本调整后按 (数量×均价 + 差额) ÷ 数量 重算移动加权平均。"""
    # 3 件均价 12.5，其中一件成本调高 10 元 → (37.5 + 10) ÷ 3
    assert inventory._shift_avg_cost(
        Decimal("3.00"), Decimal("12.5000"), Decimal("10.00")
    ) == Decimal("15.8333")


def test_shift_avg_cost_never_negative() -> None:
    """成本下调导致均价为负时归零，避免库存金额出现负数。"""
    assert inventory._shift_avg_cost(
        Decimal("1.00"), Decimal("5.0000"), Decimal("-10.00")
    ) == inventory.ZERO_COST


def test_shift_avg_cost_keeps_avg_without_quantity() -> None:
    """库存行没有数量时均价无意义，保持原值而不是除以 0。"""
    assert inventory._shift_avg_cost(
        Decimal("0.00"), Decimal("8.0000"), Decimal("2.00")
    ) == Decimal("8.0000")


def test_calc_avg_cost_for_single_item_move() -> None:
    """单件移入目标库位时，目标行按该件成本重算均价。"""
    # 目标行 2 件均价 10，移入 1 件成本 16 → (20 + 16) ÷ 3
    assert inventory._calc_avg_cost(
        Decimal("2.00"), Decimal("10.0000"), Decimal("1.00"), Decimal("16.00")
    ) == Decimal("12.0000")


def test_ensure_item_movable_allows_in_stock() -> None:
    """在库实例可以调整仓库 / 库位。"""
    inventory._ensure_item_movable(_item())


def test_ensure_item_movable_rejects_other_status() -> None:
    """已出库 / 锁定 / 报废 / 盘亏的实例分别返回 2003 / 2004 / 2002。"""
    expected = {
        InventoryItemStatus.OUT: inventory.ITEM_ALREADY_OUT,
        InventoryItemStatus.LOCKED: inventory.ITEM_LOCKED,
        InventoryItemStatus.SCRAPPED: inventory.ITEM_NOT_IN_STOCK,
        InventoryItemStatus.LOST: inventory.ITEM_NOT_IN_STOCK,
    }

    for status, code in expected.items():
        with pytest.raises(BizException) as exc_info:
            inventory._ensure_item_movable(_item(status))
        assert exc_info.value.code == code


def test_clean_text_trims_and_converts_blank_to_none() -> None:
    """批次号 / 备注等文本去空格，空串按「清空」处理。"""
    assert inventory._clean_text("  B2026  ") == "B2026"
    assert inventory._clean_text("   ") is None
    assert inventory._clean_text(None) is None


# ---------------------------------------------------------------- 路由注册
def test_inventory_routes_registered() -> None:
    """库存查询接口均为 GET，库存件详情额外提供 PUT 编辑。"""
    paths = app.openapi()["paths"]

    read_only = {
        "/api/v1/inventory",
        "/api/v1/inventory/warning",
        "/api/v1/inventory-items",
        "/api/v1/inventory-items/{item_id}/transactions",
    }
    assert read_only <= set(paths)
    for path in read_only:
        assert set(paths[path]) == {"get"}

    assert set(paths["/api/v1/inventory-items/{item_id}"]) == {"get", "put"}
