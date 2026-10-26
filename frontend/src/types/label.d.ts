/**
 * 标签打印数据。
 * 入库单「待打印库存件」与库存件「批量打印」接口返回结构一致，
 * 统一在此定义，供 API、LabelPrint 组件与打印页复用。
 */
export interface LabelItem {
  /** 库存件ID（用于跳转打印页） */
  id?: number | null
  /** 库存件编码 */
  itemCode: string
  /** 配件名称 */
  partName: string
  /** 规格型号 */
  spec?: string | null
  /** 批次号 */
  batchNo?: string | null
  /** 二维码内容，缺省时使用 itemCode */
  qrcode?: string | null
  /** 库位编码 */
  locationCode?: string | null
}

/**
 * 标签物理尺寸固定为 40mm × 40mm（正方形标签纸）。
 * 具体尺寸在 `LabelCard.vue` 的 `--label-width / --label-height` 中定义，
 * 打印时的 `@page` 尺寸由 `LabelPrint.vue` 根据纸张类型动态注入。
 */

