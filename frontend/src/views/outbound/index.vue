<template>
  <div class="page-container outbound-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="出库单号">
          <el-input
            v-model="search.orderNo"
            placeholder="请输入出库单号"
            clearable
            class="filter-input"
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
              v-for="warehouse in warehouseOptions"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
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
        <span class="table-toolbar__title">出库单列表</span>
        <el-button type="primary" :icon="Plus" @click="goCreate">新建出库单</el-button>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="orderNo" label="出库单号" min-width="170" show-overflow-tooltip />
        <el-table-column label="仓库" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.warehouseName || `仓库 #${row.warehouseId}` }}
          </template>
        </el-table-column>
        <el-table-column label="出库类型" width="110" align="center">
          <template #default="{ row }">{{ outboundTypeText(row.outboundType) }}</template>
        </el-table-column>
        <el-table-column label="关联车辆" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.vehiclePlateNo || (row.vehicleId ? `车辆 #${row.vehicleId}` : '-') }}
          </template>
        </el-table-column>
        <el-table-column label="领用人" width="110" align="center">
          <template #default="{ row }">{{ userText(row.receiverId) }}</template>
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
        <el-table-column label="出库方式" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.scanMode === 1 ? 'success' : 'info'" size="small">
              {{ row.scanMode === 1 ? '扫码' : '手工' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="经办人" width="110" align="center">
          <template #default="{ row }">{{ userText(row.operatorId ?? row.createdBy) }}</template>
        </el-table-column>
        <el-table-column label="出库时间" width="170">
          <template #default="{ row }">{{ formatDate(row.outboundAt || row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row as OutboundOrder)">详情</el-button>
            <el-button
              v-if="row.status === 2"
              link
              type="warning"
              @click="goApprove(row as OutboundOrder)"
            >
              审核
            </el-button>
            <el-button
              v-if="row.status === 1 || row.status === 2"
              link
              type="danger"
              @click="handleCancel(row as OutboundOrder)"
            >
              作废
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
  cancelOutboundOrder,
  getOutboundOrderList,
  type OutboundOrder,
  type OutboundOrderQuery,
  type OutboundStatus,
  type OutboundType
} from '@/api/outbound'
import { getUserList, type UserOption } from '@/api/user'
import { getAllWarehouses, type Warehouse } from '@/api/warehouse'
import { useUserStore } from '@/stores/user'
import { formatDate, formatMoney } from '@/utils/format'

interface OutboundSearchForm {
  orderNo: string
  warehouseId: number | undefined
  status: OutboundStatus | undefined
  dateRange: string[]
}

type TagType = 'success' | 'warning' | 'info' | 'danger'

interface StatusMeta {
  label: string
  type: TagType
}

const STATUS_MAP: Record<OutboundStatus, StatusMeta> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '待审核', type: 'warning' },
  3: { label: '已出库', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const OUTBOUND_TYPE_MAP: Record<OutboundType, string> = {
  REPAIR: '维修领用',
  SALE: '销售出库',
  RETURN: '退料出库',
  TRANSFER: '调拨出库',
  SCRAP: '报废出库'
}

const statusOptions: Array<{ label: string; value: OutboundStatus }> = [
  { label: '草稿', value: 1 },
  { label: '待审核', value: 2 },
  { label: '已出库', value: 3 },
  { label: '已作废', value: 4 }
]

const router = useRouter()
const userStore = useUserStore()

const search = reactive<OutboundSearchForm>({
  orderNo: '',
  warehouseId: undefined,
  status: undefined,
  dateRange: []
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<OutboundOrder[]>([])
const warehouseOptions = ref<Warehouse[]>([])
const userOptions = ref<UserOption[]>([])
const loading = ref(false)

function statusMeta(status: number): StatusMeta {
  return STATUS_MAP[status as OutboundStatus] ?? { label: '未知', type: 'info' }
}

function outboundTypeText(type: string): string {
  return OUTBOUND_TYPE_MAP[type as OutboundType] ?? type
}

function userLabel(user: UserOption): string {
  return user.realName ? `${user.realName}（${user.username}）` : user.username
}

function userText(id: number | null | undefined): string {
  if (!id) {
    return '-'
  }
  const matched = userOptions.value.find((user) => user.id === id)
  return matched ? userLabel(matched) : `用户 #${id}`
}

function buildQuery(): OutboundOrderQuery {
  const [start, end] = search.dateRange
  return {
    orderNo: search.orderNo.trim() || undefined,
    warehouseId: search.warehouseId ?? undefined,
    status: search.status ?? undefined,
    startTime: start ? `${start} 00:00:00` : undefined,
    endTime: end ? `${end} 23:59:59` : undefined
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getOutboundOrderList({
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

async function loadWarehouseOptions() {
  try {
    warehouseOptions.value = await getAllWarehouses(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

/** 后端仅 admin / leader 可访问用户列表，其余角色不请求以免弹出 403 提示 */
async function loadUserOptions() {
  if (!['admin', 'leader'].includes(userStore.role)) {
    userOptions.value = []
    return
  }
  try {
    const res = await getUserList({ page: 1, pageSize: 200, status: 1 })
    userOptions.value = res.data.list
  } catch {
    userOptions.value = []
  }
}

function handleSearch() {
  pagination.page = 1
  void loadData()
}

function handleReset() {
  search.orderNo = ''
  search.warehouseId = undefined
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
  void router.push('/outbound/create')
}

function goDetail(row: OutboundOrder) {
  void router.push(`/outbound/${row.id}`)
}

/** 待审单据在详情页完成审核，并自动弹出审核确认 */
function goApprove(row: OutboundOrder) {
  void router.push({ path: `/outbound/${row.id}`, query: { action: 'approve' } })
}

async function handleCancel(row: OutboundOrder) {
  const confirmed = await ElMessageBox.confirm(
    `确认作废出库单「${row.orderNo}」？作废后不可恢复。`,
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
    await cancelOutboundOrder(row.id)
    ElMessage.success('出库单已作废')
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

onMounted(() => {
  void loadData()
  void loadWarehouseOptions()
  void loadUserOptions()
})
</script>

<style scoped lang="scss">
.outbound-page {
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

