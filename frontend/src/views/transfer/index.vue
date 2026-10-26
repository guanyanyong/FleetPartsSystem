<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="单号">
          <el-input
            v-model="search.orderNo"
            placeholder="调拨单号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="调出仓库">
          <el-select
            v-model="search.fromWarehouseId"
            placeholder="全部"
            clearable
            class="filter-select"
          >
            <el-option v-for="item in warehouses" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调入仓库">
          <el-select
            v-model="search.toWarehouseId"
            placeholder="全部"
            clearable
            class="filter-select"
          >
            <el-option v-for="item in warehouses" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部" clearable class="filter-select">
            <el-option
              v-for="(item, key) in STATUS_MAP"
              :key="key"
              :label="item.label"
              :value="Number(key)"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">调拨单列表</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新建调拨单</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="orderNo" label="调拨单号" min-width="180" show-overflow-tooltip />
        <el-table-column label="调出仓库" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.fromWarehouseName || '-' }}</template>
        </el-table-column>
        <el-table-column label="调入仓库" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.toWarehouseName || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusOf(row.status).type" effect="plain">
              {{ statusOf(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="调拨时间" width="170">
          <template #default="{ row }">{{ formatDate(row.transferAt) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as TransferOrder)">详情</el-button>
            <el-button
              v-if="row.status === 1 || row.status === 2"
              link
              type="success"
              @click="handleTransferOut(row as TransferOrder)"
            >
              确认调出
            </el-button>
            <el-button
              v-if="row.status === 3"
              link
              type="success"
              @click="handleTransferIn(row as TransferOrder)"
            >
              确认调入
            </el-button>
            <el-button
              v-if="row.status === 1 || row.status === 2"
              link
              type="danger"
              @click="handleCancel(row as TransferOrder)"
            >
              作废
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无调拨单" />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="loadData"
        />
      </div>

    </el-card>


    <el-dialog
      v-model="createVisible"
      title="新建调拨单"
      width="1080px"
      :close-on-click-modal="false"
      @closed="resetCreate"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="7">
            <el-form-item label="调出仓库" prop="fromWarehouseId">
              <el-select v-model="form.fromWarehouseId" placeholder="请选择" filterable class="w-full">
                <el-option
                  v-for="item in warehouses"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="7">
            <el-form-item label="调入仓库" prop="toWarehouseId">
              <el-select v-model="form.toWarehouseId" placeholder="请选择" filterable class="w-full">
                <el-option
                  v-for="item in warehouses"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="备注">
              <el-input v-model="form.remark" maxlength="200" placeholder="调拨说明（选填）" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="table-toolbar">
        <span class="table-toolbar__title">调拨明细</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" plain :icon="Plus" @click="partVisible = true">
            添加配件
          </el-button>
        </div>
      </div>

      <el-table :data="draftItems" border row-key="key" max-height="360">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="partCode" label="配件编码" width="140" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="单位" width="70" align="center">
          <template #default="{ row }">{{ row.unit }}</template>
        </el-table-column>
        <el-table-column label="数量" width="140" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.quantity"
              :min="0.01"
              :precision="2"
              :controls="false"
              size="small"
              class="qty-input"
            />
          </template>
        </el-table-column>
        <el-table-column label="调出库位" width="170">
          <template #default="{ row }">
            <el-select
              v-model="row.fromLocationId"
              placeholder="选填"
              clearable
              filterable
              size="small"
            >
              <el-option
                v-for="item in fromLocations"
                :key="item.id"
                :label="item.locationCode"
                :value="item.id"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="调入库位" width="170">
          <template #default="{ row }">
            <el-select v-model="row.toLocationId" placeholder="选填" clearable filterable size="small">
              <el-option
                v-for="item in toLocations"
                :key="item.id"
                :label="item.locationCode"
                :value="item.id"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeDraftItem($index)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="请点击「添加配件」选择调拨配件" :image-size="70" />
        </template>
      </el-table>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">创建调拨单</el-button>
      </template>
    </el-dialog>


    <el-drawer v-model="detailVisible" title="调拨单详情" size="820px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="调拨单号">{{ detail.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusOf(detail.status).type" effect="plain">
              {{ statusOf(detail.status).label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="调出仓库">
            {{ detail.fromWarehouseName || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="调入仓库">
            {{ detail.toWarehouseName || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="调拨时间">
            {{ formatDate(detail.transferAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="经办人">{{ detail.operatorId ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="drawer-title">调拨明细</div>
        <el-table :data="detail.items" border max-height="420">
          <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
          <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="规格" min-width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ row.spec || '-' }}</template>
          </el-table-column>
          <el-table-column label="数量" width="90" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="调出库位" width="110">
            <template #default="{ row }">{{ row.fromLocationCode || '-' }}</template>
          </el-table-column>
          <el-table-column label="调入库位" width="110">
            <template #default="{ row }">{{ row.toLocationCode || '-' }}</template>
          </el-table-column>
          <el-table-column label="库存件编码" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.itemCode || '-' }}</template>
          </el-table-column>
        </el-table>

        <div class="drawer-actions">
          <el-button
            v-if="detail.status === 1 || detail.status === 2"
            type="success"
            @click="handleTransferOut(detail)"
          >
            确认调出
          </el-button>
          <el-button v-if="detail.status === 3" type="success" @click="handleTransferIn(detail)">
            确认调入
          </el-button>
          <el-button
            v-if="detail.status === 1 || detail.status === 2"
            type="danger"
            plain
            @click="handleCancel(detail)"
          >
            作废
          </el-button>
        </div>
      </template>
    </el-drawer>

    <PartSelect v-model="partVisible" multiple :selected-ids="[]" @confirm="handlePartsConfirm" />
  </div>
</template>


<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import PartSelect from '@/components/PartSelect.vue'
import type { Part } from '@/api/part'
import {
  cancelTransferOrder,
  createTransferOrder,
  getTransferOrderDetail,
  getTransferOrderList,
  transferInOrder,
  transferOutOrder,
  type TransferOrder,
  type TransferOrderDetail,
  type TransferOrderQuery
} from '@/api/transfer'
import {
  getAllWarehouseLocations,
  getAllWarehouses,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import { formatDate, formatQuantity } from '@/utils/format'

type TagType = 'info' | 'primary' | 'success' | 'danger' | 'warning'

const STATUS_MAP: Record<number, { label: string; type: TagType }> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '待审', type: 'warning' },
  3: { label: '已调出', type: 'primary' },
  4: { label: '已调入', type: 'success' },
  5: { label: '已作废', type: 'danger' }
}

interface DraftItem {
  key: number
  partId: number
  partCode: string
  partName: string
  spec: string | null
  unit: string
  quantity: number
  fromLocationId?: number
  toLocationId?: number
}

const search = reactive<TransferOrderQuery>({
  orderNo: '',
  fromWarehouseId: undefined,
  toWarehouseId: undefined,
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<TransferOrder[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)

const createVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<{
  fromWarehouseId: number | undefined
  toWarehouseId: number | undefined
  remark: string
}>({
  fromWarehouseId: undefined,
  toWarehouseId: undefined,
  remark: ''
})

const rules: FormRules = {
  fromWarehouseId: [{ required: true, message: '请选择调出仓库', trigger: 'change' }],
  toWarehouseId: [
    { required: true, message: '请选择调入仓库', trigger: 'change' },
    {
      validator: (_rule, value: number | undefined, callback) => {
        if (value && value === form.fromWarehouseId) {
          callback(new Error('调入仓库不能与调出仓库相同'))
          return
        }
        callback()
      },
      trigger: 'change'
    }
  ]
}

const draftItems = ref<DraftItem[]>([])
const partVisible = ref(false)
const fromLocations = ref<WarehouseLocation[]>([])
const toLocations = ref<WarehouseLocation[]>([])
let draftKey = 0

const detailVisible = ref(false)
const detail = ref<TransferOrderDetail | null>(null)

function statusOf(status: number) {
  return STATUS_MAP[status] ?? { label: '未知', type: 'info' as TagType }
}

async function loadWarehouses() {
  try {
    warehouses.value = await getAllWarehouses(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

watch(
  () => form.fromWarehouseId,
  async (id) => {
    draftItems.value.forEach((item) => {
      item.fromLocationId = undefined
    })
    fromLocations.value = id ? await getAllWarehouseLocations(id).catch(() => []) : []
  }
)

watch(
  () => form.toWarehouseId,
  async (id) => {
    draftItems.value.forEach((item) => {
      item.toLocationId = undefined
    })
    toLocations.value = id ? await getAllWarehouseLocations(id).catch(() => []) : []
  }
)


async function loadData() {
  loading.value = true
  try {
    const res = await getTransferOrderList({
      ...search,
      orderNo: search.orderNo?.trim() || undefined,
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
  search.orderNo = ''
  search.fromWarehouseId = undefined
  search.toWarehouseId = undefined
  search.status = undefined
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function openCreate() {
  createVisible.value = true
}

function resetCreate() {
  form.fromWarehouseId = undefined
  form.toWarehouseId = undefined
  form.remark = ''
  draftItems.value = []
  fromLocations.value = []
  toLocations.value = []
  formRef.value?.clearValidate()
}

function handlePartsConfirm(parts: Part[]) {
  const existed = new Set(draftItems.value.map((item) => item.partId))
  parts.forEach((part) => {
    if (existed.has(part.id)) {
      return
    }
    existed.add(part.id)
    draftItems.value.push({
      key: ++draftKey,
      partId: part.id,
      partCode: part.partCode,
      partName: part.partName,
      spec: part.spec,
      unit: part.unit,
      quantity: 1,
      fromLocationId: undefined,
      toLocationId: undefined
    })
  })
}

function removeDraftItem(index: number) {
  draftItems.value.splice(index, 1)
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (!draftItems.value.length) {
    ElMessage.warning('请至少添加一条调拨明细')
    return
  }
  if (draftItems.value.some((item) => !item.quantity || item.quantity <= 0)) {
    ElMessage.warning('调拨数量必须大于 0')
    return
  }

  submitting.value = true
  try {
    const res = await createTransferOrder({
      fromWarehouseId: form.fromWarehouseId as number,
      toWarehouseId: form.toWarehouseId as number,
      remark: form.remark.trim() || null,
      items: draftItems.value.map((item) => ({
        partId: item.partId,
        quantity: item.quantity,
        fromLocationId: item.fromLocationId ?? null,
        toLocationId: item.toLocationId ?? null
      }))
    })
    ElMessage.success('调拨单创建成功')
    createVisible.value = false
    detail.value = res.data
    detailVisible.value = true
    pagination.page = 1
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function openDetail(row: TransferOrder) {
  try {
    const res = await getTransferOrderDetail(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleTransferOut(row: TransferOrder | TransferOrderDetail) {
  try {
    await ElMessageBox.confirm(
      `确认调拨单「${row.orderNo}」已从调出仓库出库吗？确认后将扣减调出仓库存。`,
      '确认调出',
      { type: 'warning' }
    )
    const res = await transferOutOrder(row.id)
    ElMessage.success('已确认调出')
    if (detailVisible.value) {
      detail.value = res.data
    }
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

async function handleTransferIn(row: TransferOrder | TransferOrderDetail) {
  try {
    await ElMessageBox.confirm(
      `确认调拨单「${row.orderNo}」的货物已全部调入吗？确认后将增加调入仓库存。`,
      '确认调入',
      { type: 'warning' }
    )
    const res = await transferInOrder(row.id)
    ElMessage.success('已确认调入')
    if (detailVisible.value) {
      detail.value = res.data
    }
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

async function handleCancel(row: TransferOrder | TransferOrderDetail) {
  try {
    await ElMessageBox.confirm(`确定作废调拨单「${row.orderNo}」吗？`, '作废确认', {
      type: 'warning'
    })
    const res = await cancelTransferOrder(row.id)
    ElMessage.success('已作废')
    if (detailVisible.value) {
      detail.value = res.data
    }
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

onMounted(async () => {
  await loadWarehouses()
  await loadData()
})
</script>

<style scoped lang="scss">
.qty-input {
  width: 110px;
}

.drawer-title {
  margin: 20px 0 12px;
  font-weight: 600;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>

