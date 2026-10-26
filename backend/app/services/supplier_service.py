"""供应商业务逻辑：分页查询、增删改查。

约定：
- 查询统一过滤 `is_deleted == 0`，删除一律逻辑删除（`is_deleted = 1`）；
- `created_by` / `updated_by` 由路由层通过 `CurrentUserId` 注入，不接受前端提交；
- `supplier.name` 表无唯一索引，名称不允许重复由应用层保证（仅比较未删除数据，
  删除后可复用名称）；
- 已产生入库单的供应商禁止删除（409），避免历史单据悬空。
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import InboundOrder, Supplier
from app.schemas.common import PageResult
from app.schemas.supplier import (
    SupplierCreate,
    SupplierQuery,
    SupplierUpdate,
    SupplierVO,
)

__all__ = [
    "create_supplier",
    "delete_supplier",
    "get_supplier",
    "list_suppliers",
    "update_supplier",
]


# ---------------------------------------------------------------- 内部工具
def _reject_null(data: dict[str, Any], labels: dict[str, str]) -> None:
    """编辑时显式提交 null 视为参数错误，避免覆盖非空列后抛 500。"""
    for field, label in labels.items():
        if field in data and data[field] is None:
            raise BizException(code=400, message=f"{label}不能为空")


async def _exists(db: AsyncSession, stmt: Select[Any]) -> bool:
    """判断查询是否存在记录。"""
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def _get_supplier_or_404(db: AsyncSession, supplier_id: int) -> Supplier:
    """按 ID 取供应商，不存在或已删除抛 404。"""
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None or supplier.is_deleted:
        raise BizException(code=404, message="供应商不存在")
    return supplier


async def _ensure_name_available(
    db: AsyncSession,
    name: str,
    exclude_id: int | None = None,
) -> None:
    """供应商名称不允许重复（仅比较未删除数据，删除后可复用）。"""
    conditions = [Supplier.name == name, Supplier.is_deleted == 0]
    if exclude_id is not None:
        conditions.append(Supplier.id != exclude_id)
    if await _exists(db, select(Supplier.id).where(*conditions)):
        raise BizException(code=409, message="供应商名称已存在")


# ---------------------------------------------------------------- 查询
async def list_suppliers(
    db: AsyncSession,
    query: SupplierQuery,
) -> PageResult[SupplierVO]:
    """供应商分页查询，支持名称/联系人/电话关键字、主营品类、状态筛选。"""
    conditions = [Supplier.is_deleted == 0]
    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                Supplier.name.like(keyword),
                Supplier.contact.like(keyword),
                Supplier.phone.like(keyword),
            )
        )
    if query.main_category:
        conditions.append(Supplier.main_category == query.main_category)
    if query.status is not None:
        conditions.append(Supplier.status == query.status)

    total = (
        await db.execute(select(func.count()).select_from(Supplier).where(*conditions))
    ).scalar_one()

    stmt = (
        select(Supplier)
        .where(*conditions)
        .order_by(Supplier.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[SupplierVO](
        list=[SupplierVO.model_validate(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_supplier(db: AsyncSession, supplier_id: int) -> SupplierVO:
    """供应商详情。"""
    return SupplierVO.model_validate(await _get_supplier_or_404(db, supplier_id))


# ---------------------------------------------------------------- 写入
async def create_supplier(
    db: AsyncSession,
    payload: SupplierCreate,
    current_user_id: int,
) -> SupplierVO:
    """新增供应商，`created_by` 取当前登录用户。"""
    await _ensure_name_available(db, payload.name)

    supplier = Supplier(
        **payload.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return SupplierVO.model_validate(supplier)


async def update_supplier(
    db: AsyncSession,
    supplier_id: int,
    payload: SupplierUpdate,
    current_user_id: int,
) -> SupplierVO:
    """编辑供应商（仅更新传入字段），`updated_by` 取当前登录用户。"""
    supplier = await _get_supplier_or_404(db, supplier_id)
    data = payload.model_dump(exclude_unset=True)
    _reject_null(data, {"name": "供应商名称", "status": "状态"})

    new_name = data.get("name")
    if new_name and new_name != supplier.name:
        await _ensure_name_available(db, new_name, exclude_id=supplier.id)

    for field, value in data.items():
        setattr(supplier, field, value)
    supplier.updated_by = current_user_id
    await db.commit()
    await db.refresh(supplier)
    return SupplierVO.model_validate(supplier)


async def delete_supplier(
    db: AsyncSession,
    supplier_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除供应商；已产生入库单时拒绝删除。"""
    supplier = await _get_supplier_or_404(db, supplier_id)

    if await _exists(
        db,
        select(InboundOrder.id).where(
            InboundOrder.supplier_id == supplier.id,
            InboundOrder.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该供应商已存在入库单，无法删除")

    supplier.is_deleted = 1
    supplier.updated_by = current_user_id
    await db.commit()
