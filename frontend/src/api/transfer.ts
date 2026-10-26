import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 调拨单状态：1草稿 2待审 3已调出 4已调入 5作废 */
export type TransferStatus = 1 | 2 | 3 | 4 | 5

/** 调拨单主表，对应后端 TransferOrderVO */
export interface TransferOrder extends AuditFields {
  id: number
  orderNo: string
  fromWarehouseId: number
  toWarehouseId: number
  status: TransferStatus
  operatorId: number | null
  auditUserId: number | null
  transferAt: string | null
  remark: string | null
  fromWarehouseName: string | null
  toWarehouseName: string | null
}

/** 调拨明细，对应后端 TransferOrderItemVO */
export interface TransferOrderItem extends AuditFields {
  id: number
  orderId: number
  partId: number
  inventoryItemId: number | null
  quantity: number
  fromLocationId: number | null
  toLocationId: number | null
  batchNo: string | null
  remark: string | null
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  itemCode: string | null
  fromLocationCode: string | null
  toLocationCode: string | null
}

/** 调拨单详情（含明细） */
export interface TransferOrderDetail extends TransferOrder {
  items: TransferOrderItem[]
}

/** 调拨单分页查询条件 */
export interface TransferOrderQuery {
  page?: number
  pageSize?: number
  keyword?: string
  orderNo?: string
  fromWarehouseId?: number
  toWarehouseId?: number
  status?: TransferStatus
  operatorId?: number
  startTime?: string
  endTime?: string
}

/** 调拨明细请求体 */
export interface TransferOrderItemPayload {
  partId: number
  inventoryItemId?: number | null
  quantity: number
  fromLocationId?: number | null
  toLocationId?: number | null
  batchNo?: string | null
  remark?: string | null
}

/** 新建调拨单请求体 */
export interface TransferOrderPayload {
  fromWarehouseId: number
  toWarehouseId: number
  operatorId?: number | null
  remark?: string | null
  items: TransferOrderItemPayload[]
}

/** 编辑草稿调拨单请求体，items 传 null 表示不修改明细 */
export interface TransferOrderUpdatePayload
  extends Partial<Omit<TransferOrderPayload, 'items'>> {
  items?: TransferOrderItemPayload[] | null
}

// ---------------------------------------------------------------- 调拨单

/** 调拨单分页列表 */
export function getTransferOrderList(params: TransferOrderQuery) {
  return request.get<PageResult<TransferOrder>>('/transfer-orders', { params })
}

/** 调拨单详情（含明细） */
export function getTransferOrderDetail(id: number) {
  return request.get<TransferOrderDetail>(`/transfer-orders/${id}`)
}

/** 新建调拨单（草稿） */
export function createTransferOrder(data: TransferOrderPayload) {
  return request.post<TransferOrderDetail>('/transfer-orders', data)
}

/** 编辑草稿调拨单；传 items 时整体替换原明细 */
export function updateTransferOrder(id: number, data: TransferOrderUpdatePayload) {
  return request.put<TransferOrderDetail>(`/transfer-orders/${id}`, data)
}

/** 确认调出：1草稿 / 2待审 -> 3已调出，扣减调出仓库存 */
export function transferOutOrder(id: number) {
  return request.post<TransferOrderDetail>(`/transfer-orders/${id}/transfer-out`)
}

/** 确认调入：3已调出 -> 4已调入，增加调入仓库存 */
export function transferInOrder(id: number) {
  return request.post<TransferOrderDetail>(`/transfer-orders/${id}/transfer-in`)
}

/** 作废调拨单：1草稿 / 2待审 -> 5作废 */
export function cancelTransferOrder(id: number) {
  return request.post<TransferOrderDetail>(`/transfer-orders/${id}/cancel`)
}
