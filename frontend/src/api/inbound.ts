import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'
import type { LabelItem } from '@/types/label'

import { getInventoryItemList, type InventoryItemDetail } from '@/api/inventoryItem'
import { getPartList, type Part } from '@/api/part'

/** 入库类型 */
export type InboundType = 'PURCHASE' | 'RETURN' | 'TRANSFER' | 'ADJUST'

/** 入库单状态：1草稿 2待审 3已入库 4作废 */
export type InboundStatus = 1 | 2 | 3 | 4

/** 入库单明细 */
export interface InboundOrderItem extends AuditFields {
  id: number
  orderId: number
  partId: number
  quantity: number
  unit: string | null
  unitPrice: number
  amount: number | null
  batchNo: string | null
  productionDate: string | null
  expireDate: string | null
  locationId: number | null
  trackByItem: number
  generateItemQty: number | null
  generated: number
  scanCode: string | null
  remark: string | null
  partCode: string | null
  partName: string | null
  spec: string | null
}

/** 入库单主表 */
export interface InboundOrder extends AuditFields {
  id: number
  orderNo: string
  supplierId: number | null
  warehouseId: number
  inboundType: InboundType
  totalAmount: number | null
  status: InboundStatus
  operatorId: number | null
  auditUserId: number | null
  auditAt: string | null
  inboundAt: string | null
  remark: string | null
  warehouseName: string | null
  supplierName: string | null
}

/** 入库单详情（含明细） */
export interface InboundOrderDetail extends InboundOrder {
  items: InboundOrderItem[]
}

/** 入库单分页查询条件 */
export interface InboundOrderQuery {
  page?: number
  pageSize?: number
  keyword?: string
  orderNo?: string
  supplierId?: number
  warehouseId?: number
  inboundType?: InboundType
  status?: InboundStatus
  operatorId?: number
  startTime?: string
  endTime?: string
}

/** 入库单明细请求体 */
export interface InboundOrderItemPayload {
  partId: number
  quantity: number
  unit?: string | null
  unitPrice?: number
  amount?: number | null
  batchNo?: string | null
  productionDate?: string | null
  expireDate?: string | null
  locationId?: number | null
  trackByItem?: number
  scanCode?: string | null
  remark?: string | null
}

/** 新建入库单请求体 */
export interface InboundOrderPayload {
  supplierId?: number | null
  warehouseId: number
  inboundType: InboundType
  operatorId?: number | null
  remark?: string | null
  items?: InboundOrderItemPayload[]
}

/** 编辑草稿请求体，items 传 null 表示不修改明细 */
export interface InboundOrderUpdatePayload
  extends Partial<Omit<InboundOrderPayload, 'items'>> {
  items?: InboundOrderItemPayload[] | null
}

/** 扫码配件返回结果（非逐件追踪件入库扫码） */
export interface ScanPartResult {
  id?: number
  partId?: number
  partCode: string
  partName: string
  spec?: string | null
  unit?: string | null
  trackByItem?: number
  shelfLifeDays?: number | null
  stockQuantity?: number
}

// ---------------------------------------------------------------- 入库单

/** 入库单分页列表 */
export function getInboundOrderList(params: InboundOrderQuery) {
  return request.get<PageResult<InboundOrder>>('/inbound-orders', { params })
}

/** 入库单详情（含明细） */
export function getInboundOrderDetail(id: number) {
  return request.get<InboundOrderDetail>(`/inbound-orders/${id}`)
}

/** 新建入库单（创建后为草稿） */
export function createInboundOrder(data: InboundOrderPayload) {
  return request.post<InboundOrderDetail>('/inbound-orders', data)
}

/** 编辑草稿入库单 */
export function updateInboundOrder(id: number, data: InboundOrderUpdatePayload) {
  return request.put<InboundOrderDetail>(`/inbound-orders/${id}`, data)
}

/**
 * 删除入库单（仅草稿）。
 * 后端接口文档约定为逻辑删除；若后端未开放该接口，前端统一使用「作废」。
 */
export function deleteInboundOrder(id: number) {
  return request.delete<null>(`/inbound-orders/${id}`)
}

/** 提交审核：1 草稿 → 2 待审 */
export function submitInboundOrder(id: number) {
  return request.post<InboundOrderDetail>(`/inbound-orders/${id}/submit`)
}

