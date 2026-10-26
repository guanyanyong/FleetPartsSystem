"""维修工单业务逻辑：分页查询、增删改查、状态流转（开始维修 / 完工 / 结算）。

约定：
- 查询统一过滤 `is_deleted == 0`（子表 `work_order_part` 同样过滤）；
- `created_by` / `updated_by` 由路由层通过 `CurrentUserId` 注入，不接受前端提交；
- 工单号 `WO + yyyyMMdd + 6 位流水` 由 `code_generator` 生成，插入时若唯一索引
  `uk_order_no` 冲突（并发取到相同流水号）自动重新取号，最多重试 5 次；
- 状态机：1待修 → 2维修中 → 3已完工 → 4已结算，非法流转返回业务码 3001；
- 完工时把 `work_order_part.cost` 汇总到 `total_parts_cost`；结算时填写工时费。
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models import Part, SysUser, Vehicle, WorkOrder, WorkOrderPart
from app.models.enums import CommonStatus, RepairType, WorkOrderStatus
from app.schemas.common import PageResult
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderDetailVO,
    WorkOrderPartVO,
    WorkOrderQuery,
    WorkOrderSettle,
    WorkOrderUpdate,
    WorkOrderVO,
)
from app.services.code_generator import (
    WORK_ORDER_SEQUENCE,
    SequenceExhausted,
    generate_work_order_no,
    next_sequence,
)

__all__ = [
    "create_work_order",
    "finish_work_order",
    "get_work_order",
    "list_work_order_parts",
    "list_work_orders",
    "settle_work_order",
    "start_work_order",
    "update_work_order",
]

# 业务错误码：单据状态不允许操作（见 docs/backend-requirements.md 错误码约定）
ORDER_STATUS_NOT_ALLOWED: int = 3001

# 工单号冲突重试次数
ORDER_NO_MAX_RETRY: int = 5

# 维修类型取值（work_order.repair_type）
REPAIR_TYPES: frozenset[str] = frozenset(
    {RepairType.MAINTENANCE, RepairType.REPAIR, RepairType.ACCIDENT}
)


# ---------------------------------------------------------------- 内部工具
def _reject_null(data: dict[str, Any], labels: dict[str, str]) -> None:
    """编辑时显式提交 null 视为参数错误，避免覆盖非空列后抛 500。"""
    for field, label in labels.items():
        if field in data and data[field] is None:
            raise BizException(code=400, message=f"{label}不能为空")


def _money(value: Decimal | int | None) -> Decimal:
    """金额统一保留两位小数（四舍五入）。"""
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_order_or_404(
    db: AsyncSession,
    order_id: int,
    *,
    for_update: bool = False,
) -> WorkOrder:
    """取工单；状态流转类操作加行锁，避免并发重复开工 / 完工 / 结算。"""
    stmt = select(WorkOrder).where(
        WorkOrder.id == order_id,
        WorkOrder.is_deleted == 0,
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise BizException(code=404, message="维修工单不存在")
    return order


async def _ensure_vehicle_exists(db: AsyncSession, vehicle_id: int) -> None:
    """校验关联车辆存在。"""
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.is_deleted:
        raise BizException(code=404, message="车辆不存在")


async def _ensure_repair_man_exists(
    db: AsyncSession, repair_man_id: int | None
) -> None:
    """校验维修负责人存在且启用（未传表示不指定负责人）。"""
    if repair_man_id is None:
        return
    user = await db.get(SysUser, repair_man_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message="维修负责人不存在")
    if user.status != CommonStatus.ENABLED:
        raise BizException(code=400, message="维修负责人已停用")


def _ensure_repair_type(repair_type: str) -> None:
    """校验维修类型取值。"""
    if repair_type not in REPAIR_TYPES:
        raise BizException(
            code=400,
            message="维修类型不正确，可选 MAINTENANCE/REPAIR/ACCIDENT",
        )


def _to_order_vo(
    order: WorkOrder,
    plate_no: str | None = None,
    repair_man_name: str | None = None,
) -> WorkOrderVO:
    """主表实体转 VO，并补充车牌号 / 维修负责人姓名。"""
    vo = WorkOrderVO.model_validate(order)
    vo.plate_no = plate_no
    vo.repair_man_name = repair_man_name
    return vo


def _to_part_vo(line: WorkOrderPart, part: Part | None = None) -> WorkOrderPartVO:
    """领料记录转 VO，并补充配件展示字段。"""
    vo = WorkOrderPartVO.model_validate(line)
    if part is not None:
        vo.part_code = part.part_code
        vo.part_name = part.part_name
        vo.spec = part.spec
        vo.unit = part.unit
    return vo


def _order_query() -> Any:
    """工单查询骨架：带车牌号、维修负责人姓名。"""
    return (
        select(WorkOrder, Vehicle.plate_no, SysUser.real_name)
        .outerjoin(Vehicle, Vehicle.id == WorkOrder.vehicle_id)
        .outerjoin(SysUser, SysUser.id == WorkOrder.repair_man_id)
    )


def _part_query() -> Any:
    """领料记录查询骨架：带配件编码 / 名称 / 规格 / 单位。"""
    return select(WorkOrderPart, Part).outerjoin(Part, Part.id == WorkOrderPart.part_id)


# ---------------------------------------------------------------- 创建 / 查询
async def _insert_order_with_retry(
    db: AsyncSession,
    payload: WorkOrderCreate,
    current_user_id: int,
) -> WorkOrder:
    """插入工单主表；单号冲突（并发取到同一流水号）时重新取号。"""
    for attempt in range(1, ORDER_NO_MAX_RETRY + 1):
        try:
            seq = await next_sequence(db, WORK_ORDER_SEQUENCE)
        except SequenceExhausted as exc:
            raise BizException(
                code=409,
                message="当日维修工单号已用尽，请联系管理员",
            ) from exc

        order = WorkOrder(
            order_no=generate_work_order_no(seq),
            vehicle_id=payload.vehicle_id,
            repair_type=payload.repair_type,
            description=payload.description,
            repair_man_id=payload.repair_man_id,
            in_at=payload.in_at or datetime.now(),
            status=WorkOrderStatus.WAITING,
            total_parts_cost=Decimal("0.00"),
            total_labor_cost=Decimal("0.00"),
            remark=payload.remark,
            created_by=current_user_id,
            updated_by=current_user_id,
        )
        db.add(order)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # 仅单号重复可重试，其它完整性错误直接暴露
            if "uk_order_no" not in str(exc.orig):
                raise BizException(
                    code=409,
                    message="维修工单保存失败，请检查后重试",
                ) from exc
            if attempt < ORDER_NO_MAX_RETRY:
                continue
            raise BizException(code=409, message="维修工单号生成冲突，请重试") from exc
        return order

    raise BizException(code=409, message="维修工单号生成冲突，请重试")


async def create_work_order(
    db: AsyncSession,
    payload: WorkOrderCreate,
    current_user_id: int,
) -> WorkOrderDetailVO:
    """新建维修工单（待修）：工单号自动生成，进厂时间默认当前时间。"""
    _ensure_repair_type(payload.repair_type)
    await _ensure_vehicle_exists(db, payload.vehicle_id)
    await _ensure_repair_man_exists(db, payload.repair_man_id)

    order = await _insert_order_with_retry(db, payload, current_user_id)
    return await get_work_order(db, order.id)


async def list_work_orders(
    db: AsyncSession,
    query: WorkOrderQuery,
) -> PageResult[WorkOrderVO]:
    """工单分页查询，支持工单号关键字、车辆、维修类型、负责人、状态、创建时间筛选。"""
    conditions = [WorkOrder.is_deleted == 0]
    if query.keyword:
        conditions.append(WorkOrder.order_no.like(f"%{query.keyword.strip()}%"))
    if query.order_no:
        conditions.append(WorkOrder.order_no.like(f"%{query.order_no.strip()}%"))
    if query.vehicle_id is not None:
        conditions.append(WorkOrder.vehicle_id == query.vehicle_id)
    if query.repair_type:
        conditions.append(WorkOrder.repair_type == query.repair_type)
    if query.repair_man_id is not None:
        conditions.append(WorkOrder.repair_man_id == query.repair_man_id)
    if query.status is not None:
        conditions.append(WorkOrder.status == query.status)
    if query.start_time is not None:
        conditions.append(WorkOrder.created_at >= query.start_time)
    if query.end_time is not None:
        conditions.append(WorkOrder.created_at <= query.end_time)

    total = (
        await db.execute(select(func.count()).select_from(WorkOrder).where(*conditions))
    ).scalar_one()

    stmt = (
        _order_query()
        .where(*conditions)
        .order_by(WorkOrder.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).all()

    return PageResult[WorkOrderVO](
        list=[_to_order_vo(order, plate_no, name) for order, plate_no, name in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_work_order(db: AsyncSession, order_id: int) -> WorkOrderDetailVO:
    """工单详情（主表 + 领料记录）。"""
    row = (
        await db.execute(
            _order_query().where(
                WorkOrder.id == order_id,
                WorkOrder.is_deleted == 0,
            )
        )
    ).first()
    if row is None:
        raise BizException(code=404, message="维修工单不存在")
    order, plate_no, repair_man_name = row

    detail = WorkOrderDetailVO(
        **_to_order_vo(order, plate_no, repair_man_name).model_dump()
    )
    detail.parts = await _load_parts(db, order.id)
    return detail


async def _load_parts(db: AsyncSession, order_id: int) -> list[WorkOrderPartVO]:
    """读取领料记录（按领料顺序升序），并补充配件展示字段。"""
    stmt = (
        _part_query()
        .where(
            WorkOrderPart.work_order_id == order_id,
            WorkOrderPart.is_deleted == 0,
        )
        .order_by(WorkOrderPart.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [_to_part_vo(line, part) for line, part in rows]


async def list_work_order_parts(
    db: AsyncSession,
    order_id: int,
) -> list[WorkOrderPartVO]:
    """工单领料记录（出库审核通过时由出库服务写入）。"""
    await _get_order_or_404(db, order_id)
    return await _load_parts(db, order_id)


# ---------------------------------------------------------------- 状态流转
async def update_work_order(
    db: AsyncSession,
    order_id: int,
    payload: WorkOrderUpdate,
    current_user_id: int,
) -> WorkOrderDetailVO:
    """编辑工单基础信息；已完工 / 已结算不允许编辑。

    状态、配件成本、工时费由开始维修 / 完工 / 结算接口维护，
    请求体中携带这些字段时直接拒绝，避免绕过状态机。
    """
    order = await _get_order_or_404(db, order_id)
    if order.status not in (WorkOrderStatus.WAITING, WorkOrderStatus.REPAIRING):
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="已完工或已结算的工单不允许编辑",
        )

    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="工单状态请通过开始维修 / 完工 / 结算操作变更",
        )
    if "total_parts_cost" in data:
        raise BizException(code=400, message="配件成本由完工时自动汇总，不支持手工修改")
    if "total_labor_cost" in data:
        raise BizException(code=400, message="工时费请通过结算操作填写")

    _reject_null(data, {"repair_type": "维修类型"})
    if "repair_type" in data:
        _ensure_repair_type(data["repair_type"])
    if "repair_man_id" in data:
        await _ensure_repair_man_exists(db, data["repair_man_id"])

    for field, value in data.items():
        setattr(order, field, value)
    order.updated_by = current_user_id
    await db.commit()
    return await get_work_order(db, order.id)


async def start_work_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> WorkOrderDetailVO:
    """开始维修：待修 → 维修中。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != WorkOrderStatus.WAITING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅待修状态的工单可以开始维修",
        )

    order.status = WorkOrderStatus.REPAIRING
    if order.in_at is None:
        order.in_at = datetime.now()
    order.updated_by = current_user_id
    await db.commit()
    return await get_work_order(db, order.id)


