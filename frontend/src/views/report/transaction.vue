<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="配件编码 / 名称 / 单号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="仓库">
          <el-select v-model="search.warehouseId" placeholder="全部仓库" clearable class="filter-select">
            <el-option
              v-for="item in warehouses"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="search.bizType" placeholder="全部" clearable class="filter-select">
            <el-option
              v-for="(item, key) in BIZ_TYPE_MAP"
              :key="key"
              :label="item.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="单据类型">
          <el-select v-model="search.refType" placeholder="全部" clearable class="filter-select">
            <el-option
              v-for="(label, key) in REF_TYPE_MAP"
              :key="key"
              :label="label"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="单据号">
          <el-input v-model="search.refNo" placeholder="关联单号" clearable @keyup.enter="handleSearch" />
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
      <el-row :gutter="12">
        <el-col v-for="item in summaryItems" :key="item.label" :xs="12" :sm="8" :md="3">
          <div class="summary-item">
            <span class="summary-item__label">{{ item.label }}</span>
            <span class="summary-item__value">{{ formatQuantity(item.value) }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">库存流水</span>
        <span class="table-toolbar__hint">记录每一次库存变动的前后数量</span>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column label="发生时间" width="160">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="warehouseName" label="仓库" width="110" show-overflow-tooltip />
        <el-table-column label="库位" width="100">
          <template #default="{ row }">{{ row.locationCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="业务类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="bizTypeOf(row.bizType).type" effect="plain">
              {{ bizTypeOf(row.bizType).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="变动数量" width="110" align="right">
          <template #default="{ row }">
            <span :class="Number(row.changeQty) >= 0 ? 'text-increase' : 'text-decrease'">
              {{ Number(row.changeQty) > 0 ? '+' : '' }}{{ formatQuantity(row.changeQty) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="变动前" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.beforeQty) }}</template>
        </el-table-column>
        <el-table-column label="变动后" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.afterQty) }}</template>
        </el-table-column>
        <el-table-column label="单位成本" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.unitCost) }}</template>
        </el-table-column>
        <el-table-column label="单据" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.refNo">{{ REF_TYPE_MAP[(row as TransactionReportRow).refType] || row.refType }} / {{ row.refNo }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="批号" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.batchNo || '-' }}</template>
        </el-table-column>
        <el-table-column label="扫码编码" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.scanCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作人" width="90" align="center">
          <template #default="{ row }">{{ row.operatorId ?? '-' }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无流水记录" />
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
import { computed, onMounted, reactive, ref } from 'vue'

import { Refresh, Search } from '@element-plus/icons-vue'

import {
  getTransactionReport,
  type BizType,
  type RefType,
  type TransactionReportQuery,
  type TransactionReportRow
} from '@/api/report'
import { getAllWarehouses, type Warehouse } from '@/api/warehouse'
import { formatDate, formatMoney, formatQuantity } from '@/utils/format'

type TagType = 'success' | 'danger' | 'primary' | 'warning'

const BIZ_TYPE_MAP: Record<BizType, { label: string; type: TagType }> = {
  IN: { label: '入库', type: 'success' },
  OUT: { label: '出库', type: 'danger' },
  TRANSFER_IN: { label: '调拨入', type: 'primary' },
  TRANSFER_OUT: { label: '调拨出', type: 'warning' },
  ADJUST_IN: { label: '盘盈', type: 'success' },
  ADJUST_OUT: { label: '盘亏', type: 'danger' }
}

const REF_TYPE_MAP: Record<RefType, string> = {
  INBOUND: '入库单',
  OUTBOUND: '出库单',
  TRANSFER: '调拨单',
  STOCKTAKE: '盘点单'
}

const search = reactive<TransactionReportQuery>({
  keyword: '',
  warehouseId: undefined,
  bizType: undefined,
  refType: undefined,
  refNo: '',
  startTime: undefined,
  endTime: undefined
})

const dateRange = ref<[string, string] | null>(null)
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<TransactionReportRow[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)

const summary = reactive({
  inQty: 0,
  outQty: 0,
  transferInQty: 0,
  transferOutQty: 0,
  adjustInQty: 0,
  adjustOutQty: 0,
  netQty: 0
})

const summaryItems = computed(() => [
  { label: '入库', value: summary.inQty },
  { label: '出库', value: summary.outQty },
  { label: '调拨入', value: summary.transferInQty },
  { label: '调拨出', value: summary.transferOutQty },
  { label: '盘盈', value: summary.adjustInQty },
  { label: '盘亏', value: summary.adjustOutQty },
  { label: '净变动', value: summary.netQty }
])

function bizTypeOf(type: BizType) {
  return BIZ_TYPE_MAP[type] ?? { label: type, type: 'primary' as TagType }
}

async function loadWarehouses() {
  try {
    warehouses.value = await getAllWarehouses(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  search.startTime = dateRange.value?.[0]
  search.endTime = dateRange.value?.[1]
  try {
    const res = await getTransactionReport({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      refNo: search.refNo?.trim() || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
    const data = res.data.summary
    summary.inQty = data?.inQty ?? 0
    summary.outQty = data?.outQty ?? 0
    summary.transferInQty = data?.transferInQty ?? 0
    summary.transferOutQty = data?.transferOutQty ?? 0
    summary.adjustInQty = data?.adjustInQty ?? 0
    summary.adjustOutQty = data?.adjustOutQty ?? 0
    summary.netQty = data?.netQty ?? 0
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
  search.keyword = ''
  search.warehouseId = undefined
  search.bizType = undefined
  search.refType = undefined
  search.refNo = ''
  dateRange.value = null
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

onMounted(async () => {
  await loadWarehouses()
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

.text-increase {
  color: var(--el-color-success);
  font-weight: 600;
}

.text-decrease {
  color: var(--el-color-danger);
  font-weight: 600;
}

.table-toolbar__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
