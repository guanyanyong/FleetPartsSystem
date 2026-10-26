/** 后端分页响应 data 结构，对应 app.schemas.common.PageResult */
export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

/** 可编辑表的审计字段，对应后端 AuditVO */
export interface AuditFields {
  createdBy?: number | null
  createdAt?: string
  updatedBy?: number | null
  updatedAt?: string | null
  isDeleted?: number
}
