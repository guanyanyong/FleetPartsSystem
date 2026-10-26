<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="配件编码 / 名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="配件分类">
          <el-select
            v-model="search.categoryId"
            placeholder="全部分类"
            clearable
            filterable
            class="filter-select"
          >
            <el-option
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
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
        <el-form-item label="库位">
          <el-select
            v-model="search.locationId"
            placeholder="全部库位"
            clearable
            filterable
            class="filter-select"
          >
            <el-option
              v-for="item in locations"
              :key="item.id"
              :label="item.locationCode"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="低于安全库存">
          <el-switch v-model="search.lowStock" />
        </el-form-item>
        <el-form-item label="包含零库存">
          <el-switch v-model="search.includeZero" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="summary-card" shadow="never">
      <el-row :gutter="16">
        <el-col :xs="12" :sm="6">
          <div class="summary-item">
            <span class="summary-item__label">配件种类</span>
            <span class="summary-item__value">{{ formatNumber(summary.partKinds) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item">
            <span class="summary-item__label">库存总量</span>
            <span class="summary-item__value">{{ formatQuantity(summary.totalQuantity) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item">
            <span class="summary-item__label">库存金额</span>
            <span class="summary-item__value">{{ formatMoney(summary.totalAmount, true) }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item">
            <span class="summary-item__label">低库存项</span>
            <span class="summary-item__value summary-item__value--danger">
              {{ formatNumber(summary.lowStockCount) }}
            </span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">库存报表</span>
        <span class="table-toolbar__hint">按配件 + 仓库 + 库位维度汇总</span>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe :row-key="rowKey">
        <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="分类" width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.categoryName || '-' }}</template>
        </el-table-column>
        <el-table-column prop="warehouseName" label="仓库" width="120" show-overflow-tooltip />
        <el-table-column label="库位" width="110">
          <template #default="{ row }">{{ row.locationCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="库存数量" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': isLowStock(row as InventoryReportRow) }">{{ formatQuantity(row.quantity) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="锁定数量" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.lockedQty) }}</template>
        </el-table-column>
        <el-table-column label="平均成本" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.avgCost) }}</template>
        </el-table-column>
        <el-table-column label="库存金额" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.safetyStock) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="isLowStock(row as InventoryReportRow)" type="danger" effect="plain">低库存</el-tag>
            <el-tag v-else type="success" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无库存数据" />
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
import { onMounted, reactive, ref, watch } from 'vue'

import { Download, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { getPartCategoryTree, type PartCategory } from '@/api/part'
import {
  exportInventoryReport,
  getInventoryReport,
  type InventoryReportQuery,
  type InventoryReportRow
} from '@/api/report'
import {
  getAllWarehouseLocations,
  getAllWarehouses,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import {
  formatDate,
  formatMoney,
  formatNumber,
  formatQuantity
} from '@/utils/format'

interface CategoryOption {
  id: number
  label: string
}

const search = reactive<InventoryReportQuery>({
  keyword: '',
  categoryId: undefined,
  warehouseId: undefined,
  locationId: undefined,
  lowStock: false,
  includeZero: false
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<InventoryReportRow[]>([])
const warehouses = ref<Warehouse[]>([])
const locations = ref<WarehouseLocation[]>([])
const categoryOptions = ref<CategoryOption[]>([])
const loading = ref(false)
const exporting = ref(false)

const summary = reactive({
  partKinds: 0,
  totalQuantity: 0,
  totalAmount: 0,
  lowStockCount: 0
})

function flattenCategories(nodes: PartCategory[], depth = 0): CategoryOption[] {
  return nodes.flatMap((node) => [
    { id: node.id, label: `${'　'.repeat(depth)}${node.name}` },
    ...flattenCategories(node.children ?? [], depth + 1)
  ])
}

function rowKey(row: InventoryReportRow) {
  return `${row.partId}-${row.warehouseId}-${row.locationId ?? 0}`
}

function isLowStock(row: InventoryReportRow) {
  // 与后端保持一致：可用数量（库存 - 锁定）低于安全库存才算低库存
  return (
    row.safetyStock !== null &&
    row.safetyStock > 0 &&
    row.quantity - row.lockedQty < row.safetyStock
  )
}

async function loadOptions() {
  try {
    const [warehouseList, categoryTree] = await Promise.all([
      getAllWarehouses(1),
      getPartCategoryTree(1)
    ])
    warehouses.value = warehouseList
    categoryOptions.value = flattenCategories(categoryTree.data)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getInventoryReport({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      lowStock: search.lowStock ? true : undefined,
      includeZero: search.includeZero ? true : undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
    const data = res.data.summary
    summary.partKinds = data?.partKinds ?? 0
    summary.totalQuantity = data?.totalQuantity ?? 0
    summary.totalAmount = data?.totalAmount ?? 0
    summary.lowStockCount = data?.lowStockCount ?? 0
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
  search.categoryId = undefined
  search.warehouseId = undefined
  search.locationId = undefined
  search.lowStock = false
  search.includeZero = false
  locations.value = []
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportInventoryReport({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      lowStock: search.lowStock ? true : undefined,
      includeZero: search.includeZero ? true : undefined
    })
    downloadBlob(blob, `库存报表_${formatDate(new Date(), 'YYYYMMDDHHmmss')}.xlsx`)
    ElMessage.success('导出成功')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    exporting.value = false
  }
}

watch(
  () => search.warehouseId,
  async (id) => {
    search.locationId = undefined
    locations.value = id ? await getAllWarehouseLocations(id).catch(() => []) : []
  }
)

onMounted(async () => {
  await loadOptions()
  await loadData()
})
</script>

<style scoped lang="scss">
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
    font-size: 22px;
    font-weight: 600;
    color: var(--el-color-primary);

    &--danger {
      color: var(--el-color-danger);
    }
  }
}

.text-danger {
  color: var(--el-color-danger);
  font-weight: 600;
}

.table-toolbar__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
