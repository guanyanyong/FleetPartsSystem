"""用户业务逻辑：分页查询、增删改、重置密码、启用/停用。

审计字段约定：`created_by` / `updated_by` 一律取当前登录用户 ID，
由路由层通过 `CurrentUserId` 依赖传入，不接受前端提交。
"""

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.security import hash_password
from app.models import SysUser
from app.models.enums import UserStatus
from app.schemas.common import PageResult
from app.schemas.user import UserCreate, UserQuery, UserUpdate, UserVO

__all__ = [
    "create_user",
    "delete_user",
    "get_user",
    "list_users",
    "reset_password",
    "set_status",
    "update_user",
]


def _hash_or_400(password: str) -> str:
    """生成密码哈希；超长等非法密码转为 400 业务错误。"""
    try:
        return hash_password(password)
    except ValueError as exc:
        raise BizException(code=400, message=str(exc)) from exc


async def _get_or_404(db: AsyncSession, user_id: int) -> SysUser:
    user = await db.get(SysUser, user_id)
    if user is None or user.is_deleted:
        raise BizException(code=404, message="用户不存在")
    return user


async def _ensure_username_available(
    db: AsyncSession,
    username: str,
    exclude_id: int | None = None,
) -> None:
    """登录名唯一性校验（包含已逻辑删除的数据，与唯一索引保持一致）。"""
    stmt: Select[tuple[int]] = select(SysUser.id).where(SysUser.username == username)
    if exclude_id is not None:
        stmt = stmt.where(SysUser.id != exclude_id)
    if (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None:
        raise BizException(code=409, message="登录名已存在")


async def list_users(db: AsyncSession, query: UserQuery) -> PageResult[UserVO]:
    """用户分页查询，支持用户名/姓名/电话关键字、角色、状态、默认仓库筛选。"""
    conditions = [SysUser.is_deleted == 0]
    if query.keyword:
        keyword = f"%{query.keyword.strip()}%"
        conditions.append(
            or_(
                SysUser.username.like(keyword),
                SysUser.real_name.like(keyword),
                SysUser.phone.like(keyword),
            )
        )
    if query.role:
        conditions.append(SysUser.role == query.role)
    if query.status is not None:
        conditions.append(SysUser.status == query.status)
    if query.default_warehouse_id is not None:
        conditions.append(SysUser.default_warehouse_id == query.default_warehouse_id)

    total = (
        await db.execute(select(func.count()).select_from(SysUser).where(*conditions))
    ).scalar_one()

    stmt = (
        select(SysUser)
        .where(*conditions)
        .order_by(SysUser.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return PageResult[UserVO](
        list=[UserVO.model_validate(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


async def get_user(db: AsyncSession, user_id: int) -> UserVO:
    """用户详情。"""
    return UserVO.model_validate(await _get_or_404(db, user_id))


async def create_user(
    db: AsyncSession,
    payload: UserCreate,
    current_user_id: int,
) -> UserVO:
    """新增用户，`created_by` 取当前登录用户。"""
    await _ensure_username_available(db, payload.username)
    user = SysUser(
        username=payload.username,
        password_hash=_hash_or_400(payload.password),
        real_name=payload.real_name,
        phone=payload.phone,
        role=payload.role,
        default_warehouse_id=payload.default_warehouse_id,
        status=payload.status,
        created_by=current_user_id,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="登录名已存在") from exc
    await db.refresh(user)
    return UserVO.model_validate(user)


async def update_user(
    db: AsyncSession,
    user_id: int,
    payload: UserUpdate,
    current_user_id: int,
) -> UserVO:
    """编辑用户（仅更新传入字段），`updated_by` 取当前登录用户。"""
    user = await _get_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    new_username = data.get("username")
    if new_username and new_username != user.username:
        await _ensure_username_available(db, new_username, exclude_id=user.id)

    for field, value in data.items():
        setattr(user, field, value)
    user.updated_by = current_user_id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise BizException(code=409, message="登录名已存在") from exc
    await db.refresh(user)
    return UserVO.model_validate(user)


async def delete_user(db: AsyncSession, user_id: int, current_user_id: int) -> None:
    """逻辑删除用户（is_deleted=1）。"""
    if user_id == current_user_id:
        raise BizException(code=409, message="不能删除当前登录账号")
    user = await _get_or_404(db, user_id)
    user.is_deleted = 1
    user.updated_by = current_user_id
    await db.commit()


async def reset_password(
    db: AsyncSession,
    user_id: int,
    password: str,
    current_user_id: int,
) -> None:
    """重置密码。"""
    user = await _get_or_404(db, user_id)
    user.password_hash = _hash_or_400(password)
    user.updated_by = current_user_id
    await db.commit()


async def set_status(
    db: AsyncSession,
    user_id: int,
    new_status: int,
    current_user_id: int,
) -> UserVO:
    """启用/停用用户；不允许停用当前登录账号。"""
    if user_id == current_user_id and new_status != UserStatus.ENABLED:
        raise BizException(code=409, message="不能停用当前登录账号")
    user = await _get_or_404(db, user_id)
    user.status = new_status
    user.updated_by = current_user_id
    await db.commit()
    await db.refresh(user)
    return UserVO.model_validate(user)
