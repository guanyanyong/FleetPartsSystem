import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 仓库 */
export interface Warehouse extends AuditFields {
  id: number
  name: string
  address: string | null
  keeperId: number | null
  /** 后端暂未返回负责人姓名，预留字段便于后续扩展 */
  keeperName?: string | null
  status: number
}

/** 仓库分页查询条件 */
export interface WarehouseQuery {
  page?: number
  pageSize?: number
  keyword?: string
  keeperId?: number
  status?: number
}

/** 新增 / 编辑仓库请求体 */
export interface WarehousePayload {
  name: string
  address?: string | null
  keeperId?: number | null
  status?: number
}

/** 库位 */
export interface WarehouseLocation extends AuditFields {
  id: number
  warehouseId: number
  locationCode: string
  locationQrcode: string | null
  remark: string | null
  status: number
}

/** 库位分页查询条件 */
export interface WarehouseLocationQuery {
  page?: number
  pageSize?: number
  warehouseId?: number
  keyword?: string
  status?: number
}

/** 新增 / 编辑库位请求体 */
export interface WarehouseLocationPayload {
  warehouseId: number
  locationCode: string
  locationQrcode?: string | null
  remark?: string | null
  status?: number
}

// ---------------------------------------------------------------- 仓库

/** 仓库分页列表 */
export function getWarehouseList(params: WarehouseQuery) {
  return request.get<PageResult<Warehouse>>('/warehouses', { params })
}

/** 仓库详情 */
export function getWarehouseDetail(id: number) {
  return request.get<Warehouse>(`/warehouses/${id}`)
}

/** 新增仓库 */
export function createWarehouse(data: WarehousePayload) {
  return request.post<Warehouse>('/warehouses', data)
}

/** 编辑仓库 */
export function updateWarehouse(id: number, data: Partial<WarehousePayload>) {
  return request.put<Warehouse>(`/warehouses/${id}`, data)
}

/** 逻辑删除仓库（仓库下仍有库位 / 库存时后端返回 409） */
export function deleteWarehouse(id: number) {
  return request.delete<null>(`/warehouses/${id}`)
}

/** 仓库下拉选项：后端单页最多 200 条，按名称关键字分页拉取 */
export async function getAllWarehouses(status?: number): Promise<Warehouse[]> {
  const pageSize = 200
  const result: Warehouse[] = []
  let page = 1
  let total = 0

  do {
    const res = await getWarehouseList({ page, pageSize, status })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}

// ---------------------------------------------------------------- 库位

/** 库位分页列表 */
export function getWarehouseLocationList(params: WarehouseLocationQuery) {
  return request.get<PageResult<WarehouseLocation>>('/warehouse-locations', { params })
}

/** 新增库位 */
export function createWarehouseLocation(data: WarehouseLocationPayload) {
  return request.post<WarehouseLocation>('/warehouse-locations', data)
}

/** 编辑库位 */
export function updateWarehouseLocation(
  id: number,
  data: Partial<WarehouseLocationPayload>
) {
  return request.put<WarehouseLocation>(`/warehouse-locations/${id}`, data)
}

/** 逻辑删除库位（库位仍有库存或库存件时后端返回 409） */
export function deleteWarehouseLocation(id: number) {
  return request.delete<null>(`/warehouse-locations/${id}`)
}

/** 指定仓库的启用库位下拉选项（循环拉取全量） */
export async function getAllWarehouseLocations(warehouseId: number): Promise<WarehouseLocation[]> {
  const pageSize = 200
  const result: WarehouseLocation[] = []
  let page = 1
  let total = 0

  do {
    const res = await getWarehouseLocationList({
      page,
      pageSize,
      warehouseId,
      status: 1
    })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}
