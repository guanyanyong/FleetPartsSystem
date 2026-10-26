import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 盘点单状态：1草稿 2盘点中 3已完成 4作废 */
export type StocktakeStatus = 1 | 2 | 3 | 4

/** 盘点单主表，对应后端 StocktakeOrderVO */
export interface StocktakeOrder extends AuditFields {
  id: number
  orderNo: string
  warehouseId: number
  status: StocktakeStatus
  operatorId: number | null
  auditUserId: number | null
  stocktakeAt: string | null
  remark: string | null
  warehouseName: string | null
}

/** 盘点明细，对应后端 StocktakeOrderItemVO */
export interface StocktakeOrderItem extends AuditFields {
  id: number
  orderId: number
  partId: number
  inventoryItemId: number | null
  locationId: number | null
  bookQty: number | null
  actualQty: number | null
  diffQty: number | null
  scanCode: string | null
  remark: string | null
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  itemCode: string | null
  locationCode: string | null
}

/** 盘点单详情（含明细） */
export interface StocktakeOrderDetail extends StocktakeOrder {
  items: StocktakeOrderItem[]
}

/** 盘点单分页查询条件 */
export interface StocktakeOrderQuery {
  page?: number
  pageSize?: number
  keyword?: string
  orderNo?: string
  warehouseId?: number
  status?: StocktakeStatus
  operatorId?: number
  startTime?: string
  endTime?: string
}

/** 新建盘点单明细：不传 items 时后端按仓库自动生成快照 */
export interface StocktakeOrderItemPayload {
  partId: number
  inventoryItemId?: number | null
  locationId?: number | null
  bookQty?: number
  actualQty?: number
  remark?: string | null
}

/** 新建 / 编辑盘点单请求体 */
export interface StocktakeOrderPayload {
  warehouseId: number
  operatorId?: number | null
  remark?: string | null
  items?: StocktakeOrderItemPayload[]
}

/** 编辑盘点单请求体，items 传 null 表示不修改明细 */
export interface StocktakeOrderUpdatePayload
  extends Partial<Omit<StocktakeOrderPayload, 'items'>> {
  items?: StocktakeOrderItemPayload[] | null
}

/** 修改实盘数量请求体 */
export interface StocktakeItemUpdatePayload {
  actualQty: number
  remark?: string | null
}

// ---------------------------------------------------------------- 盘点单

/** 盘点单分页列表 */
export function getStocktakeOrderList(params: StocktakeOrderQuery) {
  return request.get<PageResult<StocktakeOrder>>('/stocktake-orders', { params })
}

/** 盘点单详情（含明细） */
export function getStocktakeOrderDetail(id: number) {
  return request.get<StocktakeOrderDetail>(`/stocktake-orders/${id}`)
}

/** 新建盘点单（草稿），不传 items 时按仓库现有库存自动生成快照 */
export function createStocktakeOrder(data: StocktakeOrderPayload) {
  return request.post<StocktakeOrderDetail>('/stocktake-orders', data)
}

/** 编辑草稿盘点单；传 items 时整体替换原明细 */
export function updateStocktakeOrder(id: number, data: StocktakeOrderUpdatePayload) {
  return request.put<StocktakeOrderDetail>(`/stocktake-orders/${id}`, data)
}

/** 开始盘点：1草稿 -> 2盘点中 */
export function startStocktakeOrder(id: number) {
  return request.post<StocktakeOrderDetail>(`/stocktake-orders/${id}/start`)
}

/**
 * 扫码盘点：只接受盘点中状态的单据。
 * 失败时后端返回业务错误码（3001 状态不允许 / 4001 编码无法识别 / 2002 非在库）。
 */
export function scanStocktakeItem(id: number, code: string, locationId?: number) {
  return request.post<StocktakeOrderItem>(`/stocktake-orders/${id}/scan`, {
    code: code.trim(),
    locationId: locationId ?? null
  })
}

/** 手工修改实盘数量 */
export function updateStocktakeItem(
  orderId: number,
  itemId: number,
  data: StocktakeItemUpdatePayload
) {
  return request.put<StocktakeOrderItem>(
    `/stocktake-orders/${orderId}/items/${itemId}`,
    data
  )
}

/** 完成盘点：2盘点中 -> 3已完成，生成盘盈盘亏流水 */
export function finishStocktakeOrder(id: number) {
  return request.post<StocktakeOrderDetail>(`/stocktake-orders/${id}/finish`)
}

/** 作废盘点单：1草稿 / 2盘点中 -> 4作废 */
export function cancelStocktakeOrder(id: number) {
  return request.post<StocktakeOrderDetail>(`/stocktake-orders/${id}/cancel`)
}
