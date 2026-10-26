/**
 * 复制文本到剪贴板。
 *
 * 优先使用 Clipboard API（要求 HTTPS / localhost），
 * 在局域网 http 部署或旧浏览器下自动降级为 textarea + execCommand，
 * 保证「标签预览 → 复制」在车间内网环境同样可用。
 *
 * @returns 是否复制成功
 */
export async function copyText(text: string): Promise<boolean> {
  if (!text) {
    return false
  }

  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 权限被拒绝或浏览器限制时继续走降级方案
    }
  }

  return fallbackCopy(text)
}

/** 降级复制：临时 textarea + document.execCommand('copy') */
function fallbackCopy(text: string): boolean {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '0'
  textarea.style.left = '-9999px'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)

  // 记录原选区，复制完成后还原，避免影响用户当前选中内容
  const selection = document.getSelection()
  const previousRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null

  let succeeded = false
  try {
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    succeeded = document.execCommand('copy')
  } catch {
    succeeded = false
  } finally {
    document.body.removeChild(textarea)
    if (previousRange && selection) {
      selection.removeAllRanges()
      selection.addRange(previousRange)
    }
  }

  return succeeded
}

/**
 * 将一条记录的字段拼成制表符（\t）分隔的一行，便于直接粘贴到 Excel 按列拆分。
 *
 * 字段值里的制表符 / 换行统一替换为空格，避免多出一列或串行。
 */
export function toTsvRow(values: Array<string | number | null | undefined>): string {
  return values
    .map((value) =>
      String(value ?? '')
        .replace(/[\t\r\n]+/g, ' ')
        .trim()
    )
    .join('\t')
}
