"""配件业务逻辑：分类树、配件增删改查、车型适配、单位换算。

约定：
- 查询统一过滤 `is_deleted == 0`，删除一律逻辑删除（`is_deleted = 1`）。
- `created_by` / `updated_by` 由路由层通过 `CurrentUserId` 注入，不接受前端提交。
- `part.part_code` 唯一：重复时抛业务码 1001；校验包含已逻辑删除数据，
  与 `uk_part_code` 唯一索引保持一致（删除后编码仍被占用，避免索引冲突）。
"""

from decimal import Decimal

from sqlalchemy import ScalarSelect, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import (
    Inventory,
    Part,
    PartCategory,
    PartUnitConversion,
    PartVehicleModel,
    VehicleModel,
)
from app.schemas.common import PageResult
from app.schemas.part import (
    PartCategoryCreate,
    PartCategoryTreeVO,
    PartCategoryUpdate,
    PartCategoryVO,
    PartCreate,
    PartQuery,
    PartUnitConversionAdd,
    PartUnitConversionVO,
    PartUpdate,
    PartVehicleModelAdd,
    PartVehicleModelDetailVO,
    PartVO,
)

__all__ = [
    "PART_CODE_DUPLICATED",
    "add_part_model",
    "create_category",
    "create_part",
    "create_unit_conversion",
    "delete_category",
    "delete_part",
    "delete_part_model",
    "delete_unit_conversion",
    "get_category",
    "get_part",
    "list_category_tree",
    "list_part_models",
    "list_parts",
    "list_unit_conversions",
    "update_category",
    "update_part",
]

# 业务错误码：配件编码重复（见 docs/backend-requirements.md 错误码约定）
PART_CODE_DUPLICATED: int = 1001


# ---------------------------------------------------------------- 内部工具
async def _get_part_or_404(db: AsyncSession, part_id: int) -> Part:
    """按 ID 取配件，不存在或已删除抛 404。"""
    part = await db.get(Part, part_id)
    if part is None or part.is_deleted:
        raise BizException(code=404, message="配件不存在")
    return part


async def _get_category_or_404(db: AsyncSession, category_id: int) -> PartCategory:
    """按 ID 取配件分类，不存在或已删除抛 404。"""
    category = await db.get(PartCategory, category_id)
    if category is None or category.is_deleted:
        raise BizException(code=404, message="配件分类不存在")
    return category


