import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 出库类型 */
export type OutboundType = 'REPAIR' | 'SALE' | 'RETURN' | 'TRANSFER' | 'SCRAP'

/** 出库单状态：1草稿 2待审 3已出库 4作废 */
export type OutboundStatus = 1 | 2 | 3 | 4

/** 扫码类型 */
export type ScanType = 'BARCODE' | 'QRCODE' | 'MANUAL'

/** 出库单明细 */
export interface OutboundOrderItem extends AuditFields {
  id: number
  orderId: number
  partId: number
  inventoryItemId: number | null
  quantity: number
  unit: string | null
  unitCost: number | null
  amount: number | null
  batchNo: string | null
  locationId: number | null
  scanCode: string | null
  scanType: string | null
  scanAt: string | null
  remark: string | null
  partCode: string | null
  partName: string | null
  spec: string | null
  itemCode: string | null
}

/** 出库单主表 */
export interface OutboundOrder extends AuditFields {
  id: number
  orderNo: string
  warehouseId: number
  outboundType: OutboundType
  vehicleId: number | null
  workOrderId: number | null
  receiverId: number | null
  totalAmount: number | null
  status: OutboundStatus
  scanMode: number
  scannerId: number | null
  operatorId: number | null
  auditUserId: number | null
  auditAt: string | null
  outboundAt: string | null
  remark: string | null
  warehouseName: string | null
  vehiclePlateNo: string | null
}

/** 出库单详情（含明细） */
export interface OutboundOrderDetail extends OutboundOrder {
  items: OutboundOrderItem[]
}

/** 出库单分页查询条件 */
export interface OutboundOrderQuery {
  page?: number
  pageSize?: number
  keyword?: string
  orderNo?: string
  warehouseId?: number
  outboundType?: OutboundType
  vehicleId?: number
  workOrderId?: number
  receiverId?: number
  status?: OutboundStatus
  scanMode?: number
  startTime?: string
  endTime?: string
}

/** 出库单明细请求体 */
export interface OutboundOrderItemPayload {
  partId: number
  inventoryItemId?: number | null
  quantity: number
  unit?: string | null
  unitCost?: number
  amount?: number | null
  batchNo?: string | null
  locationId?: number | null
  scanCode?: string | null
  scanType?: ScanType | null
  scanAt?: string | null
  remark?: string | null
}

/** 新建出库单请求体 */
export interface OutboundOrderPayload {
  warehouseId: number
  outboundType: OutboundType
  vehicleId?: number | null
  workOrderId?: number | null
  receiverId?: number | null
  scanMode?: number
  scannerId?: number | null
  operatorId?: number | null
  remark?: string | null
  items?: OutboundOrderItemPayload[]
}

/** 编辑草稿请求体，items 传 null 表示不修改明细 */
export interface OutboundOrderUpdatePayload
  extends Partial<Omit<OutboundOrderPayload, 'items'>> {
  items?: OutboundOrderItemPayload[] | null
}

// ---------------------------------------------------------------- 出库单

/** 出库单分页列表 */
export function getOutboundOrderList(params: OutboundOrderQuery) {
  return request.get<PageResult<OutboundOrder>>('/outbound-orders', { params })
}

/** 出库单详情（含明细） */
export function getOutboundOrderDetail(id: number) {
  return request.get<OutboundOrderDetail>(`/outbound-orders/${id}`)
}

/** 新建出库单（草稿） */
export function createOutboundOrder(data: OutboundOrderPayload) {
  return request.post<OutboundOrderDetail>('/outbound-orders', data)
}

/** 编辑草稿出库单；传 items 时整体替换原明细 */
export function updateOutboundOrder(id: number, data: OutboundOrderUpdatePayload) {
  return request.put<OutboundOrderDetail>(`/outbound-orders/${id}`, data)
}

/** 删除草稿出库单 */
export function deleteOutboundOrder(id: number) {
  return request.delete<null>(`/outbound-orders/${id}`)
}

/** 提交审核：1草稿 -> 2待审 */
export function submitOutboundOrder(id: number) {
  return request.post<OutboundOrderDetail>(`/outbound-orders/${id}/submit`)
}

/** 审核通过（执行出库）：2待审 -> 3已出库 */
export function approveOutboundOrder(id: number) {
  return request.post<OutboundOrderDetail>(`/outbound-orders/${id}/approve`)
}

/** 作废出库单：1草稿 / 2待审 -> 4作废 */
export function cancelOutboundOrder(id: number) {
  return request.post<OutboundOrderDetail>(`/outbound-orders/${id}/cancel`)
}

// ---------------------------------------------------------------- 扫码

/** 库存件扫码结果，对应后端 ScanResultVO */
export interface InventoryItemScanResult {
  itemId: number
  itemCode: string
  qrcode: string
  partId: number
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  batchNo: string | null
  /** 1在库 2锁定 3已出库 4已报废 5已盘亏 */
  status: number
  statusText: string
  warehouseId: number
  warehouseName: string | null
  locationId: number | null
  locationCode: string | null
  unitCost: number
  inAt: string | null
}

/**
 * 扫码查询库存件：`GET /scan/inventory-item?code=xxx`。
 *
 * 失败时后端返回 HTTP 200 + body.code（2002 已报废/盘亏、2003 已出库、
 * 2004 已锁定、4001 无法识别），request 拦截器会统一抛出带 code 的 ApiError。
 */
export function scanInventoryItem(code: string) {
  return request.get<InventoryItemScanResult | null>('/scan/inventory-item', {
    params: { code: code.trim() },
    silent: true
  })
}

