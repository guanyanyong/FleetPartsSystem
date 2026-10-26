<template>
  <div class="page-container location-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="所属仓库">
          <el-select
            v-model="search.warehouseId"
            clearable
            filterable
            placeholder="请选择仓库"
            class="filter-select"
          >
            <el-option
              v-for="warehouse in warehouses"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="库位编码">
          <el-input
            v-model="search.keyword"
            placeholder="请输入库位编码"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" clearable placeholder="全部状态" class="filter-select">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
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
        <span class="table-toolbar__title">库位列表</span>
        <div>
          <el-button :icon="Refresh" @click="loadData">刷新</el-button>
          <el-button :icon="Files" @click="openBatchDialog">批量生成</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增库位</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column label="所属仓库" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ warehouseNameOf(row.warehouseId) }}</template>
        </el-table-column>
        <el-table-column
          prop="locationCode"
          label="库位编码"
          min-width="160"
          show-overflow-tooltip
        />
        <el-table-column label="二维码内容" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.locationQrcode || '-' }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" effect="plain">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as WarehouseLocation)">编辑</el-button>
            <el-button link type="primary" @click="openQrcode(row as WarehouseLocation)">二维码</el-button>
            <el-button link type="danger" @click="handleDelete(row as WarehouseLocation)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无库位数据" />
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

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      :close-on-click-modal="false"
      @closed="formRef?.clearValidate()"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="所属仓库" prop="warehouseId">
          <el-select
            v-model="form.warehouseId"
            filterable
            placeholder="请选择仓库"
            class="full-width"
          >
            <el-option
              v-for="warehouse in warehouses"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="库位编码" prop="locationCode">
          <el-input v-model="form.locationCode" maxlength="50" placeholder="如：A-01-03" />
        </el-form-item>
        <el-form-item label="二维码内容" prop="locationQrcode">
          <el-input
            v-model="form.locationQrcode"
            maxlength="255"
            placeholder="可选，填写库位二维码标识，如 A-01-03"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="2"
            maxlength="100"
            show-word-limit
            placeholder="请输入备注"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog
      v-model="batchVisible"
      title="批量生成库位"
      width="560px"
      :close-on-click-modal="false"
      @closed="batchFormRef?.clearValidate()"
    >
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-width="100px">
        <el-form-item label="所属仓库" prop="warehouseId">
          <el-select
            v-model="batchForm.warehouseId"
            filterable
            placeholder="请选择仓库"
            class="full-width"
          >
            <el-option
              v-for="warehouse in warehouses"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="编码前缀" prop="prefix">
          <el-input v-model="batchForm.prefix" maxlength="40" placeholder="如：A-01-" />
        </el-form-item>
        <el-form-item label="起止序号" prop="startNo">
          <div class="batch-range">
            <el-input-number
              v-model="batchForm.startNo"
              :min="1"
              :precision="0"
              controls-position="right"
            />
            <span class="batch-range__sep">至</span>
            <el-input-number
              v-model="batchForm.endNo"
              :min="1"
              :precision="0"
              controls-position="right"
            />
          </div>
        </el-form-item>
        <el-form-item label="序号位数" prop="padLength">
          <div class="batch-pad">
            <el-input-number
              v-model="batchForm.padLength"
              :min="1"
              :max="6"
              :precision="0"
              controls-position="right"
            />
            <span class="form-tip">不足位数时左侧补 0，如 3 位生成 A-01-001</span>
          </div>
        </el-form-item>
        <el-form-item label="生成预览">
          <div class="batch-preview">
            <span v-if="batchCodes.length === 0" class="form-tip">请填写编码前缀与起止序号</span>
            <template v-else>
              <el-tag
                v-for="code in previewCodes"
                :key="code"
                type="info"
                effect="plain"
                class="batch-preview__tag"
              >
                {{ code }}
              </el-tag>
              <span v-if="batchCodes.length > previewCodes.length" class="form-tip">
                等共 {{ batchCodes.length }} 个库位
              </span>
            </template>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="batchSubmitting"
          :disabled="batchCodes.length === 0"
          @click="handleBatchSubmit"
        >
          开始生成
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qrVisible" title="库位二维码" width="380px" destroy-on-close align-center>
      <div v-if="qrRow" class="qr-dialog">
        <p class="qr-dialog__title">{{ qrRow.locationCode }}</p>
        <p class="form-tip">{{ warehouseNameOf(qrRow.warehouseId) }}</p>
        <QrCode ref="qrRef" :value="qrcodeContent(qrRow)" :size="200" />
        <p class="qr-dialog__value">{{ qrcodeContent(qrRow) }}</p>
      </div>
      <template #footer>
        <el-button @click="qrVisible = false">关闭</el-button>
        <el-button type="primary" :icon="Printer" @click="handlePrintQrcode">打印二维码</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

