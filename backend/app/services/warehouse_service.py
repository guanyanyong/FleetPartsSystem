"""仓库与库位业务逻辑：分页查询、增删改查。

约定：
- 查询统一过滤 `is_deleted == 0`，删除一律逻辑删除（`is_deleted = 1`）；
- `created_by` / `updated_by` 由路由层通过 `CurrentUserId` 注入，不接受前端提交；
- 仓库名称表无唯一索引，重复校验由应用层保证（仅比较未删除数据）；
- 库位编码在仓库内唯一（`uk_warehouse_location`）：校验包含已逻辑删除数据，
  避免与唯一索引冲突；
- 仓库下存在库位 / 库存 / 库存件、库位存在库存时禁止删除（409）。
"""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import Inventory, InventoryItem, SysUser, Warehouse, WarehouseLocation
from app.schemas.common import PageResult
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseLocationCreate,
    WarehouseLocationQuery,
    WarehouseLocationUpdate,
    WarehouseLocationVO,
    WarehouseQuery,
    WarehouseUpdate,
    WarehouseVO,
)

__all__ = [
    "create_warehouse",
    "create_warehouse_location",
    "delete_warehouse",
    "delete_warehouse_location",
    "get_warehouse",
    "list_warehouse_locations",
    "list_warehouses",
    "update_warehouse",
    "update_warehouse_location",
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


async def _get_warehouse_or_404(db: AsyncSession, warehouse_id: int) -> Warehouse:
    """按 ID 取仓库，不存在或已删除抛 404。"""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.is_deleted:
        raise BizException(code=404, message="仓库不存在")
    return warehouse


async def _get_location_or_404(
    db: AsyncSession,
    location_id: int,
) -> WarehouseLocation:
    """按 ID 取库位，不存在或已删除抛 404。"""
    location = await db.get(WarehouseLocation, location_id)
    if location is None or location.is_deleted:
        raise BizException(code=404, message="库位不存在")
    return location


async def _ensure_keeper_exists(db: AsyncSession, keeper_id: int | None) -> None:
    """校验负责人用户存在（keeper_id 为空表示未指定）。"""
    if keeper_id is None:
        return
    user = await db.get(SysUser, keeper_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message="负责人不存在")


async def _ensure_name_available(
    db: AsyncSession,
    name: str,
    exclude_id: int | None = None,
) -> None:
    """仓库名不允许重复（仅比较未删除数据，删除后可复用）。"""
    conditions = [Warehouse.name == name, Warehouse.is_deleted == 0]
    if exclude_id is not None:
        conditions.append(Warehouse.id != exclude_id)
    if await _exists(db, select(Warehouse.id).where(*conditions)):
        raise BizException(code=409, message="仓库名已存在")


async def _ensure_location_code_available(
    db: AsyncSession,
    warehouse_id: int,
    location_code: str,
    exclude_id: int | None = None,
) -> None:
    """库位编码在仓库内唯一（包含已逻辑删除数据，与 uk_warehouse_location 一致）。"""
    conditions = [
        WarehouseLocation.warehouse_id == warehouse_id,
        WarehouseLocation.location_code == location_code,
    ]
    if exclude_id is not None:
        conditions.append(WarehouseLocation.id != exclude_id)
    if await _exists(db, select(WarehouseLocation.id).where(*conditions)):
        raise BizException(code=409, message="该仓库下库位编码已存在")


# ---------------------------------------------------------------- 仓库
async def list_warehouses(
    db: AsyncSession,
    query: WarehouseQuery,
) -> PageResult[WarehouseVO]:
    """仓库分页查询，支持仓库名关键字、负责人、状态筛选。"""
    conditions = [Warehouse.is_deleted == 0]
    if query.keyword:
        conditions.append(Warehouse.name.like(f"%{query.keyword.strip()}%"))
    if query.keeper_id is not None:
        conditions.append(Warehouse.keeper_id == query.keeper_id)
    if query.status is not None:
        conditions.append(Warehouse.status == query.status)

    total = (
        await db.execute(select(func.count()).select_from(Warehouse).where(*conditions))
    ).scalar_one()

    stmt = (
        select(Warehouse)
        .where(*conditions)
        .order_by(Warehouse.id.asc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[WarehouseVO](
        list=[WarehouseVO.model_validate(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_warehouse(db: AsyncSession, warehouse_id: int) -> WarehouseVO:
    """仓库详情。"""
    return WarehouseVO.model_validate(await _get_warehouse_or_404(db, warehouse_id))


async def create_warehouse(
    db: AsyncSession,
    payload: WarehouseCreate,
    current_user_id: int,
) -> WarehouseVO:
    """新增仓库，`created_by` 取当前登录用户。"""
    await _ensure_name_available(db, payload.name)
    await _ensure_keeper_exists(db, payload.keeper_id)

    warehouse = Warehouse(
        **payload.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseVO.model_validate(warehouse)


async def update_warehouse(
    db: AsyncSession,
    warehouse_id: int,
    payload: WarehouseUpdate,
    current_user_id: int,
) -> WarehouseVO:
    """编辑仓库（仅更新传入字段），`updated_by` 取当前登录用户。"""
    warehouse = await _get_warehouse_or_404(db, warehouse_id)
    data = payload.model_dump(exclude_unset=True)
    _reject_null(data, {"name": "仓库名", "status": "状态"})

    new_name = data.get("name")
    if new_name and new_name != warehouse.name:
        await _ensure_name_available(db, new_name, exclude_id=warehouse.id)
    if "keeper_id" in data:
        await _ensure_keeper_exists(db, data["keeper_id"])

    for field, value in data.items():
        setattr(warehouse, field, value)
    warehouse.updated_by = current_user_id
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseVO.model_validate(warehouse)


async def delete_warehouse(
    db: AsyncSession,
    warehouse_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除仓库；仍存在库位 / 库存 / 库存件时拒绝删除。"""
    warehouse = await _get_warehouse_or_404(db, warehouse_id)

    if await _exists(
        db,
        select(WarehouseLocation.id).where(
            WarehouseLocation.warehouse_id == warehouse.id,
            WarehouseLocation.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该仓库下存在库位，无法删除")

    if await _exists(
        db,
        select(Inventory.id).where(
            Inventory.warehouse_id == warehouse.id,
            Inventory.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该仓库存在库存记录，无法删除")

    if await _exists(
        db,
        select(InventoryItem.id).where(
            InventoryItem.warehouse_id == warehouse.id,
            InventoryItem.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该仓库存在库存件，无法删除")

    warehouse.is_deleted = 1
    warehouse.updated_by = current_user_id
    await db.commit()


# ---------------------------------------------------------------- 库位
async def list_warehouse_locations(
    db: AsyncSession,
    query: WarehouseLocationQuery,
) -> PageResult[WarehouseLocationVO]:
    """库位分页查询，支持按仓库、库位编码关键字、状态筛选。"""
    conditions = [WarehouseLocation.is_deleted == 0]
    if query.warehouse_id is not None:
        conditions.append(WarehouseLocation.warehouse_id == query.warehouse_id)
    if query.keyword:
        conditions.append(
            WarehouseLocation.location_code.like(f"%{query.keyword.strip()}%")
        )
    if query.status is not None:
        conditions.append(WarehouseLocation.status == query.status)

    total = (
        await db.execute(
            select(func.count()).select_from(WarehouseLocation).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(WarehouseLocation)
        .where(*conditions)
        .order_by(
            WarehouseLocation.warehouse_id.asc(),
            WarehouseLocation.location_code.asc(),
            WarehouseLocation.id.asc(),
        )
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[WarehouseLocationVO](
        list=[WarehouseLocationVO.model_validate(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def create_warehouse_location(
    db: AsyncSession,
    payload: WarehouseLocationCreate,
    current_user_id: int,
) -> WarehouseLocationVO:
    """新增库位；所属仓库需存在，仓库内库位编码唯一。"""
    await _get_warehouse_or_404(db, payload.warehouse_id)
    await _ensure_location_code_available(
        db, payload.warehouse_id, payload.location_code
    )

    location = WarehouseLocation(
        **payload.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(location)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="该仓库下库位编码已存在") from exc
    await db.refresh(location)
    return WarehouseLocationVO.model_validate(location)


async def update_warehouse_location(
    db: AsyncSession,
    location_id: int,
    payload: WarehouseLocationUpdate,
    current_user_id: int,
) -> WarehouseLocationVO:
    """编辑库位；调整所属仓库时按新仓库重新校验库位编码唯一性。"""
    location = await _get_location_or_404(db, location_id)
    data = payload.model_dump(exclude_unset=True)
    _reject_null(
        data,
        {"warehouse_id": "仓库", "location_code": "库位编码", "status": "状态"},
    )

    warehouse_id = data.get("warehouse_id", location.warehouse_id)
    if warehouse_id != location.warehouse_id:
        await _get_warehouse_or_404(db, warehouse_id)
    location_code = data.get("location_code", location.location_code)
    if warehouse_id != location.warehouse_id or location_code != location.location_code:
        await _ensure_location_code_available(
            db,
            warehouse_id,
            location_code,
            exclude_id=location.id,
        )

    for field, value in data.items():
        setattr(location, field, value)
    location.updated_by = current_user_id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="该仓库下库位编码已存在") from exc
    await db.refresh(location)
    return WarehouseLocationVO.model_validate(location)


async def delete_warehouse_location(
    db: AsyncSession,
    location_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除库位；该库位仍有库存或库存件时拒绝删除。"""
    location = await _get_location_or_404(db, location_id)

    if await _exists(
        db,
        select(Inventory.id).where(
            Inventory.location_id == location.id,
            Inventory.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该库位存在库存记录，无法删除")

    if await _exists(
        db,
        select(InventoryItem.id).where(
            InventoryItem.location_id == location.id,
            InventoryItem.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该库位存在库存件，无法删除")

    location.is_deleted = 1
    location.updated_by = current_user_id
    await db.commit()
