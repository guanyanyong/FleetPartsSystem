<template>
  <div class="page-container dashboard">
    <div class="dashboard__header">
      <div>
        <h2 class="dashboard__title">首页看板</h2>
        <p class="dashboard__subtitle">
          {{ source === 'report' ? '数据来自报表聚合接口' : '报表接口暂不可用，数据由基础列表接口汇总' }}
        </p>
      </div>
      <div class="dashboard__actions">
        <el-tag v-if="source === 'fallback'" type="warning" effect="plain">降级模式</el-tag>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
      </div>
    </div>

    <el-row v-loading="loading" :gutter="12" class="stat-row">
      <el-col v-for="item in statCards" :key="item.key" :xs="12" :sm="8" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card__body">
            <div class="stat-card__icon" :style="{ color: item.color, background: item.bg }">
              <el-icon :size="22"><component :is="item.icon" /></el-icon>
            </div>
            <div class="stat-card__content">
              <span class="stat-card__label">{{ item.label }}</span>
              <span class="stat-card__value">{{ item.value }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12" class="chart-row">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-card__header">
              <span>待处理事项分布</span>
              <span class="panel-card__hint">共 {{ pendingTotal }} 项</span>
            </div>
          </template>
          <ChartPanel
            :option="pendingOption"
            :empty="pendingTotal === 0"
            empty-text="暂无待处理事项"
            height="300px"
          />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-card__header">
              <span>基础数据概览</span>
              <span class="panel-card__hint">配件 / 车辆 / 仓库 / 低库存</span>
            </div>
          </template>
          <ChartPanel :option="baseOption" height="300px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { Component } from 'vue'

import {
  Box,
  Money,
  OfficeBuilding,
  Refresh,
  Tickets,
  Tools,
  TrendCharts,
  Van,
  Warning
} from '@element-plus/icons-vue'
import type { EChartsOption } from 'echarts'

import { getInboundOrderList } from '@/api/inbound'
import { getInventoryList } from '@/api/inventory'
import { getOutboundOrderList } from '@/api/outbound'
import { getPartList } from '@/api/part'
import { getDashboardData, type DashboardData } from '@/api/report'
import { getVehicleList } from '@/api/vehicle'
import { getWarehouseList } from '@/api/warehouse'
import { getWorkOrderList } from '@/api/workOrder'
import ChartPanel from '@/components/ChartPanel.vue'
import { formatMoney, formatNumber } from '@/utils/format'

interface StatCard {
  key: string
  label: string
  value: string
  icon: Component
  color: string
  bg: string
}

const loading = ref(false)
const source = ref<'report' | 'fallback'>('report')

const data = reactive<DashboardData>({
  partCount: 0,
  vehicleCount: 0,
  warehouseCount: 0,
  inventoryQuantity: 0,
  inventoryAmount: 0,
  lowStockCount: 0,
  pendingInboundCount: 0,
  pendingOutboundCount: 0,
  repairingWorkOrderCount: 0,
  monthInboundAmount: 0,
  monthOutboundAmount: 0
})

const statCards = computed<StatCard[]>(() => [
  {
    key: 'part',
    label: '配件种类',
    value: formatNumber(data.partCount),
    icon: Box,
    color: '#409eff',
    bg: 'rgba(64, 158, 255, 0.12)'
  },
  {
    key: 'vehicle',
    label: '在册车辆',
    value: formatNumber(data.vehicleCount),
    icon: Van,
    color: '#67c23a',
    bg: 'rgba(103, 194, 58, 0.12)'
  },
  {
    key: 'warehouse',
    label: '仓库数量',
    value: formatNumber(data.warehouseCount),
    icon: OfficeBuilding,
    color: '#909399',
    bg: 'rgba(144, 147, 153, 0.12)'
  },
  {
    key: 'quantity',
    label: '库存总量',
    value: formatNumber(data.inventoryQuantity),
    icon: TrendCharts,
    color: '#6f42c1',
    bg: 'rgba(111, 66, 193, 0.12)'
  },
  {
    key: 'amount',
    label: '库存金额',
    value: formatMoney(data.inventoryAmount, true),
    icon: Money,
    color: '#e6a23c',
    bg: 'rgba(230, 162, 60, 0.12)'
  },
  {
    key: 'lowStock',
    label: '低库存配件',
    value: formatNumber(data.lowStockCount),
    icon: Warning,
    color: '#f56c6c',
    bg: 'rgba(245, 108, 108, 0.12)'
  },
  {
    key: 'inbound',
    label: '待审入库单',
    value: formatNumber(data.pendingInboundCount),
    icon: Tickets,
    color: '#409eff',
    bg: 'rgba(64, 158, 255, 0.12)'
  },
  {
    key: 'outbound',
    label: '待审出库单',
    value: formatNumber(data.pendingOutboundCount),
    icon: Tickets,
    color: '#e6a23c',
    bg: 'rgba(230, 162, 60, 0.12)'
  },
  {
    key: 'workOrder',
    label: '维修中工单',
    value: formatNumber(data.repairingWorkOrderCount),
    icon: Tools,
    color: '#f56c6c',
    bg: 'rgba(245, 108, 108, 0.12)'
  },
  {
    key: 'monthIn',
    label: '本月入库金额',
    value: formatMoney(data.monthInboundAmount, true),
    icon: TrendCharts,
    color: '#67c23a',
    bg: 'rgba(103, 194, 58, 0.12)'
  },
  {
    key: 'monthOut',
    label: '本月出库金额',
    value: formatMoney(data.monthOutboundAmount, true),
    icon: TrendCharts,
    color: '#f56c6c',
    bg: 'rgba(245, 108, 108, 0.12)'
  }
])

const pendingTotal = computed(
  () => data.pendingInboundCount + data.pendingOutboundCount + data.repairingWorkOrderCount
)

const pendingOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, itemWidth: 12, itemHeight: 12 },
  color: ['#409eff', '#e6a23c', '#f56c6c'],
  series: [
    {
      name: '待处理',
      type: 'pie',
      radius: ['45%', '68%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{c}' },
      data: [
        { name: '待审入库单', value: data.pendingInboundCount },
        { name: '待审出库单', value: data.pendingOutboundCount },
        { name: '维修中工单', value: data.repairingWorkOrderCount }
      ]
    }
  ]
}))

const baseOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 16, right: 24, top: 24, bottom: 8, containLabel: true },
  xAxis: {
    type: 'category',
    data: ['配件种类', '在册车辆', '仓库数量', '低库存配件'],
    axisTick: { alignWithLabel: true }
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      name: '数量',
      type: 'bar',
      barWidth: '45%',
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      data: [
        { value: data.partCount, itemStyle: { color: '#409eff' } },
        { value: data.vehicleCount, itemStyle: { color: '#67c23a' } },
        { value: data.warehouseCount, itemStyle: { color: '#909399' } },
        { value: data.lowStockCount, itemStyle: { color: '#f56c6c' } }
      ]
    }
  ]
}))

/** 报表接口不可用时，分页汇总现有库存数据（最多 25 页，避免无限拉取） */
async function summarizeInventory() {
  let quantity = 0
  let amount = 0
  let page = 1
  const pageSize = 200

  while (page <= 25) {
    const res = await getInventoryList({ page, pageSize })
    const { list, total } = res.data
    for (const row of list) {
      quantity += Number(row.quantity) || 0
      amount += (Number(row.quantity) || 0) * (Number(row.avgCost) || 0)
    }
    if (list.length < pageSize || page * pageSize >= total) {
      break
    }
    page += 1
  }

  return { quantity, amount }
}

async function loadFallback() {
  const [partRes, vehicleRes, warehouseRes, inboundRes, outboundRes, workOrderRes, inventory] =
    await Promise.all([
      getPartList({ page: 1, pageSize: 1 }).catch(() => null),
      getVehicleList({ page: 1, pageSize: 1 }).catch(() => null),
      getWarehouseList({ page: 1, pageSize: 1 }).catch(() => null),
      getInboundOrderList({ page: 1, pageSize: 1, status: 2 }).catch(() => null),
      getOutboundOrderList({ page: 1, pageSize: 1, status: 2 }).catch(() => null),
      getWorkOrderList({ page: 1, pageSize: 1, status: 2 }).catch(() => null),
      summarizeInventory().catch(() => ({ quantity: 0, amount: 0 }))
    ])

  data.partCount = partRes?.data.total ?? 0
  data.vehicleCount = vehicleRes?.data.total ?? 0
  data.warehouseCount = warehouseRes?.data.total ?? 0
  data.pendingInboundCount = inboundRes?.data.total ?? 0
  data.pendingOutboundCount = outboundRes?.data.total ?? 0
  data.repairingWorkOrderCount = workOrderRes?.data.total ?? 0
  data.inventoryQuantity = inventory.quantity
  data.inventoryAmount = inventory.amount
  data.lowStockCount = 0
  data.monthInboundAmount = 0
  data.monthOutboundAmount = 0

  // 低库存数量从库存汇总接口获取
  const lowStock = await getInventoryList({ page: 1, pageSize: 1, lowStock: true }).catch(() => null)
  data.lowStockCount = lowStock?.data.total ?? 0
}

async function loadData() {
  loading.value = true
  try {
    const res = await getDashboardData()
    Object.assign(data, res.data)
    source.value = 'report'
  } catch {
    source.value = 'fallback'
    await loadFallback()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped lang="scss">
.dashboard {
  &__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  &__title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__subtitle {
    margin: 4px 0 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.stat-row {
  margin-bottom: 4px;
}

.stat-card {
  margin-bottom: 12px;

  :deep(.el-card__body) {
    padding: 16px;
  }

  &__body {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    flex-shrink: 0;
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  &__label {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  &__value {
    font-size: 20px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.chart-row {
  .panel-card {
    margin-bottom: 12px;

    &__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-weight: 600;
    }

    &__hint {
      font-size: 12px;
      font-weight: 400;
      color: var(--el-text-color-secondary);
    }
  }
}
</style>


