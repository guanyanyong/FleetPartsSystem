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
        <el-form-item label="仓库">
          <el-select
            v-model="search.warehouseId"
            placeholder="全部仓库"
            clearable
            filterable
            class="filter-select"
          >
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
            :disabled="!search.warehouseId"
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
        <el-form-item label="低库存">
          <el-switch v-model="search.lowStock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">库存查询</span>
        <span class="table-toolbar__hint">按配件 + 仓库 + 库位汇总的在库数量</span>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column prop="warehouseName" label="仓库" width="120" show-overflow-tooltip />
        <el-table-column label="库位" width="110">
          <template #default="{ row }">{{ row.locationCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="库存数量" width="110" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': isLowStock(row as InventoryDetail) }">{{ formatQuantity(row.quantity) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="件数" width="90" align="right">
          <template #default="{ row }">{{ formatNumber(row.itemCount) }}</template>
        </el-table-column>
        <el-table-column label="锁定数量" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.lockedQty) }}</template>
        </el-table-column>
        <el-table-column label="平均成本" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.avgCost) }}</template>
        </el-table-column>
        <el-table-column label="库存金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(rowAmount(row as InventoryDetail)) }}</template>
        </el-table-column>
        <el-table-column label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ formatQuantity(row.safetyStock) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="isLowStock(row as InventoryDetail)" type="danger" effect="plain">低库存</el-tag>
            <el-tag v-else type="success" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近入库" width="160">
          <template #default="{ row }">{{ formatDate(row.lastInAt) }}</template>
        </el-table-column>
        <el-table-column label="最近出库" width="160">
          <template #default="{ row }">{{ formatDate(row.lastOutAt) }}</template>
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

import { Refresh, Search } from '@element-plus/icons-vue'

import {
  getInventoryList,
  type InventoryDetail,
  type InventoryQuery
} from '@/api/inventory'
import {
  getAllWarehouseLocations,
  getAllWarehouses,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import { formatDate, formatMoney, formatNumber, formatQuantity } from '@/utils/format'

const search = reactive<InventoryQuery>({
  keyword: '',
  warehouseId: undefined,
  locationId: undefined,
  lowStock: false
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<InventoryDetail[]>([])
const warehouses = ref<Warehouse[]>([])
const locations = ref<WarehouseLocation[]>([])
const loading = ref(false)

function isLowStock(row: InventoryDetail) {
  return row.safetyStock !== null && row.quantity < row.safetyStock
}

function rowAmount(row: InventoryDetail) {
  return (Number(row.quantity) || 0) * (Number(row.avgCost) || 0)
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
  try {
    const res = await getInventoryList({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      lowStock: search.lowStock ? true : undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
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
  search.locationId = undefined
  search.lowStock = false
  locations.value = []
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

watch(
  () => search.warehouseId,
  async (id) => {
    search.locationId = undefined
    locations.value = id ? await getAllWarehouseLocations(id).catch(() => []) : []
  }
)

onMounted(async () => {
  await loadWarehouses()
  await loadData()
})
</script>

<style scoped lang="scss">
.text-danger {
  color: var(--el-color-danger);
  font-weight: 600;
}

.table-toolbar__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
