<template>
  <div class="page-container inbound-create-page">
    <el-card class="form-card" shadow="never">
      <div class="card-title">新建入库单</div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="inbound-form"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="供应商" prop="supplierId">
              <el-select
                v-model="form.supplierId"
                placeholder="请选择供应商"
                clearable
                filterable
                class="full-width"
              >
                <el-option
                  v-for="supplier in supplierOptions"
                  :key="supplier.id"
                  :label="supplier.name"
                  :value="supplier.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="入库仓库" prop="warehouseId">
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
            <el-form-item label="入库类型" prop="inboundType">
              <el-select v-model="form.inboundType" class="full-width">
                <el-option
                  v-for="item in inboundTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="备注" prop="remark">
              <el-input
                v-model="form.remark"
                placeholder="选填，最多 255 字"
                maxlength="255"
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
          :disabled="saving || submitting || !items.length"
          @click="handleClearItems"
        >
          清空明细
        </el-button>
        <span class="scan-bar__tip">扫码自动追加明细，已存在的配件数量 +1</span>
      </div>

      <el-table
        :data="items"
        row-key="key"
        border
        empty-text="请扫描配件条码，或点击「手动添加」选择配件"
        class="items-table"
      >
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
        <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="spec" label="规格型号" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="数量" width="140" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.quantity"
              :min="row.trackByItem === 1 ? 1 : 0.01"
              :max="999999"
              :precision="row.trackByItem === 1 ? 0 : 2"
              :step="1"
              :value-on-clear="1"
              controls-position="right"
              size="small"
              class="number-input"
            />
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column label="单价" width="140" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.unitPrice"
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
          <template #default="{ row }">{{ formatMoney(rowAmount(row as InboundItemRow)) }}</template>
        </el-table-column>
        <el-table-column label="批次号" width="150">
          <template #default="{ row }">
            <el-input v-model="row.batchNo" maxlength="50" placeholder="选填" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="生产日期" width="150">
          <template #default="{ row }">
            <el-date-picker
              v-model="row.productionDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选填"
              size="small"
              class="full-width"
            />
          </template>
        </el-table-column>
        <el-table-column label="到期日期" width="150">
          <template #default="{ row }">
            <el-date-picker
              v-model="row.expireDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选填"
              size="small"
              class="full-width"
            />
          </template>
        </el-table-column>
        <el-table-column label="库位" width="170">
          <template #default="{ row }">
            <el-select
              v-model="row.locationId"
              placeholder="选填"
              clearable
              filterable
              size="small"
              :disabled="!form.warehouseId"
              class="full-width"
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
        <el-table-column label="操作" width="70" align="center" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeItem($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="items-summary">
        <span>明细 {{ items.length }} 项</span>
        <span>
          合计金额：<b class="items-summary__amount">{{ formatMoney(totalAmount) }}</b>
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
  createInboundOrder,
  scanPart,
  submitInboundOrder,
  type InboundOrderPayload,
  type InboundType,
  type ScanPartResult
} from '@/api/inbound'
import type { Part } from '@/api/part'
import { getAllSuppliers, type Supplier } from '@/api/supplier'
import {
  getAllWarehouses,
  getAllWarehouseLocations,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import PartSelect from '@/components/PartSelect.vue'
import ScanInput from '@/components/ScanInput.vue'
import { formatMoney } from '@/utils/format'

interface InboundForm {
  supplierId: number | undefined
  warehouseId: number | undefined
  inboundType: InboundType
  remark: string
}

/** 明细编辑行 */
interface InboundItemRow {
  key: number
  partId: number
  partCode: string
  partName: string
  spec: string
  unit: string
  trackByItem: number
  quantity: number
  unitPrice: number
  batchNo: string
  productionDate: string
  expireDate: string
  locationId: number | undefined
  scanCode: string | null
}

/** 扫码 / 手动选择得到的配件最小信息 */
interface ScannedPart {
  partId: number
  partCode: string
  partName: string
  spec: string
  unit: string
  trackByItem: number
}

const inboundTypeOptions: Array<{ label: string; value: InboundType }> = [
  { label: '采购入库', value: 'PURCHASE' },
  { label: '退货入库', value: 'RETURN' },
  { label: '调拨入库', value: 'TRANSFER' },
  { label: '调整入库', value: 'ADJUST' }
]

const router = useRouter()

const formRef = ref<FormInstance>()
const form = reactive<InboundForm>({
  supplierId: undefined,
  warehouseId: undefined,
  inboundType: 'PURCHASE',
  remark: ''
})

const rules: FormRules<InboundForm> = {
  warehouseId: [{ required: true, message: '请选择入库仓库', trigger: 'change' }],
  inboundType: [{ required: true, message: '请选择入库类型', trigger: 'change' }],
  remark: [{ max: 255, message: '备注不能超过 255 个字符', trigger: 'blur' }]
}

const items = ref<InboundItemRow[]>([])
const supplierOptions = ref<Supplier[]>([])
const warehouseOptions = ref<Warehouse[]>([])
const locations = ref<WarehouseLocation[]>([])

const partDialogVisible = ref(false)
const saving = ref(false)
const submitting = ref(false)
const scanning = ref(false)

let nextRowKey = 1

const selectedPartIds = computed(() => items.value.map((row) => row.partId))

const totalAmount = computed(() =>
  items.value.reduce((sum, row) => sum + rowAmount(row), 0)
)

/** 明细行金额：数量 × 单价，保留两位小数 */
function rowAmount(row: InboundItemRow): number {
  const quantity = Number(row.quantity)
  const price = Number(row.unitPrice)
  if (!Number.isFinite(quantity) || !Number.isFinite(price)) {
    return 0
  }
  return Number((quantity * price).toFixed(2))
}

async function loadOptions() {
  try {
    const [suppliers, warehouses] = await Promise.all([
      getAllSuppliers(1),
      getAllWarehouses(1)
    ])
    supplierOptions.value = suppliers
    warehouseOptions.value = warehouses
  } catch {
    // 错误提示由 request 拦截器统一处理
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
    if (oldValue !== undefined && value !== oldValue) {
      // 切换仓库后清空已选库位，避免跨仓库脏数据
      items.value.forEach((row) => {
        row.locationId = undefined
      })
    }
    if (typeof value === 'number' && value > 0) {
      void loadLocations(value)
    } else {
      locations.value = []
    }
  }
)

onMounted(() => {
  void loadOptions()
})

/** 扫码返回值归一化，兼容 partId / id 两种字段命名 */
function normalizeScanResult(data: ScanPartResult, code: string): ScannedPart | null {
  const partId = data.partId ?? data.id
  if (!partId) {
    return null
  }
  return {
    partId,
    partCode: data.partCode || code,
    partName: data.partName || '-',
    spec: data.spec ?? '',
    unit: data.unit || '个',
    trackByItem: data.trackByItem ?? 0
  }
}

/**
 * 追加明细：同一配件已存在时数量 +1，否则新增一行。
 * @param part 配件最小信息
 * @param scanCode 本次扫码内容（手动添加为空）
 * @returns added 新增成功；incremented 数量已累加
 */
function addPart(part: ScannedPart, scanCode: string | null = null): 'added' | 'incremented' {
  const existing = items.value.find((row) => row.partId === part.partId)
  if (existing) {
    const quantity = Number(existing.quantity)
    existing.quantity = (Number.isFinite(quantity) ? quantity : 0) + 1
    existing.scanCode = existing.scanCode ?? scanCode
    return 'incremented'
  }

  items.value.push({
    key: nextRowKey++,
    partId: part.partId,
    partCode: part.partCode,
    partName: part.partName,
    spec: part.spec,
    unit: part.unit,
    trackByItem: part.trackByItem,
    quantity: 1,
    unitPrice: 0,
    batchNo: '',
    productionDate: '',
    expireDate: '',
    locationId: undefined,
    scanCode
  })
  return 'added'
}

async function handleScan(code: string) {
  if (scanning.value) {
    return
  }
  scanning.value = true
  try {
    const res = await scanPart(code)
    const part = normalizeScanResult(res.data, code)
    if (!part) {
      ElMessage.warning('扫码结果无法识别，请使用「手动添加」选择配件')
      return
    }
    const result = addPart(part, code.trim())
    ElMessage.success(
      result === 'incremented'
        ? `${part.partName} 已在明细中，数量 +1`
        : `已添加 ${part.partName}`
    )
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '扫码失败，请重试')
  } finally {
    scanning.value = false
  }
}