async def _ensure_part_code_available(
    db: AsyncSession,
    part_code: str,
    exclude_id: int | None = None,
) -> None:
    """配件编码唯一性校验（包含已逻辑删除数据，与唯一索引一致）。"""
    stmt = select(Part.id).where(Part.part_code == part_code)
    if exclude_id is not None:
        stmt = stmt.where(Part.id != exclude_id)
    if (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None:
        raise BizException(code=PART_CODE_DUPLICATED, message="配件编码已存在")


async def _ensure_category_exists(db: AsyncSession, category_id: int | None) -> None:
    """校验分类存在（category_id 为空表示未指定分类）。"""
    if category_id is not None:
        await _get_category_or_404(db, category_id)


async def _ensure_category_name_available(
    db: AsyncSession,
    name: str,
    parent_id: int | None,
    exclude_id: int | None = None,
) -> None:
    """同一父分类下分类名不允许重复（表无唯一索引，应用层保证）。"""
    conditions = [PartCategory.name == name, PartCategory.is_deleted == 0]
    if parent_id is None:
        conditions.append(PartCategory.parent_id.is_(None))
    else:
        conditions.append(PartCategory.parent_id == parent_id)
    if exclude_id is not None:
        conditions.append(PartCategory.id != exclude_id)
    if (
        await db.execute(select(PartCategory.id).where(*conditions).limit(1))
    ).scalar_one_or_none() is not None:
        raise BizException(code=409, message="同级分类下已存在同名分类")


async def _ensure_parent_valid(
    db: AsyncSession,
    category_id: int | None,
    parent_id: int | None,
) -> None:
    """校验父分类：存在、非自身、且不能形成环（父分类不能是自己的子孙）。"""
    if parent_id is None:
        return
    if category_id is not None and parent_id == category_id:
        raise BizException(code=409, message="父分类不能是自身")

    cursor: PartCategory | None = await _get_category_or_404(db, parent_id)
    visited: set[int] = set()
    while cursor is not None and cursor.id not in visited:
        if category_id is not None and cursor.id == category_id:
            raise BizException(code=409, message="父分类不能是自己的子分类")
        visited.add(cursor.id)
        cursor = (
            await db.get(PartCategory, cursor.parent_id) if cursor.parent_id else None
        )


# ---------------------------------------------------------------- 配件分类
async def list_category_tree(
    db: AsyncSession,
    status: int | None = None,
) -> list[PartCategoryTreeVO]:
    """分类树，children 递归嵌套，按 sort、id 升序。

    父分类被过滤掉（停用/删除）时，其子分类上浮为根节点，避免数据丢失。
    """
    conditions = [PartCategory.is_deleted == 0]
    if status is not None:
        conditions.append(PartCategory.status == status)

    stmt = (
        select(PartCategory)
        .where(*conditions)
        .order_by(PartCategory.sort.asc(), PartCategory.id.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    nodes: dict[int, PartCategoryTreeVO] = {
        row.id: PartCategoryTreeVO.model_validate(row) for row in rows
    }
    roots: list[PartCategoryTreeVO] = []
    for row in rows:
        node = nodes[row.id]
        parent = nodes.get(row.parent_id) if row.parent_id is not None else None
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
    return roots


async def get_category(db: AsyncSession, category_id: int) -> PartCategoryVO:
    """分类详情。"""
    return PartCategoryVO.model_validate(await _get_category_or_404(db, category_id))


async def create_category(
    db: AsyncSession,
    payload: PartCategoryCreate,
    current_user_id: int,
) -> PartCategoryVO:
    """新增分类，`created_by` 取当前登录用户。"""
    await _ensure_parent_valid(db, None, payload.parent_id)
    await _ensure_category_name_available(db, payload.name, payload.parent_id)

    category = PartCategory(**payload.model_dump(), created_by=current_user_id)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return PartCategoryVO.model_validate(category)


async def update_category(
    db: AsyncSession,
    category_id: int,
    payload: PartCategoryUpdate,
    current_user_id: int,
) -> PartCategoryVO:
    """编辑分类（仅更新传入字段），`updated_by` 取当前登录用户。"""
    category = await _get_category_or_404(db, category_id)
    data = payload.model_dump(exclude_unset=True)

    new_parent_id = data.get("parent_id", category.parent_id)
    new_name = data.get("name", category.name)
    if "parent_id" in data:
        await _ensure_parent_valid(db, category.id, new_parent_id)
    if "name" in data or "parent_id" in data:
        await _ensure_category_name_available(
            db, new_name, new_parent_id, exclude_id=category.id
        )

    for field, value in data.items():
        setattr(category, field, value)
    category.updated_by = current_user_id
    await db.commit()
    await db.refresh(category)
    return PartCategoryVO.model_validate(category)


async def delete_category(
    db: AsyncSession,
    category_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除分类；存在子分类或已关联配件时拒绝删除。"""
    category = await _get_category_or_404(db, category_id)

    child_id = (
        await db.execute(
            select(PartCategory.id)
            .where(
                PartCategory.parent_id == category.id,
                PartCategory.is_deleted == 0,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if child_id is not None:
        raise BizException(code=409, message="该分类下存在子分类，无法删除")

    part_id = (
        await db.execute(
            select(Part.id)
            .where(Part.category_id == category.id, Part.is_deleted == 0)
            .limit(1)
        )
    ).scalar_one_or_none()
    if part_id is not None:
        raise BizException(code=409, message="该分类下存在配件，无法删除")

    category.is_deleted = 1
    category.updated_by = current_user_id
    await db.commit()


# ---------------------------------------------------------------- 配件
def _stock_quantity_expr() -> ScalarSelect[Decimal]:
    """当前库存合计（跨仓库/库位）标量子查询，供列表与详情扩展字段使用。"""
    return (
        select(func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.part_id == Part.id, Inventory.is_deleted == 0)
        .correlate(Part)
        .scalar_subquery()
    )


def _to_part_vo(
    part: Part,
    category_name: str | None = None,
    stock_quantity: Decimal | None = None,
) -> PartVO:
    """ORM 对象转 VO，并补充分类名称与库存合计。"""
    vo = PartVO.model_validate(part)
    vo.category_name = category_name
    vo.stock_quantity = Decimal(stock_quantity or 0)
    return vo


async def list_parts(db: AsyncSession, query: PartQuery) -> PageResult[PartVO]:
    """配件分页查询，支持编码/名称/规格关键字、分类、品牌、追踪方式、状态筛选。"""
    conditions = [Part.is_deleted == 0]
    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                Part.part_code.like(keyword),
                Part.part_name.like(keyword),
                Part.spec.like(keyword),
            )
        )
    if query.part_code:
        conditions.append(Part.part_code.like(f"%{query.part_code.strip()}%"))
    if query.category_id is not None:
        conditions.append(Part.category_id == query.category_id)
    if query.brand:
        conditions.append(Part.brand == query.brand)
    if query.is_general is not None:
        conditions.append(Part.is_general == query.is_general)
    if query.track_by_item is not None:
        conditions.append(Part.track_by_item == query.track_by_item)
    if query.scan_enabled is not None:
        conditions.append(Part.scan_enabled == query.scan_enabled)
    if query.status is not None:
        conditions.append(Part.status == query.status)

    total = (
        await db.execute(select(func.count()).select_from(Part).where(*conditions))
    ).scalar_one()

    stmt = (
        select(Part, PartCategory.name, _stock_quantity_expr())
        .outerjoin(PartCategory, PartCategory.id == Part.category_id)
        .where(*conditions)
        .order_by(Part.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    return PageResult[PartVO](
        list=[
            _to_part_vo(part, category_name, stock_quantity)
            for part, category_name, stock_quantity in rows
        ],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_part(db: AsyncSession, part_id: int) -> PartVO:
    """配件详情（含分类名称、库存合计）。"""
    stmt = (
        select(Part, PartCategory.name, _stock_quantity_expr())
        .outerjoin(PartCategory, PartCategory.id == Part.category_id)
        .where(Part.id == part_id, Part.is_deleted == 0)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="配件不存在")
    part, category_name, stock_quantity = row
    return _to_part_vo(part, category_name, stock_quantity)


async def create_part(
    db: AsyncSession,
    payload: PartCreate,
    current_user_id: int,
) -> PartVO:
    """新增配件；`part_code` 重复返回业务码 1001，`created_by` 取当前登录用户。"""
    await _ensure_part_code_available(db, payload.part_code)
    await _ensure_category_exists(db, payload.category_id)

    part = Part(**payload.model_dump(), created_by=current_user_id)
    db.add(part)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=PART_CODE_DUPLICATED, message="配件编码已存在") from exc
    return await get_part(db, part.id)


async def update_part(
    db: AsyncSession,
    part_id: int,
    payload: PartUpdate,
    current_user_id: int,
) -> PartVO:
    """编辑配件（仅更新传入字段）；改编码仍做唯一校验，`updated_by` 取当前登录用户。"""
    part = await _get_part_or_404(db, part_id)
    data = payload.model_dump(exclude_unset=True)

    new_part_code = data.get("part_code")
    if new_part_code and new_part_code != part.part_code:
        await _ensure_part_code_available(db, new_part_code, exclude_id=part.id)
    if "category_id" in data:
        await _ensure_category_exists(db, data["category_id"])

    for field, value in data.items():
        setattr(part, field, value)
    part.updated_by = current_user_id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=PART_CODE_DUPLICATED, message="配件编码已存在") from exc
    return await get_part(db, part.id)


async def delete_part(db: AsyncSession, part_id: int, current_user_id: int) -> None:
    """逻辑删除配件（is_deleted=1），适配关系与单位换算保留历史数据。"""
    part = await _get_part_or_404(db, part_id)
    part.is_deleted = 1
    part.updated_by = current_user_id
    await db.commit()


# ---------------------------------------------------------------- 适配车型
def _to_model_detail_vo(
    relation: PartVehicleModel,
    model: VehicleModel,
) -> PartVehicleModelDetailVO:
    """适配关系 + 车型基础信息。"""
    vo = PartVehicleModelDetailVO.model_validate(relation)
    vo.brand = model.brand
    vo.model_name = model.model_name
    vo.tonnage = model.tonnage
    vo.model_status = model.status
    return vo


async def list_part_models(
    db: AsyncSession,
    part_id: int,
) -> list[PartVehicleModelDetailVO]:
    """配件适配车型列表（含品牌/型号/吨位）。"""
    await _get_part_or_404(db, part_id)
    stmt = (
        select(PartVehicleModel, VehicleModel)
        .join(VehicleModel, VehicleModel.id == PartVehicleModel.model_id)
        .where(
            PartVehicleModel.part_id == part_id,
            PartVehicleModel.is_deleted == 0,
        )
        .order_by(PartVehicleModel.id.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [_to_model_detail_vo(relation, model) for relation, model in rows]


async def add_part_model(
    db: AsyncSession,
    part_id: int,
    payload: PartVehicleModelAdd,
    current_user_id: int,
) -> PartVehicleModelDetailVO:
    """添加适配车型；已适配返回 409，历史逻辑删除记录则恢复复用。"""
    await _get_part_or_404(db, part_id)

    model = await db.get(VehicleModel, payload.model_id)
    if model is None or model.is_deleted:
        raise BizException(code=404, message="车型不存在")

    relation = (
        await db.execute(
            select(PartVehicleModel)
            .where(
                PartVehicleModel.part_id == part_id,
                PartVehicleModel.model_id == payload.model_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if relation is not None:
        if not relation.is_deleted:
            raise BizException(code=409, message="该车型已适配")
        # uk_part_model 唯一索引仍占用该组合，恢复历史记录而非新增
        relation.is_deleted = 0
        relation.remark = payload.remark
        relation.updated_by = current_user_id
    else:
        relation = PartVehicleModel(
            part_id=part_id,
            model_id=payload.model_id,
            remark=payload.remark,
            created_by=current_user_id,
        )
        db.add(relation)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="该车型已适配") from exc
    await db.refresh(relation)
    return _to_model_detail_vo(relation, model)


async def delete_part_model(
    db: AsyncSession,
    part_id: int,
    model_id: int,
    current_user_id: int,
) -> None:
    """移除适配车型（逻辑删除）；路径中的 modelId 为车型ID。"""
    await _get_part_or_404(db, part_id)
    relation = (
        await db.execute(
            select(PartVehicleModel)
            .where(
                PartVehicleModel.part_id == part_id,
                PartVehicleModel.model_id == model_id,
                PartVehicleModel.is_deleted == 0,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if relation is None:
        raise BizException(code=404, message="适配车型不存在")

    relation.is_deleted = 1
    relation.updated_by = current_user_id
    await db.commit()


# ---------------------------------------------------------------- 单位换算
async def list_unit_conversions(
    db: AsyncSession,
    part_id: int,
) -> list[PartUnitConversionVO]:
    """配件单位换算列表。"""
    await _get_part_or_404(db, part_id)
    stmt = (
        select(PartUnitConversion)
        .where(
            PartUnitConversion.part_id == part_id,
            PartUnitConversion.is_deleted == 0,
        )
        .order_by(PartUnitConversion.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [PartUnitConversionVO.model_validate(row) for row in rows]


async def create_unit_conversion(
    db: AsyncSession,
    part_id: int,
    payload: PartUnitConversionAdd,
    current_user_id: int,
) -> PartUnitConversionVO:
    """新增单位换算；源/目标单位相同或已存在相同换算时拒绝。"""
    await _get_part_or_404(db, part_id)
    if payload.from_unit == payload.to_unit:
        raise BizException(code=400, message="源单位与目标单位不能相同")

    exists_id = (
        await db.execute(
            select(PartUnitConversion.id)
            .where(
                PartUnitConversion.part_id == part_id,
                PartUnitConversion.from_unit == payload.from_unit,
                PartUnitConversion.to_unit == payload.to_unit,
                PartUnitConversion.is_deleted == 0,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if exists_id is not None:
        raise BizException(code=409, message="该单位换算已存在")

    conversion = PartUnitConversion(
        part_id=part_id,
        from_unit=payload.from_unit,
        to_unit=payload.to_unit,
        rate=payload.rate,
        created_by=current_user_id,
    )
    db.add(conversion)
    await db.commit()
    await db.refresh(conversion)
    return PartUnitConversionVO.model_validate(conversion)


async def delete_unit_conversion(
    db: AsyncSession,
    part_id: int,
    conversion_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除单位换算。"""
    await _get_part_or_404(db, part_id)
    conversion = await db.get(PartUnitConversion, conversion_id)
    if conversion is None or conversion.is_deleted or conversion.part_id != part_id:
        raise BizException(code=404, message="单位换算不存在")

    conversion.is_deleted = 1
    conversion.updated_by = current_user_id
    await db.commit()
