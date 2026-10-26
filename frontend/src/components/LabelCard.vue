<template>
  <div class="label">
    <div class="label__header">
      <div class="label__name" :title="partName">{{ partName }}</div>
      <div class="label__spec" :title="item.spec || ''">{{ item.spec || '—' }}</div>
    </div>

    <div class="label__code" :title="item.itemCode">{{ item.itemCode }}</div>

    <div class="label__body">
      <div class="label__meta">
        <div class="label__row">
          <span>批次</span>
          <b :title="item.batchNo || ''">{{ item.batchNo || '—' }}</b>
        </div>
        <div class="label__row">
          <span>库位</span>
          <b :title="item.locationCode || ''">{{ item.locationCode || '—' }}</b>
        </div>
      </div>
      <div class="label__qr">
        <QrCode :value="qrValue" :size="qrSize" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import QrCode from '@/components/QrCode.vue'
import type { LabelItem } from '@/types/label'

/**
 * 单张库存件标签：固定 40mm × 40mm。
 * 屏幕预览、单张预览与打印共用同一份结构，保证所见即所得。
 */
const props = withDefaults(
  defineProps<{
    /** 标签数据 */
    item: LabelItem
    /** 二维码画布边长（px），实际显示尺寸由 CSS 缩放到标签内 */
    qrSize?: number
  }>(),
  { qrSize: 240 }
)

/** 二维码内容缺省时回退到库存件编码 */
const qrValue = computed(() => props.item.qrcode || props.item.itemCode)

/** 配件名称缺省时回退到编码，避免标签顶部空白 */
const partName = computed(() => props.item.partName || props.item.itemCode)
</script>

<style scoped lang="scss">
.label {
  --label-width: 40mm;
  --label-height: 40mm;
  --label-qr: 18mm;

  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  width: var(--label-width);
  height: var(--label-height);
  padding: 2mm;
  overflow: hidden;
  font-size: 8px;
  line-height: 1.2;
  color: #303133;
  background-color: #fff;
  border: 1px dashed #c0c4cc;
  border-radius: 2px;
  break-inside: avoid;
  page-break-inside: avoid;
}

.label__header {
  flex: none;
  padding-bottom: 0.8mm;
}

.label__name {
  overflow: hidden;
  font-size: 1.4em;
  font-weight: 600;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.label__spec {
  overflow: hidden;
  color: #606266;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.label__code {
  flex: none;
  margin-top: 0.8mm;
  padding-bottom: 0.6mm;
  overflow: hidden;
  font-size: 1.1em;
  font-weight: 600;
  letter-spacing: 0.2px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-bottom: 0.2mm solid #dcdfe6;
}

.label__body {
  display: flex;
  flex: 1;
  gap: 1.5mm;
  min-height: 0;
  padding-top: 1mm;
}

.label__meta {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-around;
  min-width: 0;
}

.label__row {
  display: flex;
  flex-direction: column;
  min-width: 0;

  span {
    font-size: 0.95em;
    color: #909399;
  }

  b {
    overflow: hidden;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.label__qr {
  flex: none;
  width: var(--label-qr);
  height: var(--label-qr);

  :deep(canvas) {
    width: 100% !important;
    height: 100% !important;
  }
}
</style>
