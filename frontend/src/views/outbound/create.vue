<template>
  <div class="page-container outbound-create-page">
    <el-card class="form-card" shadow="never">
      <div class="card-title">新建出库单</div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="outbound-form"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="出库仓库" prop="warehouseId">
              <el-select
                v-model="form.warehouseId"
                placeholder="请选择仓库"
                clearable
                filterable
                class="full-width"
              >
                <el-option
                  v-for="warehouse in warehouseOptions"
                  :key="warehouse.id"
                  :label="warehouse.name"
                  :value="warehouse.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="出库类型" prop="outboundType">
              <el-select v-model="form.outboundType" class="full-width">
                <el-option
                  v-for="item in outboundTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="关联车辆" prop="vehicleId">
              <el-select
                v-model="form.vehicleId"
                placeholder="选填，可搜索车牌号"
                clearable
                filterable
                class="full-width"
              >
                <el-option
                  v-for="vehicle in vehicleOptions"
                  :key="vehicle.id"
                  :label="vehicle.plateNo"
                  :value="vehicle.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="关联工单" prop="workOrderId">
              <el-select
                v-model="form.workOrderId"
                placeholder="选填，可搜索工单号"
                clearable
                filterable
                class="full-width"
              >
                <el-option
                  v-for="order in workOrderOptions"
                  :key="order.id"
                  :label="order.orderNo"
                  :value="order.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="领用人" prop="receiverId">
              <el-select
                v-model="form.receiverId"
                placeholder="选填，可选择领用人"
                clearable
                filterable
                class="full-width"
              >
                <el-option
                  v-for="user in userOptions"
                  :key="user.id"
                  :label="userLabel(user)"
                  :value="user.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input
                v-model="form.remark"
                placeholder="选填，最多 255 字"
                maxlength="255"
                show-word-limit
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card class="items-card" shadow="never">
      <div class="scan-bar">
        <div class="scan-bar__input">
          <ScanInput :disabled="saving || submitting" @scan="handleScan" />
        </div>
        <el-button :icon="Plus" :disabled="saving || submitting" @click="openPartSelect">
          手动添加
        </el-button>
        <el-button
          :icon="Delete"
          :disabled="saving || submitting || !cart.items.length"
          @click="handleClearItems"
        >
          清空明细
        </el-button>
        <span class="scan-bar__tip">请先选择出库仓库，扫描库存件二维码自动追加明细</span>
      </div>

      <el-table
        :data="cart.items"
        row-key="key"
        border
        empty-text="请扫描库存件二维码，或点击「手动添加」选择非追踪配件"
        class="items-table"
      >
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column label="库存件编码" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ 'text-muted': !row.itemCode }">{{ row.itemCode || '手工添加' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="spec" label="规格型号" min-width="120" show-overflow-tooltip />
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column label="数量" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.inventoryItemId">1</span>
            <el-input-number
              v-else
              v-model="row.quantity"
              :min="0.01"
              :max="999999"
              :precision="2"
              :step="1"
              :value-on-clear="1"
              controls-position="right"
              size="small"
              class="number-input"
            />
          </template>
        </el-table-column>
        <el-table-column label="单位成本" width="140" align="center">
          <template #default="{ row }">
            <span v-if="row.inventoryItemId">{{ formatMoney(row.unitCost) }}</span>
            <el-input-number
              v-else
              v-model="row.unitCost"
              :min="0"
              :max="99999999"
              :precision="4"
              :step="1"
              :value-on-clear="0"
              controls-position="right"
              size="small"
              class="number-input"
            />
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(rowAmount(row as CartItem)) }}</template>
        </el-table-column>
        <el-table-column label="批次号" width="140">
          <template #default="{ row }">
            <span v-if="row.inventoryItemId">{{ row.batchNo || '-' }}</span>
            <el-input
              v-else
              v-model="row.batchNo"
              maxlength="50"
              placeholder="选填"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="库位" width="150">
          <template #default="{ row }">
            <span v-if="row.inventoryItemId">{{ row.locationCode || '-' }}</span>
            <el-select
              v-else
              v-model="row.locationId"
              placeholder="选填"
              clearable
              filterable
              size="small"
              :disabled="!form.warehouseId"
              class="full-width"
              @change="(value: number | undefined) => handleLocationChange(row as CartItem, value)"
            >
              <el-option
                v-for="location in locations"
                :key="location.id"
                :label="location.locationCode"
                :value="location.id"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="扫码时间" width="160">
          <template #default="{ row }">
            {{ row.inventoryItemId ? formatDate(row.scanAt) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="备注" width="150">
          <template #default="{ row }">
            <el-input
              v-model="row.remark"
              maxlength="255"
              placeholder="选填"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" @click="cart.removeItem($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="items-summary">
        <span>明细 {{ cart.items.length }} 项，共 {{ formatQuantity(cart.totalQuantity) }} 件</span>
        <span>
          合计金额：<b class="items-summary__amount">{{ formatMoney(cart.totalAmount) }}</b>
        </span>
      </div>

      <div class="form-actions">
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <el-button :loading="saving" :disabled="submitting" @click="handleSave(false)">
          保存草稿
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="saving"
          @click="handleSave(true)"
        >
          提交审核
        </el-button>
      </div>
    </el-card>

    <PartSelect
      v-model="partDialogVisible"
      multiple
      title="选择非追踪配件"
      :selected-ids="selectedPartIds"
      @confirm="handlePartsSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { ArrowLeft, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createOutboundOrder,
  scanInventoryItem,
  submitOutboundOrder,
  type OutboundOrderPayload,
  type OutboundType
} from '@/api/outbound'
import type { Part } from '@/api/part'
import { getUserList, type UserOption } from '@/api/user'
import { getAllVehicles, type VehicleOption } from '@/api/vehicle'
import {
  getAllWarehouses,
  getAllWarehouseLocations,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import { getAllWorkOrders, type WorkOrderOption } from '@/api/workOrder'
import PartSelect from '@/components/PartSelect.vue'
import ScanInput from '@/components/ScanInput.vue'
import { useCartStore, type CartItem } from '@/stores/cart'
import { useUserStore } from '@/stores/user'
import { ApiError } from '@/utils/request'
import { formatDate, formatMoney, formatQuantity } from '@/utils/format'

interface OutboundForm {
  warehouseId: number | undefined
  outboundType: OutboundType
  vehicleId: number | undefined
  workOrderId: number | undefined
  receiverId: number | undefined
  remark: string
}

const outboundTypeOptions: Array<{ label: string; value: OutboundType }> = [
  { label: '维修领用', value: 'REPAIR' },
  { label: '销售出库', value: 'SALE' },
  { label: '退料出库', value: 'RETURN' },
  { label: '调拨出库', value: 'TRANSFER' },
  { label: '报废出库', value: 'SCRAP' }
]

/** 扫码业务错误码提示文案（后端 HTTP 200 + body.code） */
const SCAN_ERROR_MESSAGE: Record<number, string> = {
  2002: '该库存件已报废或盘亏，无法出库',
  2003: '该库存件已出库，无法重复出库',
  2004: '该库存件已锁定，无法出库',
  4001: '无法识别的条码，请确认扫码内容'
}

const router = useRouter()
const cart = useCartStore()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const form = reactive<OutboundForm>({
  warehouseId: undefined,
  outboundType: 'REPAIR',
  vehicleId: undefined,
  workOrderId: undefined,
  receiverId: undefined,
  remark: ''
})

const rules: FormRules<OutboundForm> = {
  warehouseId: [{ required: true, message: '请选择出库仓库', trigger: 'change' }],
  outboundType: [{ required: true, message: '请选择出库类型', trigger: 'change' }],
  remark: [{ max: 255, message: '备注不能超过 255 个字符', trigger: 'blur' }]
}

const warehouseOptions = ref<Warehouse[]>([])
const vehicleOptions = ref<VehicleOption[]>([])
const workOrderOptions = ref<WorkOrderOption[]>([])
const userOptions = ref<UserOption[]>([])
const locations = ref<WarehouseLocation[]>([])

const partDialogVisible = ref(false)
const saving = ref(false)
const submitting = ref(false)
const scanning = ref(false)

const selectedPartIds = computed(() => cart.items.map((row) => row.partId))

/** 明细行金额：数量 × 单位成本，保留两位小数 */
function rowAmount(row: CartItem): number {
  const quantity = Number(row.quantity)
  const cost = Number(row.unitCost)
  if (!Number.isFinite(quantity) || !Number.isFinite(cost)) {
    return 0
  }
  return Number((quantity * cost).toFixed(2))
}

function userLabel(user: UserOption): string {
  return user.realName ? `${user.realName}（${user.username}）` : user.username
}

async function loadOptions() {
  try {
    const [warehouses, vehicles, workOrders] = await Promise.all([
      getAllWarehouses(1),
      getAllVehicles(),
      getAllWorkOrders()
    ])
    warehouseOptions.value = warehouses
    vehicleOptions.value = vehicles
    workOrderOptions.value = workOrders
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

async function loadLocations(warehouseId: number) {
  locations.value = []
  try {
    locations.value = await getAllWarehouseLocations(warehouseId)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

watch(
  () => form.warehouseId,
  (value, oldValue) => {
    if (oldValue !== undefined && value !== oldValue && cart.items.length) {
      // 已扫明细可能属于旧仓库，切换仓库后直接清空避免脏数据
      cart.clear()
      ElMessage.info('已切换仓库，出库明细已清空')
    }
    if (typeof value === 'number' && value > 0) {
      void loadLocations(value)
    } else {
      locations.value = []
    }
  }
)

watch(
  () => form.workOrderId,
  (value) => {
    if (!value) {
      return
    }
    // 选择工单后自动带出工单关联车辆，减少重复选择
    const workOrder = workOrderOptions.value.find((item) => item.id === value)
    if (workOrder?.vehicleId) {
      form.vehicleId = workOrder.vehicleId
    }
  }
)

onMounted(() => {
  cart.clear()
  void loadOptions()
  void loadUserOptions()
})

/** 扫码失败：按业务错误码给出可读提示 */
function scanErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code !== undefined) {
    return SCAN_ERROR_MESSAGE[error.code] ?? error.message
  }
  return error instanceof Error ? error.message : '扫码失败，请重试'
}

/**
 * 扫码出库：只接受「在库」的库存件，且必须与出库仓库一致。
 * 返回的实例信息直接作为明细的配件 / 批次 / 库位 / 成本来源。
 */
async function handleScan(code: string) {
  if (scanning.value) {
    return
  }
  if (!form.warehouseId) {
    ElMessage.warning('请先选择出库仓库再扫码')
    return
  }

  scanning.value = true
  try {
    const res = await scanInventoryItem(code)
    const data = res.data
    if (!data) {
      ElMessage.warning('未找到该库存件，请确认条码内容')
      return
    }
    if (data.status !== 1) {
      ElMessage.error(`该库存件当前状态为「${data.statusText}」，无法出库`)
      return
    }
    if (data.warehouseId !== form.warehouseId) {
      ElMessage.error(
        `该库存件属于仓库「${data.warehouseName || `#${data.warehouseId}`}」，与出库仓库不一致`
      )
      return
    }

    cart.addItem({
      partId: data.partId,
      partCode: data.partCode || '-',
      partName: data.partName || '-',
      spec: data.spec,
      unit: data.unit,
      quantity: 1,
      unitCost: Number(data.unitCost || 0),
      inventoryItemId: data.itemId,
      itemCode: data.itemCode,
      batchNo: data.batchNo,
      locationId: data.locationId,
      locationCode: data.locationCode,
      scanCode: code.trim(),
      scanType: code.trim().toUpperCase().startsWith('QR:') ? 'QRCODE' : 'BARCODE',
      scanAt: formatDate(new Date()),
      remark: null
    })
    ElMessage.success(`已添加 ${data.partName || data.itemCode}`)
  } catch (error) {
    ElMessage.error(scanErrorMessage(error))
  } finally {
    scanning.value = false
  }
}

function openPartSelect() {
  partDialogVisible.value = true
}

/**
 * 手动添加非追踪配件：逐件追踪的配件必须扫码指定库存件，这里直接拦截。
 * 同一配件在同一库位已有明细时累加数量，否则新增一行。
 */
function handlePartsSelected(parts: Part[]) {
  if (!parts.length) {
    return
  }

  const tracked = parts.filter((part) => part.trackByItem === 1)
  const manualParts = parts.filter((part) => part.trackByItem !== 1)

  manualParts.forEach((part) => {
    const existing = cart.items.find(
      (row) =>
        row.inventoryItemId === null && row.partId === part.id && row.locationId === null
    )
    if (existing) {
      existing.quantity += 1
      return
    }
    cart.addItem({
      partId: part.id,
      partCode: part.partCode,
      partName: part.partName,
      spec: part.spec,
      unit: part.unit,
      quantity: 1,
      unitCost: 0,
      inventoryItemId: null,
      itemCode: null,
      batchNo: null,
      locationId: null,
      locationCode: null,
      scanCode: null,
      scanType: null,
      scanAt: null,
      remark: null
    })
  })

  if (tracked.length) {
    ElMessage.warning(
      `按件追踪配件（${tracked.map((part) => part.partName).join('、')}）请扫码添加`
    )
  }
  if (manualParts.length) {
    ElMessage.success(`已添加 ${manualParts.length} 个配件`)
  }
}

function handleLocationChange(row: CartItem, locationId: number | undefined) {
  const location = locations.value.find((item) => item.id === locationId)
  row.locationCode = location?.locationCode ?? null
}

async function handleClearItems() {
  if (!cart.items.length) {
    return
  }

  const confirmed = await ElMessageBox.confirm('确认清空全部出库明细？', '清空确认', {
    type: 'warning',
    confirmButtonText: '清空',
    cancelButtonText: '取消'
  })
    .then(() => true)
    .catch(() => false)

  if (confirmed) {
    cart.clear()
  }
}

/** 明细校验：数量必须大于 0，逐件追踪件数量固定为 1 */
function validateItems(): boolean {
  for (let index = 0; index < cart.items.length; index += 1) {
    const row = cart.items[index]
    if (!row) {
      continue
    }
    const quantity = Number(row.quantity)
    if (!Number.isFinite(quantity) || quantity <= 0) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」数量必须大于 0`)
      return false
    }
    if (row.inventoryItemId !== null && quantity !== 1) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」按件追踪，数量必须为 1`)
      return false
    }
    if (!Number.isFinite(Number(row.unitCost)) || Number(row.unitCost) < 0) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」单位成本不能小于 0`)
      return false
    }
  }
  return true
}

function buildPayload(warehouseId: number): OutboundOrderPayload {
  return {
    warehouseId,
    outboundType: form.outboundType,
    vehicleId: form.vehicleId ?? null,
    workOrderId: form.workOrderId ?? null,
    receiverId: form.receiverId ?? null,
    scanMode: cart.items.some((row) => row.inventoryItemId !== null) ? 1 : 0,
    remark: form.remark.trim() || null,
    items: cart.items.map((row) => ({
      partId: row.partId,
      inventoryItemId: row.inventoryItemId,
      quantity: Number(row.quantity),
      unit: row.unit,
      unitCost: Number(row.unitCost),
      batchNo: row.batchNo?.trim() || null,
      locationId: row.locationId ?? null,
      scanCode: row.scanCode,
      scanType: row.scanType,
      scanAt: row.scanAt,
      remark: row.remark?.trim() || null
    }))
  }
}

async function handleSave(submitAfter: boolean) {
  if (!formRef.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (!form.warehouseId) {
    ElMessage.warning('请选择出库仓库')
    return
  }
  if (!cart.items.length) {
    ElMessage.warning('请先扫码或手动添加出库明细')
    return
  }
  if (!validateItems()) {
    return
  }

  const loadingRef = submitAfter ? submitting : saving
  loadingRef.value = true
  let createdId: number | null = null
  try {
    const created = await createOutboundOrder(buildPayload(form.warehouseId))
    createdId = created.data.id
    if (submitAfter) {
      await submitOutboundOrder(createdId)
      ElMessage.success('出库单已创建并提交审核')
    } else {
      ElMessage.success('出库单草稿保存成功')
    }
    cart.clear()
    void router.replace(`/outbound/${createdId}`)
  } catch {
    // 建单成功但提交失败时，草稿已落库，跳转详情避免用户重复建单
    if (createdId !== null) {
      cart.clear()
      ElMessage.warning('出库单已保存为草稿，请在详情页继续处理')
      void router.replace(`/outbound/${createdId}`)
    }
  } finally {
    loadingRef.value = false
  }
}

function goBack() {
  void router.push('/outbound')
}
</script>

<style scoped lang="scss">
.outbound-create-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-title {
  margin-bottom: 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.outbound-form {
  :deep(.el-form-item) {
    margin-bottom: 8px;
  }
}

.full-width {
  width: 100%;
}

.scan-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;

  &__input {
    flex: 1;
    min-width: 280px;
    max-width: 520px;
  }

  &__tip {
    font-size: 12px;
    color: #909399;
  }
}

.items-table {
  margin-top: 16px;

  .number-input {
    width: 110px;
  }
}

.text-muted {
  color: #909399;
}

.items-summary {
  display: flex;
  gap: 24px;
  align-items: center;
  justify-content: flex-end;
  padding: 12px 16px;
  margin-top: 12px;
  font-size: 14px;
  background-color: #fafafa;
  border-radius: 4px;

  &__amount {
    font-size: 16px;
    color: #f56c6c;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

