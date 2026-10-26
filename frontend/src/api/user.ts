import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 用户下拉选项，对应后端 UserVO（不含密码） */
export interface UserOption extends AuditFields {
  id: number
  username: string
  realName: string | null
  phone: string | null
  role: string
  defaultWarehouseId: number | null
  status: number
}

export interface UserQuery {
  page?: number
  pageSize?: number
  keyword?: string
  role?: string
  status?: number
}

/** 角色选项（与后端 Role 枚举一致） */
export const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '库管员', value: 'keeper' },
  { label: '采购员', value: 'purchaser' },
  { label: '领导', value: 'leader' },
  { label: '只读', value: 'readonly' }
] as const

/** 新增用户请求体 */
export interface UserCreatePayload {
  username: string
  password: string
  realName?: string | null
  phone?: string | null
  role?: string
  defaultWarehouseId?: number | null
  status?: number
}

/** 编辑用户请求体 */
export interface UserUpdatePayload {
  username?: string
  realName?: string | null
  phone?: string | null
  role?: string
  defaultWarehouseId?: number | null
  status?: number
}

/**
 * 用户分页列表。
 * 后端仅允许 admin / leader 调用，用于仓库负责人等人员选择。
 */
export function getUserList(params: UserQuery) {
  return request.get<PageResult<UserOption>>('/users', { params })
}

/** 用户详情 */
export function getUserDetail(id: number) {
  return request.get<UserOption>(`/users/${id}`)
}

/** 新增用户 */
export function createUser(data: UserCreatePayload) {
  return request.post<UserOption>('/users', data)
}

/** 编辑用户 */
export function updateUser(id: number, data: UserUpdatePayload) {
  return request.put<UserOption>(`/users/${id}`, data)
}

/** 逻辑删除用户 */
export function deleteUser(id: number) {
  return request.delete<null>(`/users/${id}`)
}

/** 重置密码 */
export function resetUserPassword(id: number, password: string) {
  return request.put<null>(`/users/${id}/password`, { password })
}

/** 启用 / 停用 */
export function setUserStatus(id: number, status: number) {
  return request.put<UserOption>(`/users/${id}/status`, { status })
}

// ---------------------------------------------------------------- 操作日志

/** 操作日志，对应后端 operation_log 表 */
export interface OperationLog {
  id: number
  userId: number | null
  module: string | null
  action: string | null
  refType: string | null
  refId: number | null
  scanCode: string | null
  content: string | null
  ip: string | null
  createdAt: string | null
}

/** 操作日志查询条件 */
export interface OperationLogQuery {
  page?: number
  pageSize?: number
  keyword?: string
  userId?: number
  module?: string
  startTime?: string
  endTime?: string
}

/**
 * 操作日志分页列表。
 * 后端日志查询接口上线前调用会返回 404，页面需做降级提示。
 */
export function getOperationLogList(params: OperationLogQuery) {
  return request.get<PageResult<OperationLog>>('/operation-logs', { params, silent: true })
}

/** 操作日志详情 */
export function getOperationLogDetail(id: number) {
  return request.get<OperationLog>(`/operation-logs/${id}`)
}
