<template>
  <div class="page-container inbound-detail-page">
    <el-card class="detail-header-card" shadow="never">
      <div class="detail-header">
        <div class="detail-header__main">
          <div class="detail-header__title">
            {{ detail ? detail.orderNo : '入库单详情' }}
            <el-tag v-if="detail" :type="statusMeta(detail.status).type" size="small">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </div>
          <div class="detail-header__sub">
            <span v-if="detail">入库类型：{{ inboundTypeText(detail.inboundType) }}</span>
            <span v-if="detail">供应商：{{ detail.supplierName || '-' }}</span>
            <span v-if="detail">仓库：{{ detail.warehouseName || `仓库 #${detail.warehouseId}` }}</span>
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
            审核通过
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
          <el-button
            v-if="canPrint"
            type="success"
            :loading="printing"
            @click="openPrint"
          >
            打印标签
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card v-loading="loading" class="detail-body-card" shadow="never">
      <template v-if="detail">
        <el-descriptions title="基本信息" :column="3" border class="detail-desc">
          <el-descriptions-item label="入库单号">{{ detail.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="入库类型">
            {{ inboundTypeText(detail.inboundType) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusMeta(detail.status).type" size="small">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="供应商">
            {{ detail.supplierName || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="仓库">
            {{ detail.warehouseName || `仓库 #${detail.warehouseId}` }}
          </el-descriptions-item>
          <el-descriptions-item label="总金额">
            {{ formatMoney(detail.totalAmount) }}
          </el-descriptions-item>
          <el-descriptions-item label="操作人">
            {{ userText(detail.operatorId ?? detail.createdBy) }}
          </el-descriptions-item>
          <el-descriptions-item label="审核人">
            {{ userText(detail.auditUserId) }}
          </el-descriptions-item>
          <el-descriptions-item label="审核时间">
            {{ formatDate(detail.auditAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="入库时间">
            {{ formatDate(detail.inboundAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(detail.createdAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">
            {{ detail.remark || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="items-header">
          <span class="items-header__title">入库明细</span>
          <span class="items-header__tip">共 {{ detail.items.length }} 项</span>
        </div>

        <el-table :data="detail.items" border stripe row-key="id">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
          <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="spec" label="规格型号" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ row.spec || '-' }}</template>
          </el-table-column>
          <el-table-column label="数量" width="110" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="70" align="center" />
          <el-table-column label="单价" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.unitPrice) }}</template>
          </el-table-column>
          <el-table-column label="金额" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="批次号" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.batchNo || '-' }}</template>
          </el-table-column>
          <el-table-column label="生产日期" width="120">
            <template #default="{ row }">
              {{ formatDate(row.productionDate, 'YYYY-MM-DD') }}
            </template>
          </el-table-column>
          <el-table-column label="到期日期" width="120">
            <template #default="{ row }">
              {{ formatDate(row.expireDate, 'YYYY-MM-DD') }}
            </template>
          </el-table-column>
          <el-table-column label="库位" width="120">
            <template #default="{ row }">
              {{ row.locationId ? `库位 #${row.locationId}` : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="追踪方式" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.trackByItem === 1 ? 'warning' : 'info'" size="small">
                {{ row.trackByItem === 1 ? '逐件' : '数量' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="库存件" width="120" align="center">
            <template #default="{ row }">
              <template v-if="row.trackByItem === 1">
                {{ row.generated ? '已生成' : '待生成' }}
                <span v-if="row.generateItemQty">（{{ row.generateItemQty }}）</span>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="amount-summary">
          合计金额：<b>{{ formatMoney(detail.totalAmount) }}</b>
        </div>
      </template>

      <el-empty v-else-if="!loading" description="未找到入库单" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  approveInboundOrder,
  cancelInboundOrder,
  getInboundOrderDetail,
  getInboundPrintItems,
  submitInboundOrder,
  type InboundOrderDetail,
  type InboundStatus,
  type InboundType
} from '@/api/inbound'
import { formatDate, formatMoney, formatQuantity } from '@/utils/format'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

const statusMap: Record<InboundStatus, { label: string; type: TagType }> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '待审核', type: 'warning' },
  3: { label: '已入库', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const inboundTypeMap: Record<InboundType, string> = {
  PURCHASE: '采购入库',
  RETURN: '退货入库',
  TRANSFER: '调拨入库',
  ADJUST: '调整入库'
}

const route = useRoute()
const router = useRouter()

const detail = ref<InboundOrderDetail | null>(null)
const loading = ref(false)
const submitting = ref(false)
const approving = ref(false)
const cancelling = ref(false)
const printing = ref(false)

const orderId = computed(() => Number(route.params.id))

const canSubmit = computed(() => detail.value?.status === 1)
const canApprove = computed(() => detail.value?.status === 2)
const canCancel = computed(() => detail.value?.status === 1 || detail.value?.status === 2)
const canPrint = computed(() => detail.value?.status === 3)

function statusMeta(status: InboundStatus): { label: string; type: TagType } {
  return statusMap[status] ?? { label: '未知', type: 'info' }
}

function inboundTypeText(type: InboundType): string {
  return inboundTypeMap[type] ?? type
}

function userText(id: number | null | undefined): string {
  return id ? `用户 #${id}` : '-'
}

async function loadDetail() {
  const id = orderId.value
  if (!Number.isFinite(id) || id <= 0) {
    detail.value = null
    return
  }

  loading.value = true
  try {
    const res = await getInboundOrderDetail(id)
    detail.value = res.data
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

function goBack() {
  void router.push('/inbound')
}

async function handleSubmit() {
  if (!detail.value) {
    return
  }

  const confirmed = await ElMessageBox.confirm(
    `确认提交入库单「${detail.value.orderNo}」审核？提交后不可再修改明细。`,
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
    const res = await submitInboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('已提交审核')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

/** 审核通过后统计本次生成的逐件追踪库存件数量 */
function countGeneratedItems(source: InboundOrderDetail): number {
  return source.items
    .filter((item) => item.trackByItem === 1)
    .reduce((sum, item) => {
      const generated = Number(item.generateItemQty ?? Math.floor(Number(item.quantity)))
      return sum + (Number.isFinite(generated) ? generated : 0)
    }, 0)
}

async function openPrint() {
  if (!detail.value) {
    return
  }

  printing.value = true
  try {
    const printItems = await getInboundPrintItems(detail.value.id)
    const ids = printItems.map((item) => item.id).filter((id) => Boolean(id))
    if (!ids.length) {
      ElMessage.warning('该入库单暂无可打印的库存件（仅逐件追踪配件会生成二维码）')
      return
    }
    await router.push({ path: '/inventory/item/print', query: { ids: ids.join(',') } })
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    printing.value = false
  }
}

async function handleApprove() {
  if (!detail.value) {
    return
  }

  const confirmed = await ElMessageBox.confirm(
    `确认审核通过入库单「${detail.value.orderNo}」？通过后将写入库存并生成库存件二维码。`,
    '审核确认',
    { type: 'warning', confirmButtonText: '审核通过', cancelButtonText: '取消' }
  )
    .then(() => true)
    .catch(() => false)
  if (!confirmed) {
    return
  }

  approving.value = true
  try {
    const res = await approveInboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('审核通过，库存已更新')

    if (countGeneratedItems(res.data) > 0) {
      const printNow = await ElMessageBox.confirm(
        '已生成库存件二维码，是否立即打印标签？',
        '打印提示',
        { type: 'success', confirmButtonText: '立即打印', cancelButtonText: '稍后打印' }
      )
        .then(() => true)
        .catch(() => false)
      if (printNow) {
        await openPrint()
      }
    }
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
    `确认作废入库单「${detail.value.orderNo}」？作废后不可恢复。`,
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
    const res = await cancelInboundOrder(detail.value.id)
    detail.value = res.data
    ElMessage.success('入库单已作废')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  await loadDetail()
  // 从列表「审核」入口跳转过来时自动进入审核流程
  if (route.query.action === 'approve' && detail.value?.status === 2) {
    await handleApprove()
  }
})
</script>

<style scoped lang="scss">
.inbound-detail-page {
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
    justify-content: flex-end;

    :deep(.el-button + .el-button) {
      margin-left: 0;
    }
  }
}

.detail-desc {
  margin-bottom: 8px;
}

.items-header {
  display: flex;
  gap: 12px;
  align-items: baseline;
  margin: 20px 0 12px;

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__tip {
    font-size: 12px;
    color: #909399;
  }
}

.amount-summary {
  margin-top: 12px;
  font-size: 14px;
  text-align: right;

  b {
    font-size: 16px;
    color: #f56c6c;
  }
}
</style>


