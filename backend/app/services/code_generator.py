"""业务编码生成与取号。

编码规则（见 docs/database-design.md 第六节「二维码编码规则」）：

- 库存件编码 `item_code`：IT + yyyyMMdd + 6 位流水，例 IT20261022000001
- 入库单号 IN / 出库单号 OUT / 调拨单号 TR / 盘点单号 ST / 维修工单号 WO

取号策略：
- 不引入 Redis 或独立序列表，直接按对应业务表「当日最大编码 + 1」取号，
  与 `inbound_service._next_order_no` 的做法保持一致；
- 并发安全由唯一索引（`uk_item_code` / `uk_order_no`）兜底：并发事务可能
  取到相同流水号，冲突一方回滚后重新取号（审核入库内部带重试）；
- 同一事务内需要 N 个连续流水号时使用 `next_sequences` 一次取块，
  避免库内未提交数据尚未可见导致重复取号。
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InboundOrder,
    InventoryItem,
    OutboundOrder,
    StocktakeOrder,
    TransferOrder,
    WorkOrder,
)

__all__ = [
    "ITEM_CODE_SEQUENCE",
    "MAX_DAILY_SEQ",
    "SEQUENCE_SOURCES",
    "SequenceExhausted",
    "SequenceSource",
    "generate_code",
    "generate_inbound_no",
    "generate_item_code",
    "generate_outbound_no",
    "generate_stocktake_no",
    "generate_transfer_no",
    "generate_work_order_no",
    "next_sequence",
    "next_sequences",
]

# 各前缀（与文档一致）
ITEM_CODE_PREFIX = "IT"
INBOUND_NO_PREFIX = "IN"
OUTBOUND_NO_PREFIX = "OUT"
TRANSFER_NO_PREFIX = "TR"
STOCKTAKE_NO_PREFIX = "ST"
WORK_ORDER_NO_PREFIX = "WO"

# 流水号上限：6 位
MAX_DAILY_SEQ = 999999

# 取号业务标识（供 next_sequence / next_sequences 使用）
ITEM_CODE_SEQUENCE = "inventory_item"
INBOUND_SEQUENCE = "inbound_order"
OUTBOUND_SEQUENCE = "outbound_order"
TRANSFER_SEQUENCE = "transfer_order"
STOCKTAKE_SEQUENCE = "stocktake_order"
WORK_ORDER_SEQUENCE = "work_order"


class SequenceExhausted(RuntimeError):
    """当日流水号已用尽（超过 6 位）。"""


@dataclass(frozen=True)
class SequenceSource:
    """取号来源：业务表中承载编码的字段及其前缀。"""

    column: Any
    prefix: str
    label: str


# 业务表取号来源。新增单据类型时在此登记即可复用取号逻辑。
SEQUENCE_SOURCES: dict[str, SequenceSource] = {
    ITEM_CODE_SEQUENCE: SequenceSource(
        column=InventoryItem.item_code,
        prefix=ITEM_CODE_PREFIX,
        label="库存件编码",
    ),
    INBOUND_SEQUENCE: SequenceSource(
        column=InboundOrder.order_no,
        prefix=INBOUND_NO_PREFIX,
        label="入库单号",
    ),
    OUTBOUND_SEQUENCE: SequenceSource(
        column=OutboundOrder.order_no,
        prefix=OUTBOUND_NO_PREFIX,
        label="出库单号",
    ),
    TRANSFER_SEQUENCE: SequenceSource(
        column=TransferOrder.order_no,
        prefix=TRANSFER_NO_PREFIX,
        label="调拨单号",
    ),
    STOCKTAKE_SEQUENCE: SequenceSource(
        column=StocktakeOrder.order_no,
        prefix=STOCKTAKE_NO_PREFIX,
        label="盘点单号",
    ),
    WORK_ORDER_SEQUENCE: SequenceSource(
        column=WorkOrder.order_no,
        prefix=WORK_ORDER_NO_PREFIX,
        label="维修工单号",
    ),
}


def _date_stamp(at: datetime | date | None = None) -> str:
    """yyyyMMdd 日期段（默认取当前日期）。"""
    return (at or datetime.now()).strftime("%Y%m%d")


def generate_code(prefix: str, seq: int, at: datetime | date | None = None) -> str:
    """通用编码：前缀 + yyyyMMdd + 6 位流水。"""
    if seq < 1:
        raise ValueError("流水号必须从 1 开始")
    if seq > MAX_DAILY_SEQ:
        raise SequenceExhausted(f"{prefix} 当日流水号已用尽（上限 {MAX_DAILY_SEQ}）")
    return f"{prefix}{_date_stamp(at)}{seq:06d}"


def generate_item_code(seq: int, at: datetime | date | None = None) -> str:
    """库存件编码：IT + yyyyMMdd + 6 位流水。"""
    return generate_code(ITEM_CODE_PREFIX, seq, at)


def generate_inbound_no(seq: int, at: datetime | date | None = None) -> str:
    """入库单号：IN + yyyyMMdd + 6 位流水。"""
    return generate_code(INBOUND_NO_PREFIX, seq, at)


def generate_outbound_no(seq: int, at: datetime | date | None = None) -> str:
    """出库单号：OUT + yyyyMMdd + 6 位流水。"""
    return generate_code(OUTBOUND_NO_PREFIX, seq, at)


def generate_transfer_no(seq: int, at: datetime | date | None = None) -> str:
    """调拨单号：TR + yyyyMMdd + 6 位流水。"""
    return generate_code(TRANSFER_NO_PREFIX, seq, at)


def generate_stocktake_no(seq: int, at: datetime | date | None = None) -> str:
    """盘点单号：ST + yyyyMMdd + 6 位流水。"""
    return generate_code(STOCKTAKE_NO_PREFIX, seq, at)


def generate_work_order_no(seq: int, at: datetime | date | None = None) -> str:
    """维修工单号：WO + yyyyMMdd + 6 位流水。"""
    return generate_code(WORK_ORDER_NO_PREFIX, seq, at)


def _get_source(biz_type: str) -> SequenceSource:
    """取业务取号配置，未登记时抛 ValueError。"""
    source = SEQUENCE_SOURCES.get(biz_type)
    if source is None:
        raise ValueError(
            f"未登记的取号业务类型: {biz_type}，可选 {sorted(SEQUENCE_SOURCES)}"
        )
    return source


async def next_sequence(
    db: AsyncSession,
    biz_type: str,
    *,
    at: datetime | date | None = None,
) -> int:
    """返回下一个可用流水号（从 1 开始）。

    取当日（`yyyyMMdd` 前缀）最大编码的流水段 + 1；查询包含已作废/逻辑删除的
    数据，避免复用历史编码。并发事务可能拿到相同流水号，由唯一索引兜底。
    """
    source = _get_source(biz_type)
    prefix = f"{source.prefix}{_date_stamp(at)}"

    max_code = (
        await db.execute(
            select(func.max(source.column)).where(source.column.like(f"{prefix}%"))
        )
    ).scalar_one_or_none()

    seq = 1
    if max_code:
        tail = str(max_code)[len(prefix) :]
        if tail.isdigit():
            seq = int(tail) + 1
    if seq > MAX_DAILY_SEQ:
        raise SequenceExhausted(
            f"{source.label}当日流水号已用尽（上限 {MAX_DAILY_SEQ}）"
        )
    return seq


async def next_sequences(
    db: AsyncSession,
    biz_type: str,
    count: int,
    *,
    at: datetime | date | None = None,
) -> list[int]:
    """一次申请 `count` 个连续流水号（同一事务内批量生成编码时使用）。"""
    if count < 1:
        raise ValueError("申请数量必须大于 0")

    start = await next_sequence(db, biz_type, at=at)
    end = start + count - 1
    if end > MAX_DAILY_SEQ:
        source = _get_source(biz_type)
        raise SequenceExhausted(
            f"{source.label}当日流水号不足：需要 {count} 个，最大仅到 {MAX_DAILY_SEQ}"
        )
    return list(range(start, end + 1))
