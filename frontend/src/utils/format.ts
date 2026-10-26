import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

dayjs.locale('zh-cn')

export type DateInput = string | number | Date | null | undefined

/**
 * 日期格式化，空值或非法日期统一返回 "-"
 * @example formatDate('2026-10-22T10:00:00') // 2026-10-22 10:00:00
 */
export function formatDate(value: DateInput, pattern = 'YYYY-MM-DD HH:mm:ss'): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const date = dayjs(value)
  return date.isValid() ? date.format(pattern) : '-'
}

/** 仅日期：YYYY-MM-DD */
export function formatDay(value: DateInput): string {
  return formatDate(value, 'YYYY-MM-DD')
}

/**
 * 金额格式化（默认保留两位小数并添加千分位）
 * @param withSymbol 是否带人民币符号，表格中通常为 false
 */
export function formatMoney(value: number | string | null | undefined, withSymbol = false): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const amount = Number(value)
  if (!Number.isFinite(amount)) {
    return '-'
  }
  const text = amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
  return withSymbol ? `¥${text}` : text
}

/** 数字格式化，默认整数展示 */
export function formatNumber(
  value: number | string | null | undefined,
  fractionDigits = 0
): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return '-'
  }
  return number.toLocaleString('zh-CN', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  })
}

/** 数量格式化，默认最多两位小数 */
export function formatQuantity(
  value: number | string | null | undefined,
  fractionDigits = 2
): string {
  return formatNumber(value, fractionDigits)
}
