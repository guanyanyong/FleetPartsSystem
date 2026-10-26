"""库存件业务逻辑：扫码识别（qrcode / item_code）与状态校验。

约定：
- 扫码内容支持可选的 `QR:` 前缀（大小写不敏感），并自动去掉首尾空白；
- 入库时二维码内容即 `item_code`，因此先按 `qrcode` 精确匹配，
  未命中再按 `item_code` 匹配，两条唯一索引都能作为扫码入口；
- 只有「在库」的库存件可以出库，其余状态按
  docs/backend-requirements.md 错误码约定返回：
    2003 已出库 / 2004 已锁定 / 2002 已报废或已盘亏 / 4001 无法识别；
- 成功时返回 `ScanResultVO`（配件、仓库、库位、成本、状态文案），
  前端（出库、盘点扫码）可直接把返回结果追加为单据明细。
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import InventoryItem, Part, Warehouse, WarehouseLocation
from app.models.enums import INVENTORY_ITEM_STATUS_TEXT, InventoryItemStatus
from app.schemas.inventory_item import ScanResultVO

__all__ = [
    "ITEM_ALREADY_OUT",
    "ITEM_LOCKED",
    "ITEM_NOT_IN_STOCK",
    "SCAN_CODE_PREFIX",
    "SCAN_CODE_UNRECOGNIZED",
    "normalize_scan_code",
    "scan_inventory_item",
]

# 业务错误码（见 docs/backend-requirements.md 错误码约定）
SCAN_CODE_UNRECOGNIZED: int = 4001
ITEM_NOT_IN_STOCK: int = 2002
ITEM_ALREADY_OUT: int = 2003
ITEM_LOCKED: int = 2004

# 扫码内容前缀：二维码/扫码枪可能带业务前缀，如 "QR:IT20261022000001"
SCAN_CODE_PREFIX: str = "QR:"


# ---------------------------------------------------------------- 内部工具
def normalize_scan_code(code: str) -> str:
    """去掉首尾空白与可选的 `QR:` 前缀，返回用于匹配的编码。"""
    normalized = (code or "").strip()
    if normalized[: len(SCAN_CODE_PREFIX)].upper() == SCAN_CODE_PREFIX:
        normalized = normalized[len(SCAN_CODE_PREFIX) :].strip()
    return normalized


class _ScanRow(NamedTuple):
    """扫码查询结果：库存件 + 关联配件 / 仓库 / 库位（关联数据可能为空）。"""

    item: InventoryItem
    part: Part | None
    warehouse: Warehouse | None
    location: WarehouseLocation | None


async def _load_scan_row(db: AsyncSession, code: str) -> _ScanRow | None:
    """按 qrcode / item_code 取库存件，并一次性带出配件、仓库、库位。"""
    stmt = (
        select(InventoryItem, Part, Warehouse, WarehouseLocation)
        .outerjoin(Part, Part.id == InventoryItem.part_id)
        .outerjoin(Warehouse, Warehouse.id == InventoryItem.warehouse_id)
        .outerjoin(
            WarehouseLocation,
            WarehouseLocation.id == InventoryItem.location_id,
        )
        .where(
            InventoryItem.is_deleted == 0,
            or_(
                InventoryItem.qrcode == code,
                InventoryItem.item_code == code,
            ),
        )
        # qrcode 精确命中优先于 item_code 命中
        .order_by(case((InventoryItem.qrcode == code, 0), else_=1))
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return _ScanRow(
        item=row[0],
        part=row[1],
        warehouse=row[2],
        location=row[3],
    )


def _ensure_scannable(item: InventoryItem) -> None:
    """校验库存件状态，不允许出库时抛对应业务错误码。"""
    if item.status == InventoryItemStatus.OUT:
        raise BizException(code=ITEM_ALREADY_OUT, message="该件已出库，不能重复出库")
    if item.status == InventoryItemStatus.LOCKED:
        raise BizException(code=ITEM_LOCKED, message="该件已被锁定，不能出库")
    if item.status == InventoryItemStatus.SCRAPPED:
        raise BizException(code=ITEM_NOT_IN_STOCK, message="该件已报废，不能出库")
    if item.status == InventoryItemStatus.LOST:
        raise BizException(code=ITEM_NOT_IN_STOCK, message="该件已盘亏，不能出库")
    if item.status != InventoryItemStatus.IN_STOCK:
        status_text = INVENTORY_ITEM_STATUS_TEXT.get(item.status, "未知")
        raise BizException(
            code=ITEM_NOT_IN_STOCK,
            message=f"该件状态为「{status_text}」，不能出库",
        )


def _to_scan_result_vo(
    item: InventoryItem,
    part: Part | None,
    warehouse: Warehouse | None,
    location: WarehouseLocation | None,
) -> ScanResultVO:
    """聚合库存件、配件、仓库、库位信息为扫码结果。"""
    return ScanResultVO(
        item_id=item.id,
        item_code=item.item_code,
        qrcode=item.qrcode,
        part_id=item.part_id,
        part_code=part.part_code if part is not None else None,
        part_name=part.part_name if part is not None else None,
        spec=part.spec if part is not None else None,
        unit=part.unit if part is not None else None,
        batch_no=item.batch_no,
        status=item.status,
        status_text=INVENTORY_ITEM_STATUS_TEXT.get(item.status, "未知"),
        warehouse_id=item.warehouse_id,
        warehouse_name=warehouse.name if warehouse is not None else None,
        location_id=item.location_id,
        location_code=location.location_code if location is not None else None,
        unit_cost=item.unit_cost if item.unit_cost is not None else Decimal(0),
        in_at=item.in_at,
    )


# ---------------------------------------------------------------- 扫码
async def scan_inventory_item(db: AsyncSession, code: str) -> ScanResultVO:
    """扫码查询库存件。

    - `code` 支持 `QR:` 前缀与首尾空白，按 `qrcode` 或 `item_code` 匹配；
    - 不存在（含已逻辑删除）返回 4001「扫码内容无法识别」；
    - 已出库 2003 / 已锁定 2004 / 已报废或已盘亏 2002；
    - 在库返回完整聚合信息，供前端直接追加出库/盘点明细。
    """
    normalized = normalize_scan_code(code)
    if not normalized:
        raise BizException(code=SCAN_CODE_UNRECOGNIZED, message="扫码内容无法识别")

    row = await _load_scan_row(db, normalized)
    if row is None:
        raise BizException(code=SCAN_CODE_UNRECOGNIZED, message="扫码内容无法识别")

    item, part, warehouse, location = row.item, row.part, row.warehouse, row.location
    _ensure_scannable(item)
    return _to_scan_result_vo(item, part, warehouse, location)
