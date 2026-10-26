import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 供应商 */
export interface Supplier extends AuditFields {
  id: number
  name: string
  contact: string | null
  phone: string | null
  address: string | null
  mainCategory: string | null
  paymentTerm: string | null
  status: number
}

/** 供应商分页查询条件 */
export interface SupplierQuery {
  page?: number
  pageSize?: number
  keyword?: string
  mainCategory?: string
  status?: number
}

/** 新增 / 编辑供应商请求体 */
export interface SupplierPayload {
  name: string
  contact?: string | null
  phone?: string | null
  address?: string | null
  mainCategory?: string | null
  paymentTerm?: string | null
  status?: number
}

/** 供应商分页列表 */
export function getSupplierList(params: SupplierQuery) {
  return request.get<PageResult<Supplier>>('/suppliers', { params })
}

/** 供应商详情 */
export function getSupplierDetail(id: number) {
  return request.get<Supplier>(`/suppliers/${id}`)
}

/** 新增供应商 */
export function createSupplier(data: SupplierPayload) {
  return request.post<Supplier>('/suppliers', data)
}

/** 编辑供应商 */
export function updateSupplier(id: number, data: Partial<SupplierPayload>) {
  return request.put<Supplier>(`/suppliers/${id}`, data)
}

/** 逻辑删除供应商（存在关联入库单时后端返回 409） */
export function deleteSupplier(id: number) {
  return request.delete<null>(`/suppliers/${id}`)
}

/**
 * 供应商下拉选项：后端单页最多 200 条，循环拉取全量。
 * @param status 1 合作 0 停用，不传返回全部
 */
export async function getAllSuppliers(status?: number): Promise<Supplier[]> {
  const pageSize = 200
  const result: Supplier[] = []
  let page = 1
  let total = 0

  do {
    const res = await getSupplierList({ page, pageSize, status })
    const { list, total: count } = res.data
    result.push(...list)
    total = count
    page += 1
  } while (result.length < total)

  return result
}
