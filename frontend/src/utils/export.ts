export interface CsvColumn<T> {
  label: string
  value: (row: T) => string | number | null | undefined
}

/** 将数据导出为 CSV（带 UTF-8 BOM，Excel 可直接打开） */
export function downloadCsv<T>(filename: string, columns: CsvColumn<T>[], rows: T[]): void {
  const escapeCell = (value: unknown) => {
    const text = value === null || value === undefined ? '' : String(value)
    return `"${text.replace(/"/g, '""')}"`
  }

  const lines = [
    columns.map((column) => escapeCell(column.label)).join(','),
    ...rows.map((row) => columns.map((column) => escapeCell(column.value(row))).join(','))
  ]

  const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
