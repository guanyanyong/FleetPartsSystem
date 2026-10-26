<template>
  <div class="page-container outbound-detail-page">
    <el-card class="detail-header-card" shadow="never">
      <div class="detail-header">
        <div class="detail-header__main">
          <div class="detail-header__title">
            {{ detail ? detail.orderNo : '出库单详情' }}
            <el-tag v-if="detail" :type="statusMeta(detail.status).type" size="small">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </div>
          <div class="detail-header__sub">
            <span v-if="detail">出库类型：{{ outboundTypeText(detail.outboundType) }}</span>
            <span v-if="detail">
              仓库：{{ detail.warehouseName || `仓库 #${detail.warehouseId}` }}
            </span>
            <span v-if="detail">
              车辆：{{ detail.vehiclePlateNo || (detail.vehicleId ? `车辆 #${detail.vehicleId}` : '-') }}
            </span>
          </div>
        </div>
        <div class="detail-header__actions">
          <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
          <el-button v-if="canSubmit" :loading="submitting" @click="handleSubmit">
            提交审核
          </el-button>
          <el-button
            v-if="canApprove"
            type="primary"
            :loading="approving"
            @click="handleApprove"
          >
            审核出库
          </el-button>
          <el-button
            v-if="canCancel"
            type="danger"
            plain
            :loading="cancelling"
            @click="handleCancel"
          >
            作废
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card v-loading="loading" class="detail-body-card" shadow="never">
      <template v-if="detail">
        <el-descriptions title="基本信息" :column="3" border class="detail-desc">
          <el-descriptions-item label="出库单号">{{ detail.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="出库类型">
            {{ outboundTypeText(detail.outboundType) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusMeta(detail.status).type" size="small">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="仓库">
            {{ detail.warehouseName || `仓库 #${detail.warehouseId}` }}
          </el-descriptions-item>
          <el-descriptions-item label="关联车辆">
            {{ detail.vehiclePlateNo || (detail.vehicleId ? `车辆 #${detail.vehicleId}` : '-') }}
          </el-descriptions-item>
          <el-descriptions-item label="关联工单">
            {{ detail.workOrderId ? `工单 #${detail.workOrderId}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="领用人">
            {{ userText(detail.receiverId) }}
          </el-descriptions-item>
          <el-descriptions-item label="经办人">
            {{ userText(detail.operatorId ?? detail.createdBy) }}
          </el-descriptions-item>
          <el-descriptions-item label="扫码操作人">
            {{ detail.scanMode === 1 ? userText(detail.scannerId) : '非扫码模式' }}
          </el-descriptions-item>
          <el-descriptions-item label="总金额">
            {{ formatMoney(detail.totalAmount) }}
          </el-descriptions-item>
          <el-descriptions-item label="审核人">
            {{ userText(detail.auditUserId) }}
          </el-descriptions-item>
          <el-descriptions-item label="审核时间">
            {{ formatDate(detail.auditAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="出库时间">
            {{ formatDate(detail.outboundAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(detail.createdAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">
            {{ detail.remark || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="items-header">
          <span class="items-header__title">出库明细</span>
          <span class="items-header__tip">
            共 {{ detail.items.length }} 项，合计 {{ formatQuantity(totalQuantity) }} 件
          </span>
        </div>

        <el-table :data="detail.items" border stripe row-key="id">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column label="库存件编码" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.itemCode || '-' }}</template>
          </el-table-column>
          <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
          <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="规格型号" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ row.spec || '-' }}</template>
          </el-table-column>
          <el-table-column label="数量" width="100" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="70" align="center" />
          <el-table-column label="单位成本" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.unitCost) }}</template>
          </el-table-column>
          <el-table-column label="金额" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="批次号" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.batchNo || '-' }}</template>
          </el-table-column>
          <el-table-column label="库位" width="110">
            <template #default="{ row }">
              {{ row.locationId ? `库位 #${row.locationId}` : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="扫码内容" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.scanCode || '-' }}</template>
          </el-table-column>
          <el-table-column label="扫码时间" width="160">
            <template #default="{ row }">{{ formatDate(row.scanAt) }}</template>
          </el-table-column>
          <el-table-column label="备注" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.remark || '-' }}</template>
          </el-table-column>
        </el-table>

        <div class="amount-summary">
          合计金额：<b>{{ formatMoney(detail.totalAmount) }}</b>
        </div>
      </template>

      <el-empty v-else-if="!loading" description="未找到出库单" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  approveOutboundOrder,
  cancelOutboundOrder,
  getOutboundOrderDetail,
  submitOutboundOrder,
  type OutboundOrderDetail,
  type OutboundStatus,
  type OutboundType
} from '@/api/outbound'
import { getUserList, type UserOption } from '@/api/user'
import { useUserStore } from '@/stores/user'
import { formatDate, formatMoney, formatQuantity } from '@/utils/format'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

const statusMap: Record<OutboundStatus, { label: string; type: TagType }> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '待审核', type: 'warning' },
  3: { label: '已出库', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const outboundTypeMap: Record<OutboundType, string> = {
  REPAIR: '维修领用',
  SALE: '销售出库',
  RETURN: '退料出库',
  TRANSFER: '调拨出库',
  SCRAP: '报废出库'
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const detail = ref<OutboundOrderDetail | null>(null)
const userOptions = ref<UserOption[]>([])
const loading = ref(false)
const submitting = ref(false)
const approving = ref(false)
const cancelling = ref(false)

const orderId = computed(() => Number(route.params.id))

const canSubmit = computed(() => detail.value?.status === 1)
const canApprove = computed(() => detail.value?.status === 2)
const canCancel = computed(() => detail.value?.status === 1 || detail.value?.status === 2)

const totalQuantity = computed(() => {
  if (!detail.value) {
    return 0
  }
  const total = detail.value.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  return Math.round(total * 100) / 100
})

function statusMeta(status: OutboundStatus): { label: string; type: TagType } {
  return statusMap[status] ?? { label: '未知', type: 'info' }
}

function outboundTypeText(type: OutboundType): string {
  return outboundTypeMap[type] ?? type
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

async function loadDetail() {
  const id = orderId.value
  if (!Number.isFinite(id) || id <= 0) {
    detail.value = null
    return
  }

  loading.value = true
  try {
    const res = await getOutboundOrderDetail(id)
    detail.value = res.data
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

function goBack() {
  void router.push('/outbound')
}

async function handleSubmit() {
  if (!detail.value) {
    return
  }

  const confirmed = await ElMessageBox.confirm(
    `确认提交出库单「${detail.value.orderNo}」审核？提交后将锁定库存并占用数量。`,
    '提交确认',
    { type: 'warning', confirmButtonText: '提交', cancelButtonText: '取消' }
  )
    .then(() => true)
    .catch(() => false)
  if (!confirmed) {
    return
  }

  submitting.value = true
  try {
    const res = await submitOutboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('已提交审核')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function handleApprove() {
  if (!detail.value) {
    return
  }

  const confirmed = await ElMessageBox.confirm(
    `确认审核出库单「${detail.value.orderNo}」？通过后将扣减库存并标记库存件已出库，操作不可撤销。`,
    '审核确认',
    { type: 'warning', confirmButtonText: '审核出库', cancelButtonText: '取消' }
  )
    .then(() => true)
    .catch(() => false)
  if (!confirmed) {
    return
  }

  approving.value = true
  try {
    const res = await approveOutboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('审核通过，库存已扣减')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    approving.value = false
  }
}

async function handleCancel() {
  if (!detail.value) {
    return
  }

  const confirmed = await ElMessageBox.confirm(
    `确认作废出库单「${detail.value.orderNo}」？作废后释放占用的库存，且不可恢复。`,
    '作废确认',
    { type: 'warning', confirmButtonText: '作废', cancelButtonText: '取消' }
  )
    .then(() => true)
    .catch(() => false)
  if (!confirmed) {
    return
  }

  cancelling.value = true
  try {
    const res = await cancelOutboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('出库单已作废')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadDetail(), loadUserOptions()])
  // 从列表「审核」入口跳转过来时自动进入审核流程
  if (route.query.action === 'approve' && detail.value?.status === 2) {
    await handleApprove()
  }
})
</script>

<style scoped lang="scss">
.outbound-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;

  &__main {
    min-width: 240px;
  }

  &__title {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__sub {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 8px;
    font-size: 13px;
    color: #909399;
  }

  &__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
}

.detail-desc {
  margin-bottom: 20px;
}

.items-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__tip {
    font-size: 13px;
    color: #909399;
  }
}

.amount-summary {
  padding: 12px 16px;
  margin-top: 12px;
  font-size: 14px;
  text-align: right;
  background-color: #fafafa;
  border-radius: 4px;

  b {
    font-size: 16px;
    color: #f56c6c;
  }
}
</style>

