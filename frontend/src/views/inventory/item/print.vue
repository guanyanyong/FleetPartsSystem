<template>
  <div class="page-container label-print-page">
    <el-card class="print-header-card no-print" shadow="never">
      <div class="print-header">
        <div class="print-header__main">
          <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
          <span class="print-header__title">库存件标签打印</span>
          <span class="print-header__sub">共 {{ itemIds.length }} 件 · 标签尺寸 40×40mm</span>
        </div>
        <span class="print-header__tip">点击标签可单张查看/打印，手机浏览器同样适用</span>
      </div>
    </el-card>

    <el-card v-loading="loading" class="print-body-card" shadow="never">
      <el-alert
        v-if="!itemIds.length"
        type="warning"
        :closable="false"
        show-icon
        title="没有需要打印的库存件"
        description="请从入库单详情或库存件列表勾选库存件后进入打印页面。"
      />
      <LabelPrint v-else :items="items" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ArrowLeft } from '@element-plus/icons-vue'

import { getInventoryItemPrintData } from '@/api/inventoryItem'
import LabelPrint from '@/components/LabelPrint.vue'
import type { LabelItem } from '@/types/label'

const route = useRoute()
const router = useRouter()

const items = ref<LabelItem[]>([])
const loading = ref(false)

/** 解析 query：ids（逗号分隔，批量）与 id（单张直达），去重并过滤非法值 */
const itemIds = computed<number[]>(() => {
  const collected: string[] = []
  const push = (value: unknown) => {
    if (Array.isArray(value)) {
      value.forEach(push)
      return
    }
    if (typeof value === 'string' && value.trim()) {
      collected.push(value)
    }
  }
  push(route.query.ids)
  push(route.query.id)

  const ids = collected
    .join(',')
    .split(',')
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0)

  return Array.from(new Set(ids))
})

async function loadPrintData() {
  if (!itemIds.value.length) {
    items.value = []
    return
  }

  loading.value = true
  try {
    items.value = await getInventoryItemPrintData(itemIds.value)
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  void router.push('/inventory/item')
}

/** 支持 ?id= 单张直达：手机端可用链接单独查看/打印某一张标签 */
watch(
  itemIds,
  () => {
    void loadPrintData()
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.label-print-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.print-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;

  &__main {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__sub {
    font-size: 13px;
    color: #909399;
  }

  &__tip {
    font-size: 13px;
    color: #909399;
  }
}

@media (max-width: 767px) {
  .label-print-page {
    gap: 8px;
  }

  .print-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;

    &__main {
      flex-wrap: wrap;
      gap: 8px;
    }

    &__sub,
    &__tip {
      font-size: 12px;
    }
  }

  .print-body-card :deep(.el-card__body) {
    padding: 12px;
  }
}

@media print {
  .print-header-card {
    display: none !important;
  }

  .print-body-card {
    margin: 0;

    :deep(.el-card__body) {
      padding: 0 !important;
    }
  }
}
</style>
