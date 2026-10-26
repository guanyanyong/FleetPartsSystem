import request from '@/utils/request'
import type { AuditFields, PageResult } from '@/types/api'

/** 配件分类节点（GET /part-categories/tree 返回嵌套 children） */
export interface PartCategory extends AuditFields {
  id: number
  name: string
  parentId: number | null
  sort: number | null
  status: number
  children?: PartCategory[]
}

/** 新增 / 编辑分类请求体 */
export interface PartCategoryPayload {
  name: string
  parentId?: number | null
  sort?: number
  status?: number
}

/** 配件 */
export interface Part extends AuditFields {
  id: number
  partCode: string
  partName: string
  categoryId: number | null
  categoryName: string | null
  spec: string | null
  brand: string | null
  unit: string
  isGeneral: number
  safetyStock: number | null
  maxStock: number | null
  shelfLifeDays: number | null
  trackByItem: number
  scanEnabled: number
  remark: string | null
  status: number
  stockQuantity: number
}

/** 配件分页查询条件 */
export interface PartQuery {
  page?: number
  pageSize?: number
  keyword?: string
  partCode?: string
  categoryId?: number
  brand?: string
  isGeneral?: number
  trackByItem?: number
  scanEnabled?: number
  status?: number
}

/** 新增配件请求体（编辑时为该类型的可选字段） */
export interface PartPayload {
  partCode: string
  partName: string
  categoryId?: number | null
  spec?: string | null
  brand?: string | null
  unit: string
  isGeneral?: number
  safetyStock?: number | null
  maxStock?: number | null
  shelfLifeDays?: number | null
  trackByItem?: number
  scanEnabled?: number
  remark?: string | null
  status?: number
}

export type PartUpdatePayload = Partial<PartPayload>

/** 配件适配车型（含车型基础信息） */
export interface PartVehicleModel extends AuditFields {
  id: number
  partId: number
  modelId: number
  remark: string | null
  brand?: string | null
  modelName?: string | null
  tonnage?: string | null
  modelStatus?: number | null
}

/** 新增适配车型请求体，partId 取自路径 */
export interface PartVehicleModelPayload {
  modelId: number
  remark?: string | null
}

/** 配件单位换算 */
export interface PartUnitConversion extends AuditFields {
  id: number
  partId: number
  fromUnit: string
  toUnit: string
  rate: number
}

/** 新增单位换算请求体，partId 取自路径 */
export interface PartUnitConversionPayload {
  fromUnit: string
  toUnit: string
  rate: number
}

// ---------------------------------------------------------------- 配件分类

/** 配件分类树，status 不传返回全部（1启用 0停用） */
export function getPartCategoryTree(status?: number) {
  return request.get<PartCategory[]>('/part-categories/tree', {
    params: status === undefined ? undefined : { status }
  })
}

/** 新增配件分类 */
export function createPartCategory(data: PartCategoryPayload) {
  return request.post<PartCategory>('/part-categories', data)
}

/** 编辑配件分类 */
export function updatePartCategory(id: number, data: Partial<PartCategoryPayload>) {
  return request.put<PartCategory>(`/part-categories/${id}`, data)
}

/** 逻辑删除配件分类（存在子分类或已关联配件时后端返回 409） */
export function deletePartCategory(id: number) {
  return request.delete<null>(`/part-categories/${id}`)
}

// ---------------------------------------------------------------- 配件

/** 配件分页列表 */
export function getPartList(params: PartQuery) {
  return request.get<PageResult<Part>>('/parts', { params })
}

/** 配件详情 */
export function getPartDetail(id: number) {
  return request.get<Part>(`/parts/${id}`)
}

/** 新增配件 */
export function createPart(data: PartPayload) {
  return request.post<Part>('/parts', data)
}

/** 编辑配件 */
export function updatePart(id: number, data: PartUpdatePayload) {
  return request.put<Part>(`/parts/${id}`, data)
}

/** 逻辑删除配件 */
export function deletePart(id: number) {
  return request.delete<null>(`/parts/${id}`)
}

// ---------------------------------------------------------------- 适配车型

/** 配件适配车型列表 */
export function getPartModels(partId: number) {
  return request.get<PartVehicleModel[]>(`/parts/${partId}/models`)
}

/** 添加适配车型 */
export function addPartModel(partId: number, data: PartVehicleModelPayload) {
  return request.post<PartVehicleModel>(`/parts/${partId}/models`, data)
}

/** 移除适配车型，modelId 为车型 ID */
export function deletePartModel(partId: number, modelId: number) {
  return request.delete<null>(`/parts/${partId}/models/${modelId}`)
}

// ---------------------------------------------------------------- 单位换算

/** 配件单位换算列表 */
export function getPartUnitConversions(partId: number) {
  return request.get<PartUnitConversion[]>(`/parts/${partId}/units`)
}

/** 新增单位换算 */
export function addPartUnitConversion(partId: number, data: PartUnitConversionPayload) {
  return request.post<PartUnitConversion>(`/parts/${partId}/units`, data)
}

/** 删除单位换算 */
export function deletePartUnitConversion(partId: number, conversionId: number) {
  return request.delete<null>(`/parts/${partId}/units/${conversionId}`)
}