async def _sum_parts_cost(db: AsyncSession, order_id: int) -> Decimal:
    """汇总工单领料成本合计（work_order_part.cost）。"""
    total = (
        await db.execute(
            select(func.coalesce(func.sum(WorkOrderPart.cost), 0)).where(
                WorkOrderPart.work_order_id == order_id,
                WorkOrderPart.is_deleted == 0,
            )
        )
    ).scalar_one()
    return _money(total)


async def finish_work_order(
    db: AsyncSession,
    order_id: int,
    current_user_id: int,
) -> WorkOrderDetailVO:
    """完工：维修中 → 已完工，并把领料成本汇总到 total_parts_cost。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != WorkOrderStatus.REPAIRING:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅维修中状态的工单可以完工",
        )

    order.total_parts_cost = await _sum_parts_cost(db, order.id)
    order.status = WorkOrderStatus.FINISHED
    if order.out_at is None:
        order.out_at = datetime.now()
    order.updated_by = current_user_id
    await db.commit()
    return await get_work_order(db, order.id)


async def settle_work_order(
    db: AsyncSession,
    order_id: int,
    payload: WorkOrderSettle,
    current_user_id: int,
) -> WorkOrderDetailVO:
    """结算：已完工 → 已结算，填写工时费。"""
    order = await _get_order_or_404(db, order_id, for_update=True)
    if order.status != WorkOrderStatus.FINISHED:
        raise BizException(
            code=ORDER_STATUS_NOT_ALLOWED,
            message="仅已完工状态的工单可以结算",
        )

    order.total_labor_cost = _money(payload.total_labor_cost)
    order.status = WorkOrderStatus.SETTLED
    if payload.remark is not None:
        order.remark = payload.remark
    if order.out_at is None:
        order.out_at = datetime.now()
    order.updated_by = current_user_id
    await db.commit()
    return await get_work_order(db, order.id)
