import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 维修工单，对应后端 WorkOrderVO */
export interface WorkOrderOption extends AuditFields {
  id: number
  orderNo: string
  vehicleId: number
  plateNo: string | null
  repairType: string
  description: string | null
  repairManId: number | null
  repairManName: string | null
  inAt: string | null
  outAt: string | null
  status: number
  totalPartsCost: string | number | null
  totalLaborCost: string | number | null
  remark: string | null
  createdAt: string
  updatedAt: string
}

/** 工单领料记录，对应后端 WorkOrderPartVO */
export interface WorkOrderPart extends AuditFields {
  id: number
  workOrderId: number
  outboundItemId: number | null
  partId: number
  partCode: string | null
  partName: string | null
  spec: string | null
  unit: string | null
  quantity: number | null
  cost: number | null
}

/** 维修工单详情（含领料记录） */
export interface WorkOrderDetail extends WorkOrderOption {
  parts: WorkOrderPart[]
}

/** 新建维修工单请求体 */
export interface WorkOrderPayload {
  vehicleId: number
  repairType: string
  description?: string | null
  repairManId?: number | null
  inAt?: string | null
  remark?: string | null
}

/** 编辑维修工单请求体 */
export interface WorkOrderUpdatePayload {
  repairType?: string
  description?: string | null
  repairManId?: number | null
  inAt?: string | null
  outAt?: string | null
  status?: number
  totalPartsCost?: number | null
  totalLaborCost?: number | null
  remark?: string | null
}

/** 工单分页查询条件 */
export interface WorkOrderQuery {
  page?: number
  pageSize?: number
  keyword?: string
  orderNo?: string
  vehicleId?: number
  repairType?: string
  repairManId?: number
  /** 1待修 2维修中 3已完工 4已结算 */
  status?: number
  startTime?: string
  endTime?: string
}

/** 维修工单分页列表 */
export function getWorkOrderList(params: WorkOrderQuery) {
  return request.get<PageResult<WorkOrderOption>>('/work-orders', { params })
}

/** 维修工单详情（含领料记录） */
export function getWorkOrderDetail(id: number) {
  return request.get<WorkOrderDetail>(`/work-orders/${id}`)
}

/** 新建维修工单 */
export function createWorkOrder(data: WorkOrderPayload) {
  return request.post<WorkOrderDetail>('/work-orders', data)
}

/** 编辑维修工单 */
export function updateWorkOrder(id: number, data: WorkOrderUpdatePayload) {
  return request.put<WorkOrderDetail>(`/work-orders/${id}`, data)
}

/** 开始维修：1待修 -> 2维修中 */
export function startWorkOrder(id: number) {
  return request.post<WorkOrderDetail>(`/work-orders/${id}/start`)
}

/** 完工：2维修中 -> 3已完工，自动汇总配件成本 */
export function finishWorkOrder(id: number) {
  return request.post<WorkOrderDetail>(`/work-orders/${id}/finish`)
}

/** 结算：3已完工 -> 4已结算 */
export function settleWorkOrder(id: number, totalLaborCost: number, remark?: string) {
  return request.post<WorkOrderDetail>(`/work-orders/${id}/settle`, {
    totalLaborCost,
    remark: remark ?? null
  })
}

/** 工单领料记录（按工单查询，取全量） */
export async function getWorkOrderParts(workOrderId: number): Promise<WorkOrderPart[]> {
  const pageSize = 200
  const result: WorkOrderPart[] = []
  let page = 1
  let total = 0

  do {
    const res = await request.get<PageResult<WorkOrderPart>>('/work-orders/parts', {
      params: { page, pageSize, workOrderId }
    })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}

/** 指定状态的工单下拉选项（循环拉取全量，单页最多 200 条） */
export async function getAllWorkOrders(status?: number): Promise<WorkOrderOption[]> {
  const pageSize = 200
  const result: WorkOrderOption[] = []
  let page = 1
  let total = 0

  do {
    const res = await getWorkOrderList({ page, pageSize, status })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}
