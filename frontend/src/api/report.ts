import request from '@/utils/request'
import type { PageResult } from '@/types/api'

/** 库存变动业务类型 */
export type BizType =
  | 'IN'
  | 'OUT'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT'
  | 'ADJUST_IN'
  | 'ADJUST_OUT'

/** 关联单据类型 */
export type RefType = 'INBOUND' | 'OUTBOUND' | 'TRANSFER' | 'STOCKTAKE'

/** 库存报表一行（配件 + 仓库 + 库位维度），对应后端 InventoryReportVO */
export interface InventoryReportRow {
  partId: number
  partCode: string
  partName: string
  spec: string | null
  unit: string | null
  categoryId: number | null
  categoryName: string | null
  warehouseId: number
  warehouseName: string | null
  locationId: number | null
  locationCode: string | null
  quantity: number
  itemCount: number
  lockedQty: number
  avgCost: number
  amount: number
  safetyStock: number | null
  maxStock: number | null
}

/** 库存报表合计 */
export interface InventoryReportSummary {
  partKinds: number
  totalQuantity: number
  totalAmount: number
  lowStockCount: number
}

/** 库存报表查询条件 */
export interface InventoryReportQuery {
  page?: number
  pageSize?: number
  keyword?: string
  partId?: number
  categoryId?: number
  warehouseId?: number
  locationId?: number
  lowStock?: boolean
  includeZero?: boolean
}

/** 库存报表返回结构 */
export interface InventoryReportResult extends PageResult<InventoryReportRow> {
  summary?: InventoryReportSummary
}

/** 流水报表一行，对应后端 TransactionReportVO */
export interface TransactionReportRow {
  id: number
  partId: number
  partCode: string | null
  partName: string | null
  inventoryItemId: number | null
  warehouseId: number
  warehouseName: string | null
  locationId: number | null
  locationCode: string | null
  bizType: BizType
  changeQty: number
  beforeQty: number
  afterQty: number
  unitCost: number | null
  refType: RefType
  refId: number | null
  refNo: string | null
  batchNo: string | null
  scanCode: string | null
  operatorId: number | null
  createdAt: string
}

/** 流水报表合计 */
export interface TransactionReportSummary {
  inQty: number
  outQty: number
  transferInQty: number
  transferOutQty: number
  adjustInQty: number
  adjustOutQty: number
  netQty: number
}

/** 流水报表查询条件 */
export interface TransactionReportQuery {
  page?: number
  pageSize?: number
  keyword?: string
  partId?: number
  warehouseId?: number
  bizType?: BizType
  refType?: RefType
  refNo?: string
  startTime?: string
  endTime?: string
}

/** 流水报表返回结构 */
export interface TransactionReportResult extends PageResult<TransactionReportRow> {
  summary?: TransactionReportSummary
}

/** 单车成本报表一行，对应后端 VehicleCostVO */
export interface VehicleCostReportRow {
  vehicleId: number
  plateNo: string
  modelId: number | null
  modelName: string | null
  department: string | null
  repairCount: number
  totalPartsCost: number
  totalLaborCost: number
  totalCost: number
  lastRepairAt: string | null
}

/** 单车成本查询条件 */
export interface VehicleCostReportQuery {
  page?: number
  pageSize?: number
  vehicleId?: number
  modelId?: number
  department?: string
  startTime?: string
  endTime?: string
}

/** 单车成本返回结构 */
export interface VehicleCostReportResult extends PageResult<VehicleCostReportRow> {
  summary?: {
    vehicleCount: number
    repairCount: number
    totalPartsCost: number
    totalLaborCost: number
    totalCost: number
  }
}

/** 首页看板数据，对应后端 DashboardVO */
export interface DashboardData {
  partCount: number
  vehicleCount: number
  warehouseCount: number
  inventoryQuantity: number
  inventoryAmount: number
  lowStockCount: number
  pendingInboundCount: number
  pendingOutboundCount: number
  repairingWorkOrderCount: number
  monthInboundAmount: number
  monthOutboundAmount: number
}

// ---------------------------------------------------------------- 报表

/** 库存报表分页 */
export function getInventoryReport(params: InventoryReportQuery) {
  return request.get<InventoryReportResult>('/reports/inventory', { params })
}

/**
 * 导出库存报表 Excel。
 * 后端以文件流返回，request 拦截器对非标准响应直接透传，因此这里拿到的是 Blob。
 */
export async function exportInventoryReport(params: InventoryReportQuery): Promise<Blob> {
  const result = await request.get<Blob>('/reports/inventory/export', {
    params,
    responseType: 'blob'
  })
  return result as unknown as Blob
}

/** 流水报表分页 */
export function getTransactionReport(params: TransactionReportQuery) {
  return request.get<TransactionReportResult>('/reports/transaction', { params })
}

/** 单车成本报表分页 */
export function getVehicleCostReport(params: VehicleCostReportQuery) {
  return request.get<VehicleCostReportResult>('/reports/vehicle-cost', { params })
}

/**
 * 首页看板聚合数据。
 * 后端报表模块尚未上线时静默失败，由页面回退到现有列表接口聚合。
 */
export function getDashboardData() {
  return request.get<DashboardData>('/reports/dashboard', { silent: true })
}
