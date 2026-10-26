<template>
  <div v-loading="loading" class="page-container stocktake-detail">
    <el-card class="filter-card" shadow="never">
      <div class="detail-header">
        <div class="detail-header__main">
          <el-button :icon="ArrowLeft" link @click="goBack">返回</el-button>
          <span class="detail-header__no">{{ order?.orderNo || '-' }}</span>
          <el-tag v-if="order" :type="statusOf(order.status).type" effect="plain">
            {{ statusOf(order.status).label }}
          </el-tag>
        </div>
        <div class="detail-header__actions">
          <el-button v-if="order?.status === 1" type="success" @click="handleStart">
            开始盘点
          </el-button>
          <el-button
            v-if="order?.status === 2"
            type="primary"
            :loading="finishing"
            @click="handleFinish"
          >
            完成盘点
          </el-button>
          <el-button
            v-if="order && (order.status === 1 || order.status === 2)"
            type="danger"
            plain
            @click="handleCancel"
          >
            作废
          </el-button>
        </div>
      </div>

      <el-descriptions v-if="order" :column="4" border class="detail-desc">
        <el-descriptions-item label="盘点仓库">
          {{ order.warehouseName || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="盘点人">
          {{ order.operatorId ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="盘点时间">
          {{ formatDate(order.stocktakeAt) }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(order.createdAt) }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="4">
          {{ order.remark || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">明细总数</span>
          <span class="stat-card__value">{{ summary.total }}</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">已盘</span>
          <span class="stat-card__value text-success">{{ summary.scanned }}</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">未盘</span>
          <span class="stat-card__value text-warning">{{ summary.pending }}</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">差异条目</span>
          <span class="stat-card__value text-danger">{{ summary.diffCount }}</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">盘盈数量</span>
          <span class="stat-card__value text-success">{{ formatQuantity(summary.gainQty) }}</span>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="8" :md="4">
        <el-card shadow="never" class="stat-card">
          <span class="stat-card__label">盘亏数量</span>
          <span class="stat-card__value text-danger">{{ formatQuantity(summary.lossQty) }}</span>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="order?.status === 2" class="table-card scan-card" shadow="never">
      <div class="scan-card__title">扫码盘点</div>
      <div class="scan-card__body">
        <ScanInput
          :disabled="scanning"
          placeholder="扫描库存件二维码 / 输入 item_code 后回车"
          @scan="handleScan"
        />
        <el-select
          v-model="scanLocationId"
          placeholder="当前库位（选填）"
          clearable
          filterable
          class="scan-card__location"
        >
          <el-option
            v-for="item in locations"
            :key="item.id"
            :label="item.locationCode"
            :value="item.id"
          />
        </el-select>
      </div>
      <div class="scan-card__tip">
        扫到库存件后自动标记为「已盘」；数量追踪类配件请在下表手工录入实盘数量。
      </div>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">盘点明细</span>
        <div class="table-toolbar__actions">
          <el-radio-group v-model="scope" size="small" @change="handleScopeChange">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="pending">未盘</el-radio-button>
            <el-radio-button value="diff">有差异</el-radio-button>
          </el-radio-group>
          <el-input
            v-model="keyword"
            placeholder="配件编码 / 名称 / 库存件编码"
            clearable
            class="table-toolbar__search"
          />
        </div>
      </div>

      <el-table
        :data="filteredItems"
        border
        stripe
        row-key="id"
        :row-class-name="rowClassName"
        max-height="620"
      >
        <el-table-column label="库位" width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.locationCode || '-' }}</template>
        </el-table-column>
        <el-table-column prop="partCode" label="配件编码" width="140" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="库存件编码" width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.itemCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="账面数量" width="110" align="right">
          <template #default="{ row }">{{ formatQuantity(row.bookQty) }}</template>
        </el-table-column>
        <el-table-column label="实盘数量" width="170" align="center">
          <template #default="{ row }">
            <el-input-number
              v-if="order?.status === 2"
              :model-value="row.actualQty"
              :min="0"
              :precision="2"
              :controls="false"
              :disabled="savingId === row.id"
              size="small"
              class="actual-input"
              @update:model-value="(value: number | undefined) => handleActualInput(row as StocktakeOrderItem, value)"
            />
            <span v-else>{{ formatQuantity(row.actualQty) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="差异" width="110" align="right">
          <template #default="{ row }">
            <span :class="diffClass(row as StocktakeOrderItem)">{{ formatDiff(diffOf(row as StocktakeOrderItem)) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="盘点状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="isScanned(row as StocktakeOrderItem) ? 'success' : 'info'" effect="plain" size="small">
              {{ isScanned(row as StocktakeOrderItem) ? '已盘' : '未盘' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="单位" width="70" align="center">
          <template #default="{ row }">{{ row.unit || '-' }}</template>
        </el-table-column>
        <el-table-column label="扫码记录" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.scanCode || '-' }}</template>
        </el-table-column>
        <template #empty>
          <el-empty :description="items.length ? '没有符合筛选条件的明细' : '盘点单暂无明细'" />
        </template>
      </el-table>

      <div v-if="order && order.status !== 2" class="detail-tip">
        <el-alert
          :type="order.status === 3 ? 'success' : 'info'"
          :closable="false"
          show-icon
          :title="
            order.status === 3
              ? '盘点已完成，盘盈盘亏已写入库存流水'
              : '盘点单未处于盘点中状态，明细只读'
          "
        />
      </div>
    </el-card>
  </div>
</template>



<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import ScanInput from '@/components/ScanInput.vue'
import {
  cancelStocktakeOrder,
  finishStocktakeOrder,
  getStocktakeOrderDetail,
  scanStocktakeItem,
  startStocktakeOrder,
  updateStocktakeItem,
  type StocktakeOrderDetail,
  type StocktakeOrderItem
} from '@/api/stocktake'
import { getAllWarehouseLocations, type WarehouseLocation } from '@/api/warehouse'
import { formatDate, formatQuantity } from '@/utils/format'

const route = useRoute()
const router = useRouter()

type TagType = 'info' | 'primary' | 'success' | 'danger'
type ScopeType = 'all' | 'pending' | 'diff'

const STATUS_MAP: Record<number, { label: string; type: TagType }> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '盘点中', type: 'primary' },
  3: { label: '已完成', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const orderId = Number(route.params.id)
const order = ref<StocktakeOrderDetail | null>(null)
const items = computed<StocktakeOrderItem[]>(() => order.value?.items ?? [])
const loading = ref(false)
const scanning = ref(false)
const finishing = ref(false)
const savingId = ref<number | null>(null)
const scanLocationId = ref<number | undefined>()
const locations = ref<WarehouseLocation[]>([])

const scope = ref<ScopeType>('all')
const keyword = ref('')

function statusOf(status: number) {
  return STATUS_MAP[status] ?? { label: '未知', type: 'info' as TagType }
}

function isScanned(row: StocktakeOrderItem): boolean {
  if (row.actualQty === null || row.actualQty === undefined) {
    return false
  }
  // 逐件追踪的实例：初始实盘数为 0，扫码 / 手工确认后 >= 1
  if (order.value?.status === 2 && row.inventoryItemId !== null) {
    return Number(row.actualQty) >= 1 || !!row.scanCode
  }
  return true
}

/** 差异数量：未盘行不显示差异，避免把「未盘」误读为盘亏 */
function diffOf(row: StocktakeOrderItem): number | null {
  if (!isScanned(row)) {
    return null
  }
  const actual = Number(row.actualQty ?? 0)
  const book = Number(row.bookQty ?? 0)
  return Number((actual - book).toFixed(2))
}

function formatDiff(value: number | null): string {
  if (value === null) {
    return '-'
  }
  if (value === 0) {
    return '0'
  }
  return value > 0 ? `+${formatQuantity(value)}` : formatQuantity(value)
}

function diffClass(row: StocktakeOrderItem): string {
  const diff = diffOf(row)
  if (diff === null || diff === 0) {
    return ''
  }
  return diff > 0 ? 'text-success' : 'text-danger'
}

function rowClassName({ row }: { row: StocktakeOrderItem }): string {
  const diff = diffOf(row)
  if (diff === null || diff === 0) {
    return ''
  }
  return diff > 0 ? 'row-gain' : 'row-loss'
}

const filteredItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return items.value.filter((row) => {
    if (scope.value === 'pending' && isScanned(row)) {
      return false
    }
    if (scope.value === 'diff' && !diffOf(row)) {
      return false
    }
    if (!text) {
      return true
    }
    return [row.partCode, row.partName, row.itemCode, row.locationCode]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(text))
  })
})

const summary = computed(() => {
  const list = items.value
  const scanned = list.filter((row) => isScanned(row)).length
  const diffs = list
    .map((row) => diffOf(row))
    .filter((value): value is number => value !== null && value !== 0)

  return {
    total: list.length,
    scanned,
    pending: list.length - scanned,
    diffCount: diffs.length,
    gainQty: diffs.filter((value) => value > 0).reduce((sum, value) => sum + value, 0),
    lossQty: Math.abs(diffs.filter((value) => value < 0).reduce((sum, value) => sum + value, 0))
  }
})

async function loadDetail() {
  loading.value = true
  try {
    const res = await getStocktakeOrderDetail(orderId)
    order.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function loadLocations() {
  if (!order.value?.warehouseId) {
    return
  }
  try {
    locations.value = await getAllWarehouseLocations(order.value.warehouseId)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleScan(code: string) {
  if (!order.value || order.value.status !== 2) {
    return
  }
  scanning.value = true
  try {
    const res = await scanStocktakeItem(orderId, code, scanLocationId.value)
    const item = res.data
    ElMessage.success(`已盘点：${item.partName || item.partCode || code}`)
    await loadDetail()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    scanning.value = false
  }
}

async function handleActualInput(row: StocktakeOrderItem, value: number | undefined) {
  if (value === undefined || value === null || !Number.isFinite(Number(value))) {
    return
  }
  if (Number(row.actualQty) === Number(value)) {
    return
  }
  savingId.value = row.id
  try {
    await updateStocktakeItem(orderId, row.id, {
      actualQty: Number(value),
      remark: row.remark
    })
    await loadDetail()
  } catch {
    await loadDetail()
  } finally {
    savingId.value = null
  }
}

function handleScopeChange() {
  // 本地筛选，无需请求
}

function goBack() {
  void router.push('/stocktake')
}

async function handleStart() {
  try {
    await startStocktakeOrder(orderId)
    ElMessage.success('已开始盘点')
    await loadDetail()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleFinish() {
  try {
    await ElMessageBox.confirm(
      summary.value.diffCount
        ? `当前有 ${summary.value.diffCount} 条差异，完成后将生成盘盈盘亏流水，确定继续吗？`
        : '所有明细无差异，确定完成盘点吗？',
      '完成盘点',
      { type: 'warning' }
    )
    finishing.value = true
    await finishStocktakeOrder(orderId)
    ElMessage.success('盘点已完成')
    await loadDetail()
  } catch {
    // 取消操作或接口错误
  } finally {
    finishing.value = false
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('确定作废该盘点单吗？', '作废确认', { type: 'warning' })
    await cancelStocktakeOrder(orderId)
    ElMessage.success('已作废')
    await loadDetail()
  } catch {
    // 取消操作或接口错误
  }
}

onMounted(async () => {
  if (!Number.isFinite(orderId)) {
    ElMessage.error('盘点单ID无效')
    goBack()
    return
  }
  await loadDetail()
  await loadLocations()
})
</script>


<style scoped lang="scss">
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;

  &__main {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__no {
    font-size: 18px;
    font-weight: 600;
  }

  &__actions {
    display: flex;
    gap: 8px;
  }
}

.detail-desc {
  margin-top: 16px;
}

.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 14px 16px;
  }

  &__label {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  &__value {
    font-size: 22px;
    font-weight: 600;
  }
}

.scan-card {
  margin-bottom: 16px;

  &__title {
    font-weight: 600;
    margin-bottom: 12px;
  }

  &__body {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  &__location {
    width: 200px;
    flex: none;
  }

  &__tip {
    margin-top: 8px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }
}

.table-toolbar__search {
  width: 240px;
}

.actual-input {
  width: 110px;
}

.detail-tip {
  margin-top: 16px;
}

:deep(.row-gain) {
  --el-table-tr-bg-color: var(--el-color-success-light-9);
}

:deep(.row-loss) {
  --el-table-tr-bg-color: var(--el-color-danger-light-9);
}
</style>