/** 审核通过：2 待审 → 3 已入库（生成库存件与二维码） */
export function approveInboundOrder(id: number) {
  return request.post<InboundOrderDetail>(`/inbound-orders/${id}/approve`)
}

/** 作废：草稿/待审 → 4 作废 */
export function cancelInboundOrder(id: number) {
  return request.post<InboundOrderDetail>(`/inbound-orders/${id}/cancel`)
}

/** 入库单明细 */
export function getInboundOrderItems(id: number) {
  return request.get<InboundOrderItem[]>(`/inbound-orders/${id}/items`)
}

/** 把库存件接口返回的数据转换为标签打印数据 */
function toLabelItem(item: InventoryItemDetail): LabelItem {
  return {
    id: item.id,
    itemCode: item.itemCode,
    partName: item.partName ?? item.partCode ?? item.itemCode,
    spec: item.spec,
    batchNo: item.batchNo,
    qrcode: item.qrcode || item.itemCode,
    locationCode: item.locationCode
  }
}

/**
 * 按入库明细回查本次审核生成的库存件。
 *
 * 后端暂未提供入库单打印接口，这里按「配件 + 仓库 + 批次」分页查询库存件，
 * 再用 `inboundItemId` 精确过滤，避免把其它入库单生成的同批次库存件打出来。
 */
async function queryInboundItemsFallback(id: number): Promise<LabelItem[]> {
  const detail = (await getInboundOrderDetail(id)).data
  const targets = detail.items.filter(
    (item) => item.trackByItem === 1 && item.generated === 1
  )
  if (!targets.length) {
    return []
  }

  const labels: LabelItem[] = []
  const seen = new Set<number>()
  const pageSize = 200

  for (const target of targets) {
    let page = 1
    let total = 0
    do {
      const res = await getInventoryItemList({
        page,
        pageSize,
        partId: target.partId,
        warehouseId: detail.warehouseId,
        batchNo: target.batchNo || undefined
      })
      total = res.data.total
      res.data.list.forEach((row) => {
        if (row.inboundItemId === target.id && !seen.has(row.id)) {
          seen.add(row.id)
          labels.push(toLabelItem(row))
        }
      })
      page += 1
    } while ((page - 1) * pageSize < total)
  }

  return labels
}

/**
 * 获取入库单审核后生成的待打印库存件。
 *
 * 优先调用后端专用接口；接口缺失时自动降级为库存件查询，保证打印流程可用。
 */
export async function getInboundPrintItems(id: number): Promise<LabelItem[]> {
  try {
    const res = await request.get<LabelItem[]>(`/inbound-orders/${id}/print-items`, {
      silent: true
    })
    return res.data
  } catch {
    return queryInboundItemsFallback(id)
  }
}

// ---------------------------------------------------------------- 扫码

/**
 * 扫码查询配件：`GET /scan/part?code=xxx`。
 *
 * 后端暂未实现该接口时会自动降级为按配件编码查询（`GET /parts?keyword=xxx`），
 * 保证扫码入库在现有后端上仍可用；两条路径都失败时抛出异常，由页面提示。
 */
export async function scanPart(code: string) {
  const value = code.trim()
  try {
    return await request.get<ScanPartResult>('/scan/part', {
      params: { code: value },
      // 接口缺失时不弹出全局错误，直接走降级查询
      silent: true
    })
  } catch {
    const normalized = value.toLowerCase()
    const pageSize = 100
    let page = 1
    let total = 0
    let matched: Part | undefined

    // 后端暂无扫码接口时按配件编码精确匹配，避免误选模糊搜索的第一条
    do {
      const res = await getPartList({ page, pageSize, keyword: value, status: 1 })
      total = res.data.total
      matched = res.data.list.find(
        (part) => part.partCode.trim().toLowerCase() === normalized
      )
      page += 1
    } while (!matched && (page - 1) * pageSize < total)

    if (!matched) {
      throw new Error(`未找到配件：${value}`)
    }

    return {
      code: 200,
      message: 'success',
      data: {
        partId: matched.id,
        partCode: matched.partCode,
        partName: matched.partName,
        spec: matched.spec,
        unit: matched.unit,
        trackByItem: matched.trackByItem,
        shelfLifeDays: matched.shelfLifeDays,
        stockQuantity: matched.stockQuantity
      }
    }
  }
}
