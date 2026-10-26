import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 车型下拉选项，对应后端 VehicleModelVO */
export interface VehicleModelOption extends AuditFields {
  id: number
  brand: string
  modelName: string
  tonnage: string | null
  remark: string | null
  status: number
}

/** 车辆，对应后端 VehicleVO */
export interface VehicleOption {
  id: number
  plateNo: string
  modelId: number | null
  brand: string | null
  modelName: string | null
  vin: string | null
  engineNo: string | null
  purchaseDate: string | null
  department: string | null
  /** 1在用 2维修 3停用 4报废 */
  status: number
  mileage: number | null
  remark: string | null
  createdAt: string
  updatedAt: string
}

export interface VehicleQuery {
  page?: number
  pageSize?: number
  keyword?: string
  modelId?: number
  department?: string
  status?: number
}

/** 新增 / 编辑车辆请求体 */
export interface VehiclePayload {
  plateNo: string
  modelId?: number | null
  vin?: string | null
  engineNo?: string | null
  purchaseDate?: string | null
  department?: string | null
  /** 1在用 2维修 3停用 4报废 */
  status?: number
  mileage?: number | null
  remark?: string | null
}

/** 新增 / 编辑车型请求体 */
export interface VehicleModelPayload {
  brand: string
  modelName: string
  tonnage?: string | null
  remark?: string | null
  status?: number
}

/** 车辆分页列表 */
export function getVehicleList(params: VehicleQuery) {
  return request.get<PageResult<VehicleOption>>('/vehicles', { params })
}

/** 新增车辆 */
export function createVehicle(data: VehiclePayload) {
  return request.post<VehicleOption>('/vehicles', data)
}

/** 编辑车辆 */
export function updateVehicle(id: number, data: Partial<VehiclePayload>) {
  return request.put<VehicleOption>(`/vehicles/${id}`, data)
}

/** 逻辑删除车辆（存在关联工单时后端返回 409） */
export function deleteVehicle(id: number) {
  return request.delete<null>(`/vehicles/${id}`)
}

/** 车辆详情 */
export function getVehicleDetail(id: number) {
  return request.get<VehicleOption>(`/vehicles/${id}`)
}

/** 指定状态的车辆下拉选项（循环拉取全量，单页最多 200 条） */
export async function getAllVehicles(status?: number): Promise<VehicleOption[]> {
  const pageSize = 200
  const result: VehicleOption[] = []
  let page = 1
  let total = 0

  do {
    const res = await getVehicleList({ page, pageSize, status })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}

export interface VehicleModelQuery {
  page?: number
  pageSize?: number
  keyword?: string
  brand?: string
  status?: number
}

/** 车型分页列表（配件详情中维护适配车型时使用） */
export function getVehicleModelList(params: VehicleModelQuery) {
  return request.get<PageResult<VehicleModelOption>>('/vehicle-models', { params })
}

/** 新增车型 */
export function createVehicleModel(data: VehicleModelPayload) {
  return request.post<VehicleModelOption>('/vehicle-models', data)
}

/** 编辑车型 */
export function updateVehicleModel(id: number, data: Partial<VehicleModelPayload>) {
  return request.put<VehicleModelOption>(`/vehicle-models/${id}`, data)
}

/** 逻辑删除车型（已被车辆引用时后端返回 409） */
export function deleteVehicleModel(id: number) {
  return request.delete<null>(`/vehicle-models/${id}`)
}

/** 启用中的车型选项，单页最多 200 条 */
export async function getVehicleModelOptions(): Promise<VehicleModelOption[]> {
  const pageSize = 200
  const result: VehicleModelOption[] = []
  let page = 1
  let total = 0

  do {
    const res = await getVehicleModelList({ page, pageSize, status: 1 })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}
