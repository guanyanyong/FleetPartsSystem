import { computed, ref } from 'vue'

import { defineStore } from 'pinia'

import type { ScanType } from '@/api/outbound'

/**
 * 出库明细行（前端购物车模型）。
 *
 * - 逐件追踪件由扫码添加：`inventoryItemId` 有值，数量固定为 1，单位成本取库存件成本；
 * - 非追踪件由配件选择器添加：`inventoryItemId` 为 null，数量 / 单位成本可编辑。
 */
export interface CartItem {
  /** 行唯一标识，仅前端使用 */
  key: string
  partId: number
  partCode: string
  partName: string
  spec: string | null
  unit: string | null
  quantity: number
  unitCost: number
  inventoryItemId: number | null
  itemCode: string | null
  batchNo: string | null
  locationId: number | null
  locationCode: string | null
  scanCode: string | null
  scanType: ScanType | null
  scanAt: string | null
  remark: string | null
}

/** 添加明细时无需传入行标识 */
export type CartItemInput = Omit<CartItem, 'key'>

let rowSeed = 0

function nextKey(): string {
  rowSeed += 1
  return `cart-${Date.now()}-${rowSeed}`
}

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])

  const totalQuantity = computed(() =>
    items.value.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  )

  const totalAmount = computed(() => {
    const total = items.value.reduce(
      (sum, item) => sum + Number(item.quantity || 0) * Number(item.unitCost || 0),
      0
    )
    return Math.round(total * 100) / 100
  })

  /** 是否已包含指定库存件（逐件追踪件不允许重复出库） */
  function hasInventoryItem(inventoryItemId: number): boolean {
    return items.value.some((item) => item.inventoryItemId === inventoryItemId)
  }

  /** 追加明细；逐件追踪件重复时抛出异常，由页面提示 */
  function addItem(input: CartItemInput): CartItem {
    if (input.inventoryItemId !== null && hasInventoryItem(input.inventoryItemId)) {
      throw new Error(`库存件 ${input.itemCode || input.inventoryItemId} 已在明细中`)
    }
    const item: CartItem = { ...input, key: nextKey() }
    items.value.push(item)
    return item
  }

  /** 按下标删除明细 */
  function removeItem(index: number): void {
    if (index < 0 || index >= items.value.length) {
      return
    }
    items.value.splice(index, 1)
  }

  /** 清空明细（新建出库单 / 保存成功后调用） */
  function clear(): void {
    items.value = []
  }

  return {
    items,
    totalQuantity,
    totalAmount,
    hasInventoryItem,
    addItem,
    removeItem,
    clear
  }
})
