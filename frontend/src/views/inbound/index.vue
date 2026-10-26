<template>
  <div class="page-container inbound-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="入库单号">
          <el-input
            v-model="search.orderNo"
            placeholder="请输入入库单号"
            clearable
            class="filter-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="供应商">
          <el-select
            v-model="search.supplierId"
            placeholder="全部供应商"
            clearable
            filterable
            class="filter-select"
          >
            <el-option
              v-for="supplier in supplierOptions"
              :key="supplier.id"
              :label="supplier.name"
              :value="supplier.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="search.status"
            placeholder="全部状态"
            clearable
            class="filter-select"
          >
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="search.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
            class="filter-date"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">入库单列表</span>
        <el-button type="primary" :icon="Plus" @click="goCreate">新建入库单</el-button>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="orderNo" label="入库单号" min-width="170" show-overflow-tooltip />
        <el-table-column label="供应商" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplierName || '-' }}</template>
        </el-table-column>
        <el-table-column label="仓库" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.warehouseName || `仓库 #${row.warehouseId}` }}</template>
        </el-table-column>
        <el-table-column label="入库类型" width="110" align="center">
          <template #default="{ row }">{{ inboundTypeText(row.inboundType) }}</template>
        </el-table-column>
        <el-table-column label="总金额" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.totalAmount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusMeta(row.status).type" size="small">
              {{ statusMeta(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="110" align="center">
          <template #default="{ row }">{{ operatorText(row as InboundOrder) }}</template>
        </el-table-column>
        <el-table-column label="入库时间" width="170">
          <template #default="{ row }">{{ formatDate(row.inboundAt || row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row as InboundOrder)">详情</el-button>
            <el-button v-if="row.status === 2" link type="warning" @click="goApprove(row as InboundOrder)">
              审核
            </el-button>
            <el-button
              v-if="row.status === 1 || row.status === 2"
              link
              type="danger"
              @click="handleCancel(row as InboundOrder)"
            >
              作废
            </el-button>
            <el-button
              v-if="row.status === 3"
              link
              type="success"
              :loading="printLoadingId === row.id"
              @click="handlePrint(row as InboundOrder)"
            >
              打印标签
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="loadData"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  cancelInboundOrder,
  getInboundOrderList,
  getInboundPrintItems,
  type InboundOrder,
  type InboundOrderQuery,
  type InboundStatus,
  type InboundType
} from '@/api/inbound'
import { getAllSuppliers, type Supplier } from '@/api/supplier'
import { formatDate, formatMoney } from '@/utils/format'

interface InboundSearchForm {
  orderNo: string
  supplierId: number | undefined
  status: InboundStatus | undefined
  dateRange: string[]
}

type TagType = 'success' | 'warning' | 'info' | 'danger'

interface StatusMeta {
  label: string
  type: TagType
}

const STATUS_MAP: Record<InboundStatus, StatusMeta> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '待审核', type: 'warning' },
  3: { label: '已入库', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const INBOUND_TYPE_MAP: Record<InboundType, string> = {
  PURCHASE: '采购入库',
  RETURN: '退货入库',
  TRANSFER: '调拨入库',
  ADJUST: '调整入库'
}

const statusOptions: Array<{ label: string; value: InboundStatus }> = [
  { label: '草稿', value: 1 },
  { label: '待审核', value: 2 },
  { label: '已入库', value: 3 },
  { label: '已作废', value: 4 }
]

const router = useRouter()

const search = reactive<InboundSearchForm>({
  orderNo: '',
  supplierId: undefined,
  status: undefined,
  dateRange: []
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<InboundOrder[]>([])
const supplierOptions = ref<Supplier[]>([])
const loading = ref(false)
const printLoadingId = ref<number | null>(null)

function statusMeta(status: number): StatusMeta {
  return STATUS_MAP[status as InboundStatus] ?? { label: '未知', type: 'info' }
}

function inboundTypeText(type: string): string {
  return INBOUND_TYPE_MAP[type as InboundType] ?? type
}

function operatorText(row: InboundOrder): string {
  const id = row.operatorId ?? row.createdBy
  return id ? `用户 #${id}` : '-'
}

function buildQuery(): InboundOrderQuery {
  const [start, end] = search.dateRange
  return {
    orderNo: search.orderNo.trim() || undefined,
    supplierId: search.supplierId ?? undefined,
    status: search.status ?? undefined,
    startTime: start ? `${start} 00:00:00` : undefined,
    endTime: end ? `${end} 23:59:59` : undefined
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getInboundOrderList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...buildQuery()
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function loadSupplierOptions() {
  try {
    supplierOptions.value = await getAllSuppliers(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleSearch() {
  pagination.page = 1
  void loadData()
}

function handleReset() {
  search.orderNo = ''
  search.supplierId = undefined
  search.status = undefined
  search.dateRange = []
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function goCreate() {
  void router.push('/inbound/create')
}

function goDetail(row: InboundOrder) {
  void router.push(`/inbound/${row.id}`)
}

/** 待审单据在详情页完成审核，并自动弹出审核确认 */
function goApprove(row: InboundOrder) {
  void router.push({ path: `/inbound/${row.id}`, query: { action: 'approve' } })
}

async function handleCancel(row: InboundOrder) {
  const confirmed = await ElMessageBox.confirm(
    `确认作废入库单「${row.orderNo}」？作废后不可恢复。`,
    '作废确认',
    {
      type: 'warning',
      confirmButtonText: '确认作废',
      cancelButtonText: '取消'
    }
  )
    .then(() => true)
    .catch(() => false)

  if (!confirmed) {
    return
  }

  try {
    await cancelInboundOrder(row.id)
    ElMessage.success('入库单已作废')
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

/** 查询入库单已生成的库存件并跳转标签打印页 */
async function handlePrint(row: InboundOrder) {
  printLoadingId.value = row.id
  try {
    const printItems = await getInboundPrintItems(row.id)
    const ids = printItems
      .map((item) => item.id)
      .filter((id): id is number => typeof id === 'number' && id > 0)

    if (!ids.length) {
      ElMessage.warning('该入库单暂无可打印的库存件')
      return
    }

    void router.push({ path: '/inventory/item/print', query: { ids: ids.join(',') } })
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    printLoadingId.value = null
  }
}

onMounted(() => {
  void loadData()
  void loadSupplierOptions()
})
</script>

<style scoped lang="scss">
.inbound-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card {
  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 0;
}

.filter-input {
  width: 180px;
}

.filter-select {
  width: 170px;
}

.filter-date {
  width: 260px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