import { Files, Plus, Printer, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createWarehouseLocation,
  deleteWarehouseLocation,
  getAllWarehouses,
  getWarehouseLocationList,
  updateWarehouseLocation,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import QrCode from '@/components/QrCode.vue'
import { formatDate } from '@/utils/format'

interface LocationForm {
  warehouseId: number | undefined
  locationCode: string
  locationQrcode: string
  remark: string
  status: number
}

interface BatchForm {
  warehouseId: number | undefined
  prefix: string
  startNo: number | undefined
  endNo: number | undefined
  padLength: number
}

/** 单次批量生成上限，避免误操作产生大量请求 */
const MAX_BATCH_COUNT = 100
/** 预览标签最多展示数量 */
const PREVIEW_LIMIT = 12

const search = reactive<{
  warehouseId: number | undefined
  keyword: string
  status: number | undefined
}>({
  warehouseId: undefined,
  keyword: '',
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<WarehouseLocation[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)

const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增库位' : '编辑库位'))

function createEmptyForm(): LocationForm {
  return {
    warehouseId: search.warehouseId,
    locationCode: '',
    locationQrcode: '',
    remark: '',
    status: 1
  }
}

const form = reactive<LocationForm>(createEmptyForm())

const rules: FormRules<LocationForm> = {
  warehouseId: [{ required: true, message: '请选择所属仓库', trigger: 'change' }],
  locationCode: [
    { required: true, message: '请输入库位编码', trigger: 'blur' },
    { max: 50, message: '库位编码不能超过 50 个字符', trigger: 'blur' }
  ],
  locationQrcode: [{ max: 255, message: '二维码内容不能超过 255 个字符', trigger: 'blur' }],
  remark: [{ max: 100, message: '备注不能超过 100 个字符', trigger: 'blur' }]
}

function warehouseNameOf(warehouseId: number) {
  return warehouses.value.find((item) => item.id === warehouseId)?.name ?? `仓库 #${warehouseId}`
}

async function loadWarehouses() {
  try {
    warehouses.value = await getAllWarehouses()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getWarehouseLocationList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      warehouseId: search.warehouseId ?? undefined,
      keyword: search.keyword.trim() || undefined,
      status: search.status ?? undefined
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
  search.warehouseId = undefined
  search.keyword = ''
  search.status = undefined
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  Object.assign(form, createEmptyForm())
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: WarehouseLocation) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, createEmptyForm(), {
    warehouseId: row.warehouseId,
    locationCode: row.locationCode,
    locationQrcode: row.locationQrcode ?? '',
    remark: row.remark ?? '',
    status: row.status
  })
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

async function handleSubmit() {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid || !form.warehouseId) {
    return
  }

  const qrcode = form.locationQrcode.trim()
  const remark = form.remark.trim()
  const payload = {
    warehouseId: form.warehouseId,
    locationCode: form.locationCode.trim(),
    locationQrcode: qrcode === '' ? null : qrcode,
    remark: remark === '' ? null : remark,
    status: form.status
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createWarehouseLocation(payload)
      ElMessage.success('库位新增成功')
    } else if (editingId.value !== null) {
      await updateWarehouseLocation(editingId.value, payload)
      ElMessage.success('库位更新成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: WarehouseLocation) {
  try {
    await ElMessageBox.confirm(
      `确定要删除库位「${row.locationCode}」吗？库位仍有库存时将无法删除。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  try {
    await deleteWarehouseLocation(row.id)
    ElMessage.success('删除成功')
    if (tableData.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理（仍被引用时返回 409）
  }
}

// ---------------------------------------------------------------- 二维码

const qrVisible = ref(false)
const qrRow = ref<WarehouseLocation | null>(null)
const qrRef = ref<{ getDataUrl: () => string } | null>(null)

/** 二维码内容优先使用库位自填的二维码值，未填写时回退到库位编码 */
function qrcodeContent(row: WarehouseLocation) {
  return row.locationQrcode || row.locationCode
}

function openQrcode(row: WarehouseLocation) {
  qrRow.value = row
  qrVisible.value = true
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** 打开独立打印窗口，仅打印库位标签（标题 + 仓库 + 二维码 + 内容） */
function handlePrintQrcode() {
  const row = qrRow.value
  if (!row) {
    return
  }
  const dataUrl = qrRef.value?.getDataUrl() ?? ''
  if (!dataUrl) {
    ElMessage.warning('二维码尚未生成，请稍后重试')
    return
  }

  const printWindow = window.open('', '_blank', 'width=420,height=560')
  if (!printWindow) {
    ElMessage.warning('浏览器阻止了打印窗口，请允许本站弹出窗口后重试')
    return
  }

  const title = escapeHtml(row.locationCode)
  const warehouseName = escapeHtml(warehouseNameOf(row.warehouseId))
  const content = escapeHtml(qrcodeContent(row))

  printWindow.document.write(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>库位二维码 - ${title}</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 24px;
    font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;
    color: #303133;
    text-align: center;
  }
  .title { font-size: 18px; font-weight: 600; margin-bottom: 4px; word-break: break-all; }
  .warehouse { font-size: 13px; color: #606266; margin-bottom: 12px; word-break: break-all; }
  .qr { width: 200px; height: 200px; }
  .content { margin-top: 8px; font-size: 14px; font-weight: 600; word-break: break-all; }
  @page { margin: 8mm; }
</style>
</head>
<body>
  <div class="title">${title}</div>
  <div class="warehouse">${warehouseName}</div>
  <img class="qr" src="${dataUrl}" alt="库位二维码" />
  <div class="content">${content}</div>
</body>
</html>`)
  printWindow.document.close()
  printWindow.focus()
  // 等待二维码图片解码完成后再打印，避免标签上出现空白二维码
  printWindow.setTimeout(() => {
    const qrImage = printWindow.document.querySelector<HTMLImageElement>('.qr')
    let printed = false
    const doPrint = () => {
      if (printed) {
        return
      }
      printed = true
      printWindow.print()
      printWindow.close()
    }
    if (qrImage && !qrImage.complete) {
      qrImage.addEventListener('load', doPrint, { once: true })
      qrImage.addEventListener('error', doPrint, { once: true })
      // 兜底：图片事件未触发时仍执行打印
      printWindow.setTimeout(doPrint, 1500)
      return
    }
    doPrint()
  }, 100)
}

// ---------------------------------------------------------------- 批量生成

const batchFormRef = ref<FormInstance>()
const batchVisible = ref(false)
const batchSubmitting = ref(false)

const batchForm = reactive<BatchForm>({
  warehouseId: undefined,
  prefix: '',
  startNo: 1,
  endNo: 10,
  padLength: 2
})

const batchRules: FormRules<BatchForm> = {
  warehouseId: [{ required: true, message: '请选择所属仓库', trigger: 'change' }],
  prefix: [{ required: true, message: '请输入编码前缀', trigger: 'blur' }],
  startNo: [{ required: true, message: '请输入起始序号', trigger: 'blur' }],
  endNo: [
    { required: true, message: '请输入结束序号', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        const startNo = batchForm.startNo ?? 0
        if (typeof value === 'number' && value < startNo) {
          callback(new Error('结束序号不能小于起始序号'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

const batchCount = computed(() => {
  const startNo = batchForm.startNo ?? 0
  const endNo = batchForm.endNo ?? 0
  if (startNo <= 0 || endNo < startNo) {
    return 0
  }
  return endNo - startNo + 1
})

/** 按前缀 + 序号（左补 0）生成库位编码，最多生成 MAX_BATCH_COUNT 条 */
const batchCodes = computed(() => {
  const prefix = batchForm.prefix.trim()
  const startNo = batchForm.startNo ?? 0
  const padLength = batchForm.padLength || 1
  const count = Math.min(batchCount.value, MAX_BATCH_COUNT)
  if (!prefix || count <= 0) {
    return []
  }
  return Array.from(
    { length: count },
    (_, index) => `${prefix}${String(startNo + index).padStart(padLength, '0')}`
  )
})

const previewCodes = computed(() => batchCodes.value.slice(0, PREVIEW_LIMIT))

function openBatchDialog() {
  batchForm.warehouseId = search.warehouseId
  batchForm.prefix = ''
  batchForm.startNo = 1
  batchForm.endNo = 10
  batchForm.padLength = 2
  batchVisible.value = true
  void nextTick(() => batchFormRef.value?.clearValidate())
}

async function handleBatchSubmit() {
  if (!batchFormRef.value || !batchForm.warehouseId) {
    return
  }
  const valid = await batchFormRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (batchCount.value > MAX_BATCH_COUNT) {
    ElMessage.warning(`单次最多生成 ${MAX_BATCH_COUNT} 个库位，请缩小序号范围`)
    return
  }
  const codes = batchCodes.value
  if (codes.length === 0) {
    ElMessage.warning('请填写有效的编码前缀与起止序号')
    return
  }

  batchSubmitting.value = true
  let createdCount = 0
  let failedCode: string | null = null
  try {
    // 后端未提供批量接口，这里逐条创建，遇到失败立即停止避免产生半成品数据
    for (const locationCode of codes) {
      try {
        await createWarehouseLocation({
          warehouseId: batchForm.warehouseId,
          locationCode,
          status: 1
        })
        createdCount += 1
      } catch {
        failedCode = locationCode
        break
      }
    }
  } finally {
    batchSubmitting.value = false
  }

  if (failedCode) {
    ElMessage.warning(`批量生成中断：已创建 ${createdCount} 个，库位 ${failedCode} 创建失败`)
  } else {
    ElMessage.success(`已成功生成 ${createdCount} 个库位`)
    batchVisible.value = false
  }
  await loadData()
}

onMounted(() => {
  void loadWarehouses()
  void loadData()
})
</script>

<style scoped lang="scss">
.location-page {
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

.filter-select {
  width: 160px;
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

.full-width {
  width: 100%;
}

.qr-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 4px 0;

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    text-align: center;
    word-break: break-all;
  }

  &__value {
    font-size: 13px;
    color: var(--el-text-color-regular);
    text-align: center;
    word-break: break-all;
  }

  .form-tip {
    text-align: center;
  }
}

.batch-range {
  display: flex;
  align-items: center;
  gap: 8px;

  &__sep {
    color: var(--el-text-color-secondary);
  }
}

.batch-pad {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 24px;

  &__tag {
    font-family: var(--el-font-family);
  }
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}
</style>


