import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'
import type { LabelItem } from '@/types/label'

/** 库存件状态：1在库 2锁定 3已出库 4已报废 5已盘亏 */
export type InventoryItemStatus = 1 | 2 | 3 | 4 | 5

/** 库存件（逐件追踪的实物） */
export interface InventoryItem extends AuditFields {
  id: number
  itemCode: string
  qrcode: string
  qrcodeImage: string | null
  partId: number
  warehouseId: number
  locationId: number | null
  batchNo: string | null
  serialNo: string | null
  productionDate: string | null
  expireDate: string | null
  unitCost: number
  status: InventoryItemStatus
  inboundItemId: number | null
  outboundItemId: number | null
  vehicleId: number | null
  workOrderId: number | null
  inAt: string | null
  outAt: string | null
  remark: string | null
}

/** 库存件列表 / 详情（带配件、仓库、库位展示字段） */
export interface InventoryItemDetail extends InventoryItem {
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  statusText: string | null
  warehouseName: string | null
  locationCode: string | null
}

/** 库存件分页查询条件 */
export interface InventoryItemQuery {
  page?: number
  pageSize?: number
  keyword?: string
  partId?: number
  warehouseId?: number
  locationId?: number
  status?: InventoryItemStatus
  vehicleId?: number
  workOrderId?: number
  batchNo?: string
  expireBefore?: string
}

/**
 * 编辑库存件请求体：只允许资料类字段。
 *
 * 库存件编码 / 二维码 / 数量 / 状态由入库、出库、调拨、盘点单据维护，
 * 后端不接受这些字段；`locationId: null` 表示改为仓库级存放（不指定库位）。
 */
export interface InventoryItemUpdatePayload {
  warehouseId?: number
  locationId?: number | null
  batchNo?: string | null
  serialNo?: string | null
  productionDate?: string | null
  expireDate?: string | null
  unitCost?: number
  remark?: string | null
}

/** 库存流水 */
export interface InventoryTransaction extends AuditFields {
  id: number
  partId: number
  inventoryItemId: number | null
  warehouseId: number
  locationId: number | null
  bizType: string
  changeQty: number
  beforeQty: number
  afterQty: number
  unitCost: number | null
  refType: string
  refId: number | null
  refNo: string | null
  batchNo: string | null
  scanCode: string | null
  operatorId: number | null
  remark: string | null
}

/** 库存流水分页查询条件 */
export interface InventoryTransactionQuery {
  page?: number
  pageSize?: number
  bizType?: string
  refType?: string
  refNo?: string
  startTime?: string
  endTime?: string
}

/** 库存件分页列表 */
export function getInventoryItemList(params: InventoryItemQuery) {
  return request.get<PageResult<InventoryItemDetail>>('/inventory-items', { params })
}

/** 库存件详情 */
export function getInventoryItemDetail(id: number) {
  return request.get<InventoryItemDetail>(`/inventory-items/${id}`)
}

/**
 * 编辑库存件资料（仅更新传入字段，编码 / 二维码 / 数量 / 状态不可改）。
 *
 * 仓库 / 库位变更按「单件调拨」记账：后端同步库存汇总并写调拨流水，
 * 仅「在库」实例可调整位置（其它状态返回 2002/2003/2004）。
 */
export function updateInventoryItem(id: number, data: InventoryItemUpdatePayload) {
  return request.put<InventoryItemDetail>(`/inventory-items/${id}`, data)
}

/** 库存件流水（分页） */
export function getInventoryItemTransactions(id: number, params: InventoryTransactionQuery = {}) {
  return request.get<PageResult<InventoryTransaction>>(`/inventory-items/${id}/transactions`, {
    params
  })
}

/**
 * 批量获取库存件打印数据。
 * 接口契约：`POST /inventory-items/print`，请求体 `{ ids: number[] }`。
 *
 * 后端暂未实现该接口时静默降级为逐个查询库存件详情，
 * 保证打印页在现有后端上仍可预览、打印标签。
 */
export async function getInventoryItemPrintData(ids: number[]): Promise<LabelItem[]> {
  try {
    const res = await request.post<LabelItem[]>(
      '/inventory-items/print',
      { ids },
      { silent: true }
    )
    return res.data
  } catch {
    const details = await Promise.all(ids.map((id) => getInventoryItemDetail(id)))
    return details.map((res) => {
      const item = res.data
      return {
        id: item.id,
        itemCode: item.itemCode,
        partName: item.partName ?? item.partCode ?? item.itemCode,
        spec: item.spec,
        batchNo: item.batchNo,
        qrcode: item.qrcode || item.itemCode,
        locationCode: item.locationCode
      }
    })
  }
}
