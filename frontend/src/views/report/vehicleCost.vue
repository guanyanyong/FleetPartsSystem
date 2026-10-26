<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="车辆">
          <el-select v-model="search.vehicleId" placeholder="全部车辆" clearable filterable class="filter-select">
            <el-option
              v-for="item in vehicles"
              :key="item.id"
              :label="item.plateNo"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="车型">
          <el-select v-model="search.modelId" placeholder="全部车型" clearable filterable class="filter-select">
            <el-option
              v-for="item in models"
              :key="item.id"
              :label="`${item.brand} ${item.modelName}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input
            v-model="search.department"
            placeholder="所属部门"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            value-format="YYYY-MM-DD HH:mm:ss"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            class="date-range"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="summary-card" shadow="never">
      <el-row :gutter="16">
        <el-col :xs="12" :sm="8" :md="4">
          <div class="summary-item">
            <span class="summary-item__label">车辆数</span>
            <span class="summary-item__value">{{ formatNumber(summary.vehicleCount) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <div class="summary-item">
            <span class="summary-item__label">维修次数</span>
            <span class="summary-item__value">{{ formatNumber(summary.repairCount) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <div class="summary-item">
            <span class="summary-item__label">配件成本</span>
            <span class="summary-item__value">{{ formatMoney(summary.totalPartsCost, true) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <div class="summary-item">
            <span class="summary-item__label">工时费</span>
            <span class="summary-item__value">{{ formatMoney(summary.totalLaborCost, true) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <div class="summary-item">
            <span class="summary-item__label">总成本</span>
            <span class="summary-item__value">{{ formatMoney(summary.totalCost, true) }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">单车维修成本</span>
        <span class="table-toolbar__hint">统计已完工 / 已结算工单的配件与工时费用</span>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="vehicleId">
        <el-table-column prop="plateNo" label="车牌号" width="130" />
        <el-table-column label="车型" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.modelName || '-' }}</template>
        </el-table-column>
        <el-table-column label="部门" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>
        <el-table-column label="维修次数" width="100" align="right">
          <template #default="{ row }">{{ formatNumber(row.repairCount) }}</template>
        </el-table-column>
        <el-table-column label="配件成本" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.totalPartsCost) }}</template>
        </el-table-column>
        <el-table-column label="工时费" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.totalLaborCost) }}</template>
        </el-table-column>
        <el-table-column label="总成本" width="140" align="right">
          <template #default="{ row }">
            <span class="total-cost">{{ formatMoney(row.totalCost) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最近维修" width="170">
          <template #default="{ row }">{{ formatDate(row.lastRepairAt) }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无维修成本数据" />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { Refresh, Search } from '@element-plus/icons-vue'

import {
  getVehicleCostReport,
  type VehicleCostReportQuery,
  type VehicleCostReportRow
} from '@/api/report'
import {
  getAllVehicles,
  getVehicleModelOptions,
  type VehicleModelOption,
  type VehicleOption
} from '@/api/vehicle'
import { formatDate, formatMoney, formatNumber } from '@/utils/format'

const search = reactive<VehicleCostReportQuery>({
  vehicleId: undefined,
  modelId: undefined,
  department: '',
  startTime: undefined,
  endTime: undefined
})

const dateRange = ref<[string, string] | null>(null)
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<VehicleCostReportRow[]>([])
const vehicles = ref<VehicleOption[]>([])
const models = ref<VehicleModelOption[]>([])
const loading = ref(false)

const summary = reactive({
  vehicleCount: 0,
  repairCount: 0,
  totalPartsCost: 0,
  totalLaborCost: 0,
  totalCost: 0
})

async function loadOptions() {
  try {
    const [vehicleList, modelList] = await Promise.all([
      getAllVehicles(),
      getVehicleModelOptions()
    ])
    vehicles.value = vehicleList
    models.value = modelList
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  search.startTime = dateRange.value?.[0]
  search.endTime = dateRange.value?.[1]
  try {
    const res = await getVehicleCostReport({
      ...search,
      department: search.department?.trim() || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
    const data = res.data.summary
    summary.vehicleCount = data?.vehicleCount ?? 0
    summary.repairCount = data?.repairCount ?? 0
    summary.totalPartsCost = data?.totalPartsCost ?? 0
    summary.totalLaborCost = data?.totalLaborCost ?? 0
    summary.totalCost = data?.totalCost ?? 0
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  void loadData()
}

function handleReset() {
  search.vehicleId = undefined
  search.modelId = undefined
  search.department = ''
  search.startTime = undefined
  search.endTime = undefined
  dateRange.value = null
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

onMounted(async () => {
  await loadOptions()
  await loadData()
})
</script>

<style scoped lang="scss">
.date-range {
  width: 340px;
}

.summary-card {
  margin-bottom: 12px;

  :deep(.el-card__body) {
    padding: 16px 20px;
  }
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 6px;

  &__label {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  &__value {
    font-size: 20px;
    font-weight: 600;
    color: var(--el-color-primary);
  }
}

.total-cost {
  font-weight: 600;
  color: var(--el-color-danger);
}

.table-toolbar__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
