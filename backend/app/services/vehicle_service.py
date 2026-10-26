"""车型与车辆业务逻辑：分页查询、增删改查。

约定：
- 查询统一过滤 `is_deleted == 0`，删除一律逻辑删除（`is_deleted = 1`）；
- `created_by` / `updated_by` 由路由层通过 `CurrentUserId` 注入，不接受前端提交；
- `vehicle.plate_no` 唯一（`uk_plate_no`）：重复返回 409，校验时包含已逻辑删除数据，
  与唯一索引保持一致（删除后车牌号仍被占用）；
- 车型下存在车辆、或车辆已产生维修工单 / 出库单 / 装用配件时禁止删除（409），
  避免历史单据与报表出现悬空引用。
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import InventoryItem, OutboundOrder, Vehicle, VehicleModel, WorkOrder
from app.schemas.common import PageResult
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleModelCreate,
    VehicleModelQuery,
    VehicleModelUpdate,
    VehicleModelVO,
    VehicleQuery,
    VehicleUpdate,
    VehicleVO,
)

__all__ = [
    "create_vehicle",
    "create_vehicle_model",
    "delete_vehicle",
    "delete_vehicle_model",
    "get_vehicle",
    "list_vehicle_models",
    "list_vehicles",
    "update_vehicle",
    "update_vehicle_model",
]


# ---------------------------------------------------------------- 内部工具
def _reject_null(data: dict[str, Any], labels: dict[str, str]) -> None:
    """编辑时显式提交 null 视为参数错误，避免覆盖非空列后抛 500。"""
    for field, label in labels.items():
        if field in data and data[field] is None:
            raise BizException(code=400, message=f"{label}不能为空")


async def _exists(db: AsyncSession, stmt: Select[Any]) -> bool:
    """判断查询是否存在记录（统一 limit 1，避免全表扫描）。"""
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def _get_model_or_404(db: AsyncSession, model_id: int) -> VehicleModel:
    """按 ID 取车型，不存在或已删除抛 404。"""
    model = await db.get(VehicleModel, model_id)
    if model is None or model.is_deleted:
        raise BizException(code=404, message="车型不存在")
    return model


async def _get_vehicle_or_404(db: AsyncSession, vehicle_id: int) -> Vehicle:
    """按 ID 取车辆，不存在或已删除抛 404。"""
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.is_deleted:
        raise BizException(code=404, message="车辆不存在")
    return vehicle


async def _ensure_model_exists(db: AsyncSession, model_id: int | None) -> None:
    """校验车型存在（model_id 为空表示未指定车型）。"""
    if model_id is not None:
        await _get_model_or_404(db, model_id)


async def _ensure_model_name_available(
    db: AsyncSession,
    brand: str,
    model_name: str,
    exclude_id: int | None = None,
) -> None:
    """同一品牌下的车型名称不允许重复（表无唯一索引，应用层保证）。"""
    conditions = [
        VehicleModel.brand == brand,
        VehicleModel.model_name == model_name,
        VehicleModel.is_deleted == 0,
    ]
    if exclude_id is not None:
        conditions.append(VehicleModel.id != exclude_id)
    if await _exists(db, select(VehicleModel.id).where(*conditions)):
        raise BizException(code=409, message="该品牌下已存在同名车型")


async def _ensure_plate_no_available(
    db: AsyncSession,
    plate_no: str,
    exclude_id: int | None = None,
) -> None:
    """车牌号唯一性校验（包含已逻辑删除数据，与 uk_plate_no 一致）。"""
    conditions = [Vehicle.plate_no == plate_no]
    if exclude_id is not None:
        conditions.append(Vehicle.id != exclude_id)
    if await _exists(db, select(Vehicle.id).where(*conditions)):
        raise BizException(code=409, message="车牌号已存在")


# ---------------------------------------------------------------- 车型
async def list_vehicle_models(
    db: AsyncSession,
    query: VehicleModelQuery,
) -> PageResult[VehicleModelVO]:
    """车型分页查询，支持品牌/型号关键字、品牌、状态筛选。"""
    conditions = [VehicleModel.is_deleted == 0]
    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                VehicleModel.brand.like(keyword),
                VehicleModel.model_name.like(keyword),
            )
        )
    if query.brand:
        conditions.append(VehicleModel.brand == query.brand)
    if query.status is not None:
        conditions.append(VehicleModel.status == query.status)

    total = (
        await db.execute(
            select(func.count()).select_from(VehicleModel).where(*conditions)
        )
    ).scalar_one()

    stmt = (
        select(VehicleModel)
        .where(*conditions)
        .order_by(VehicleModel.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[VehicleModelVO](
        list=[VehicleModelVO.model_validate(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def create_vehicle_model(
    db: AsyncSession,
    payload: VehicleModelCreate,
    current_user_id: int,
) -> VehicleModelVO:
    """新增车型，`created_by` 取当前登录用户。"""
    await _ensure_model_name_available(db, payload.brand, payload.model_name)

    model = VehicleModel(**payload.model_dump(), created_by=current_user_id)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return VehicleModelVO.model_validate(model)


async def update_vehicle_model(
    db: AsyncSession,
    model_id: int,
    payload: VehicleModelUpdate,
    current_user_id: int,
) -> VehicleModelVO:
    """编辑车型（仅更新传入字段），`updated_by` 取当前登录用户。"""
    model = await _get_model_or_404(db, model_id)
    data = payload.model_dump(exclude_unset=True)
    _reject_null(data, {"brand": "品牌", "model_name": "型号", "status": "状态"})

    brand = data.get("brand", model.brand)
    model_name = data.get("model_name", model.model_name)
    if brand != model.brand or model_name != model.model_name:
        await _ensure_model_name_available(db, brand, model_name, exclude_id=model.id)

    for field, value in data.items():
        setattr(model, field, value)
    model.updated_by = current_user_id
    await db.commit()
    await db.refresh(model)
    return VehicleModelVO.model_validate(model)


async def delete_vehicle_model(
    db: AsyncSession,
    model_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除车型；仍有车辆引用时拒绝删除。"""
    model = await _get_model_or_404(db, model_id)

    if await _exists(
        db,
        select(Vehicle.id).where(
            Vehicle.model_id == model.id,
            Vehicle.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该车型下存在车辆，无法删除")

    model.is_deleted = 1
    model.updated_by = current_user_id
    await db.commit()


# ---------------------------------------------------------------- 车辆
def _to_vehicle_vo(
    vehicle: Vehicle,
    model: VehicleModel | None = None,
) -> VehicleVO:
    """车辆实体转 VO，并补充车型品牌 / 型号展示字段。"""
    vo = VehicleVO.model_validate(vehicle)
    if model is not None:
        vo.brand = model.brand
        vo.model_name = model.model_name
    return vo


async def list_vehicles(
    db: AsyncSession,
    query: VehicleQuery,
) -> PageResult[VehicleVO]:
    """车辆分页查询，支持车牌/车架号/发动机号关键字、车型、部门、状态筛选。"""
    conditions = [Vehicle.is_deleted == 0]
    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                Vehicle.plate_no.like(keyword),
                Vehicle.vin.like(keyword),
                Vehicle.engine_no.like(keyword),
            )
        )
    if query.model_id is not None:
        conditions.append(Vehicle.model_id == query.model_id)
    if query.department:
        conditions.append(Vehicle.department == query.department)
    if query.status is not None:
        conditions.append(Vehicle.status == query.status)

    total = (
        await db.execute(select(func.count()).select_from(Vehicle).where(*conditions))
    ).scalar_one()

    stmt = (
        select(Vehicle, VehicleModel)
        .outerjoin(VehicleModel, VehicleModel.id == Vehicle.model_id)
        .where(*conditions)
        .order_by(Vehicle.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    return PageResult[VehicleVO](
        list=[_to_vehicle_vo(vehicle, model) for vehicle, model in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_vehicle(db: AsyncSession, vehicle_id: int) -> VehicleVO:
    """车辆详情（含车型品牌 / 型号）。"""
    stmt = (
        select(Vehicle, VehicleModel)
        .outerjoin(VehicleModel, VehicleModel.id == Vehicle.model_id)
        .where(Vehicle.id == vehicle_id, Vehicle.is_deleted == 0)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise BizException(code=404, message="车辆不存在")
    vehicle, model = row
    return _to_vehicle_vo(vehicle, model)


async def create_vehicle(
    db: AsyncSession,
    payload: VehicleCreate,
    current_user_id: int,
) -> VehicleVO:
    """新增车辆；车牌号重复返回 409，`created_by` 取当前登录用户。"""
    await _ensure_plate_no_available(db, payload.plate_no)
    await _ensure_model_exists(db, payload.model_id)

    vehicle = Vehicle(
        **payload.model_dump(),
        created_by=current_user_id,
        updated_by=current_user_id,
    )
    db.add(vehicle)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="车牌号已存在") from exc
    return await get_vehicle(db, vehicle.id)


async def update_vehicle(
    db: AsyncSession,
    vehicle_id: int,
    payload: VehicleUpdate,
    current_user_id: int,
) -> VehicleVO:
    """编辑车辆（仅更新传入字段）；改车牌仍做唯一校验。"""
    vehicle = await _get_vehicle_or_404(db, vehicle_id)
    data = payload.model_dump(exclude_unset=True)
    _reject_null(data, {"plate_no": "车牌号", "status": "状态"})

    new_plate_no = data.get("plate_no")
    if new_plate_no and new_plate_no != vehicle.plate_no:
        await _ensure_plate_no_available(db, new_plate_no, exclude_id=vehicle.id)
    if "model_id" in data:
        await _ensure_model_exists(db, data["model_id"])

    for field, value in data.items():
        setattr(vehicle, field, value)
    vehicle.updated_by = current_user_id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="车牌号已存在") from exc
    return await get_vehicle(db, vehicle.id)


async def delete_vehicle(
    db: AsyncSession,
    vehicle_id: int,
    current_user_id: int,
) -> None:
    """逻辑删除车辆；已产生维修工单 / 出库单 / 装用配件时拒绝删除。"""
    vehicle = await _get_vehicle_or_404(db, vehicle_id)

    if await _exists(
        db,
        select(WorkOrder.id).where(
            WorkOrder.vehicle_id == vehicle.id,
            WorkOrder.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该车辆已存在维修工单，无法删除")

    if await _exists(
        db,
        select(OutboundOrder.id).where(
            OutboundOrder.vehicle_id == vehicle.id,
            OutboundOrder.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该车辆已存在出库单，无法删除")

    if await _exists(
        db,
        select(InventoryItem.id).where(
            InventoryItem.vehicle_id == vehicle.id,
            InventoryItem.is_deleted == 0,
        ),
    ):
        raise BizException(code=409, message="该车辆已装用配件，无法删除")

    vehicle.is_deleted = 1
    vehicle.updated_by = current_user_id
    await db.commit()