function openPartSelect() {
  partDialogVisible.value = true
}

function handlePartsSelected(parts: Part[]) {
  if (!parts.length) {
    return
  }

  parts.forEach((part) => {
    addPart({
      partId: part.id,
      partCode: part.partCode,
      partName: part.partName,
      spec: part.spec ?? '',
      unit: part.unit,
      trackByItem: part.trackByItem
    })
  })

  ElMessage.success(`已添加 ${parts.length} 个配件`)
}

function removeItem(index: number) {
  items.value.splice(index, 1)
}

async function handleClearItems() {
  if (!items.value.length) {
    return
  }

  const confirmed = await ElMessageBox.confirm('确认清空全部入库明细？', '清空确认', {
    type: 'warning',
    confirmButtonText: '清空',
    cancelButtonText: '取消'
  })
    .then(() => true)
    .catch(() => false)

  if (confirmed) {
    items.value = []
  }
}

/** 明细校验：数量必须大于 0，单价不能小于 0 */
function validateItems(): boolean {
  for (let index = 0; index < items.value.length; index += 1) {
    const row = items.value[index]
    if (!row) {
      continue
    }
    const quantity = Number(row.quantity)
    const price = Number(row.unitPrice)
    if (!Number.isFinite(quantity) || quantity <= 0) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」数量必须大于 0`)
      return false
    }
    if (row.trackByItem === 1 && !Number.isInteger(quantity)) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」按件追踪，数量必须为整数`)
      return false
    }
    if (!Number.isFinite(price) || price < 0) {
      ElMessage.warning(`第 ${index + 1} 行「${row.partName}」单价不能小于 0`)
      return false
    }
  }
  return true
}

