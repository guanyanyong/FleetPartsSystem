import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 库存汇总（按配件 + 仓库 + 库位），对应后端 InventoryDetailVO */
export interface InventoryDetail extends AuditFields {
  id: number
  partId: number
  warehouseId: number
  locationId: number | null
  quantity: number
  itemCount: number
  lockedQty: number
  avgCost: number
  lastInAt: string | null
  lastOutAt: string | null
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  safetyStock: number | null
  maxStock: number | null
  warehouseName: string | null
  locationCode: string | null
}

/** 库存汇总查询条件 */
export interface InventoryQuery {
  page?: number
  pageSize?: number
  keyword?: string
  partId?: number
  warehouseId?: number
  locationId?: number
  lowStock?: boolean
}

/** 库存汇总分页查询 */
export function getInventoryList(params: InventoryQuery) {
  return request.get<PageResult<InventoryDetail>>('/inventory', { params })
}
