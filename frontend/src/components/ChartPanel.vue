<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'

import { echarts, type EChartsType } from '@/utils/echarts'

const props = withDefaults(
  defineProps<{
    /** ECharts 配置项，变化时自动 setOption */
    option: EChartsOption
    /** 图表高度 */
    height?: string
    /** 无数据时的占位文案 */
    emptyText?: string
    /** 是否显示无数据占位（由父组件根据数据判断） */
    empty?: boolean
  }>(),
  {
    height: '320px',
    emptyText: '暂无数据',
    empty: false
  }
)

const chartRef = ref<HTMLDivElement | null>(null)
let chart: EChartsType | null = null
let observer: ResizeObserver | null = null

function render(): void {
  if (!chartRef.value || props.empty) {
    return
  }
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  chart.setOption(props.option, true)
}

function resize(): void {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  render()
  if (chartRef.value) {
    observer = new ResizeObserver(resize)
    observer.observe(chartRef.value)
  }
})

watch(
  () => props.option,
  async () => {
    await nextTick()
    render()
  },
  { deep: true }
)

watch(
  () => props.empty,
  async (empty) => {
    if (empty) {
      chart?.clear()
      return
    }
    await nextTick()
    render()
  }
)

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  chart?.dispose()
  chart = null
})

defineExpose({ resize, render })
</script>

<template>
  <div class="chart-panel" :style="{ height }">
    <div v-show="!empty" ref="chartRef" class="chart-panel__canvas" />
    <el-empty v-if="empty" :description="emptyText" :image-size="80" />
  </div>
</template>

<style scoped lang="scss">
.chart-panel {
  position: relative;
  width: 100%;

  &__canvas {
    width: 100%;
    height: 100%;
  }
}
</style>