function buildPayload(warehouseId: number): InboundOrderPayload {
  return {
    supplierId: form.supplierId ?? null,
    warehouseId,
    inboundType: form.inboundType,
    remark: form.remark.trim() || null,
    items: items.value.map((row) => ({
      partId: row.partId,
      quantity: Number(row.quantity),
      unit: row.unit || null,
      unitPrice: Number(row.unitPrice),
      amount: rowAmount(row),
      batchNo: row.batchNo.trim() || null,
      productionDate: row.productionDate || null,
      expireDate: row.expireDate || null,
      locationId: row.locationId ?? null,
      trackByItem: row.trackByItem,
      scanCode: row.scanCode
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
    ElMessage.warning('请选择入库仓库')
    return
  }
  if (!items.value.length) {
    ElMessage.warning('请先扫码或手动添加入库明细')
    return
  }
  if (!validateItems()) {
    return
  }

  const loadingRef = submitAfter ? submitting : saving
  loadingRef.value = true
  try {
    const created = await createInboundOrder(buildPayload(form.warehouseId))
    if (submitAfter) {
      await submitInboundOrder(created.data.id)
      ElMessage.success('入库单已创建并提交审核')
    } else {
      ElMessage.success('入库单草稿保存成功')
    }
    void router.push(`/inbound/${created.data.id}`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loadingRef.value = false
  }
}

function goBack() {
  void router.push('/inbound')
}
</script>

<style scoped lang="scss">
.inbound-create-page {
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

.inbound-form {
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

