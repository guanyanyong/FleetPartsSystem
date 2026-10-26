"""报表与首页看板模块的单元测试（不依赖数据库，可直接运行 `pytest`）。

覆盖范围：
- 库存报表 VO 转换与库存金额计算；
- 库存报表 / 流水报表查询条件拼装（含低库存、排除零库存、时间范围）；
- 分页 + 合计响应模型的 camelCase 序列化；
- 库存报表 Excel 导出（表头、数据、汇总页、低库存标记）；
- 本月统计区间计算；
- 5 个报表接口路由注册。

完整的多表聚合查询已通过 MySQL 冒烟验证，不在单元测试中重复依赖数据库。
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from app.main import app
from app.models import Inventory, Part
from app.models.enums import BizType
from app.schemas.report import (
    InventoryReportQuery,
    InventoryReportResult,
    InventoryReportSummaryVO,
    InventoryReportVO,
    TransactionReportQuery,
)
from app.services import report_service as report

NOW = datetime(2026, 10, 23, 10, 0, 0)


# ---------------------------------------------------------------- 构造内存对象
def _part() -> Part:
    """构造配件主数据（仅内存对象，不落库）。"""
    return Part(
        id=1,
        part_code="P001",
        part_name="机油滤清器",
        spec="4L",
        unit="个",
        category_id=2,
        safety_stock=Decimal("5.00"),
        max_stock=Decimal("50.00"),
        is_deleted=0,
        created_at=NOW,
    )


def _inventory() -> Inventory:
    """构造库存汇总行：3 个在库，锁定 1 个，平均成本 12.50。"""
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


def _report_vo() -> InventoryReportVO:
    """构造库存报表导出所需的 VO。"""
    return InventoryReportVO(
        part_id=1,
        part_code="P001",
        part_name="机油滤清器",
        spec="4L",
        unit="个",
        category_id=2,
        category_name="滤清器",
        warehouse_id=2,
        warehouse_name="主仓库",
        location_id=3,
        location_code="A-01",
        quantity=Decimal("3.00"),
        item_count=2,
        locked_qty=Decimal("1.00"),
        avg_cost=Decimal("12.5000"),
        amount=Decimal("37.50"),
        safety_stock=Decimal("5.00"),
        max_stock=Decimal("50.00"),
    )


# ---------------------------------------------------------------- VO 与响应模型
def test_to_inventory_report_vo_calculates_amount() -> None:
    """库存报表行需要补齐分类、仓库、库位，并按数量 × 平均成本算金额。"""
    vo = report._to_inventory_report_vo(
        _inventory(),
        _part(),
        "滤清器",
        "主仓库",
        "A-01",
    )

    assert vo.part_code == "P001"
    assert vo.category_name == "滤清器"
    assert vo.warehouse_name == "主仓库"
    assert vo.location_code == "A-01"
    assert vo.amount == Decimal("37.50")
    assert report._is_low_stock(vo) is True


def test_is_low_stock_requires_positive_safety_stock() -> None:
    """安全库存为 0 / 未维护时不算低库存，与列表合计口径一致。"""
    vo = _report_vo().model_copy(
        update={"quantity": Decimal("0.00"), "safety_stock": Decimal("0.00")}
    )

    assert report._is_low_stock(vo) is False


def test_inventory_report_result_serializes_summary_as_camel_case() -> None:
    """分页结果需要同时输出 list、分页字段与 summary，且使用 camelCase。"""
    result = InventoryReportResult(
        list=[_report_vo()],
        total=1,
        page=2,
        page_size=10,
        summary=InventoryReportSummaryVO(
            part_kinds=1,
            total_quantity=Decimal("3.00"),
            total_amount=Decimal("37.50"),
            low_stock_count=1,
        ),
    )

    data = result.model_dump(by_alias=True)

    assert data["pageSize"] == 10
    assert len(data["list"]) == 1
    assert data["summary"]["partKinds"] == 1
    assert data["summary"]["lowStockCount"] == 1


# ---------------------------------------------------------------- 查询条件
def test_inventory_report_conditions() -> None:
    """默认排除零库存；关键字、分类、仓库、库位条件均需拼入。"""
    conditions = report._inventory_conditions(
        InventoryReportQuery(
            keyword=" 机油 ",
            category_id=2,
            warehouse_id=3,
            location_id=4,
        )
    )
    sql = " AND ".join(str(condition) for condition in conditions).lower()

    assert "inventory.quantity >" in sql
    assert "part.part_code like" in sql
    assert "part.category_id =" in sql
    assert "inventory.warehouse_id =" in sql
    assert "inventory.location_id =" in sql
    assert "part.safety_stock" not in sql


def test_inventory_report_low_stock_conditions_include_zero() -> None:
    """低库存筛选按可用数量比较；include_zero=true 时不再排除零库存。"""
    conditions = report._inventory_conditions(
        InventoryReportQuery(low_stock=True, include_zero=True)
    )
    sql = " AND ".join(str(condition) for condition in conditions).lower()

    assert "inventory.quantity >" not in sql
    assert "part.safety_stock is not null" in sql
    assert "part.safety_stock >" in sql
    assert "inventory.quantity - inventory.locked_qty < part.safety_stock" in sql


def test_transaction_report_conditions() -> None:
    """流水报表条件覆盖关键字、业务类型、关联单号与时间范围。"""
    conditions = report._transaction_conditions(
        TransactionReportQuery(
            keyword=" 机油 ",
            biz_type=BizType.IN,
            ref_no=" RK ",
            start_time=NOW,
            end_time=NOW,
        )
    )
    sql = " AND ".join(str(condition) for condition in conditions).lower()

    assert "part.part_code like" in sql
    assert "part.part_name like" in sql
    assert "inventory_transaction.ref_no like" in sql
    assert "inventory_transaction.biz_type =" in sql
    assert "inventory_transaction.created_at >=" in sql
    assert "inventory_transaction.created_at <=" in sql


def test_month_bounds_crosses_year() -> None:
    """12 月的本月区间应跨到下一年 1 月 1 日。"""
    start, next_start = report._month_bounds(datetime(2026, 12, 15, 9, 30))

    assert start == datetime(2026, 12, 1)
    assert next_start == datetime(2027, 1, 1)


# ---------------------------------------------------------------- Excel 导出
def test_build_inventory_report_workbook() -> None:
    """导出文件需包含明细表头、数据行、低库存状态与汇总页。"""
    content = report.build_inventory_report_workbook([_report_vo()])

    assert content.startswith(b"PK")

    workbook = load_workbook(BytesIO(content))
    sheet = workbook["库存报表"]
    assert sheet["A1"].value == "配件编码"
    assert sheet["A2"].value == "P001"
    assert sheet["B2"].value == "机油滤清器"
    assert sheet["N2"].value == "低库存"

    summary_sheet = workbook["汇总"]
    assert summary_sheet["A2"].value == "配件种类"
    assert summary_sheet["B2"].value == 1
    assert float(summary_sheet["B3"].value) == 3.0
    assert float(summary_sheet["B4"].value) == 37.5
    assert summary_sheet["B5"].value == 1


# ---------------------------------------------------------------- 路由注册
def test_report_routes_registered() -> None:
    """5 个报表接口需全部注册且均为 GET。"""
    paths = app.openapi()["paths"]

    expected = {
        "/api/v1/reports/dashboard",
        "/api/v1/reports/inventory",
        "/api/v1/reports/inventory/export",
        "/api/v1/reports/transaction",
        "/api/v1/reports/vehicle-cost",
    }
    assert expected <= set(paths)
    for path in expected:
        assert set(paths[path]) == {"get"}

