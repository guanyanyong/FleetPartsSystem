"""库存流水表 inventory_transaction（只读）。"""

from decimal import Decimal

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import ReadOnlyMixin


class InventoryTransaction(Base, ReadOnlyMixin):
    """库存变动流水，只追加不修改。"""

    __tablename__ = "inventory_transaction"
    __table_args__ = (
        Index("idx_part_warehouse_time", "part_id", "warehouse_id", "created_at"),
        Index("idx_ref", "ref_type", "ref_id"),
        Index("idx_item", "inventory_item_id"),
        {"comment": "库存流水表"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键"
    )
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="配件ID")
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="库存件实例ID"
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="仓库ID"
    )
    location_id: Mapped[int | None] = mapped_column(BigInteger, comment="库位ID")
    biz_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="IN/OUT/TRANSFER_IN/TRANSFER_OUT/ADJUST_IN/ADJUST_OUT",
    )
    change_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="变动数量"
    )
    before_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="变动前数量"
    )
    after_qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="变动后数量"
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), comment="单位成本"
    )
    ref_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="INBOUND/OUTBOUND/TRANSFER/STOCKTAKE"
    )
    ref_id: Mapped[int | None] = mapped_column(BigInteger, comment="关联单据ID")
    ref_no: Mapped[str | None] = mapped_column(String(50), comment="关联单号")
    batch_no: Mapped[str | None] = mapped_column(String(50), comment="批次号")
    scan_code: Mapped[str | None] = mapped_column(String(100), comment="扫码原始编码")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="操作人ID")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
