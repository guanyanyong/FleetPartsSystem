<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="工单号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="车辆">
          <el-select v-model="search.vehicleId" placeholder="全部车辆" clearable filterable class="filter-select">
            <el-option
              v-for="item in vehicles"
              :key="item.id"
              :label="item.plateNo"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="维修类型">
          <el-select v-model="search.repairType" placeholder="全部" clearable class="filter-select">
            <el-option
              v-for="(label, key) in REPAIR_TYPE_MAP"
              :key="key"
              :label="label"
              :value="key"
            />
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
        <span class="table-toolbar__title">维修工单</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新建工单</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="orderNo" label="工单号" width="170" show-overflow-tooltip />
        <el-table-column label="车牌号" width="120">
          <template #default="{ row }">{{ row.plateNo || '-' }}</template>
        </el-table-column>
        <el-table-column label="维修类型" width="100" align="center">
          <template #default="{ row }">
            {{ REPAIR_TYPE_MAP[row.repairType] || row.repairType }}
          </template>
        </el-table-column>
        <el-table-column label="故障描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="维修负责人" width="120">
          <template #default="{ row }">{{ row.repairManName || '-' }}</template>
        </el-table-column>
        <el-table-column label="进厂时间" width="160">
          <template #default="{ row }">{{ formatDate(row.inAt) }}</template>
        </el-table-column>
        <el-table-column label="配件成本" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.totalPartsCost) }}</template>
        </el-table-column>
        <el-table-column label="工时费" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.totalLaborCost) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusOf(row.status).type" effect="plain">
              {{ statusOf(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as WorkOrderOption)">详情</el-button>
            <el-button
              v-if="row.status === 1"
              link
              type="primary"
              @click="openEdit(row as WorkOrderOption)"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无维修工单" />
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
      :title="editingId ? '编辑工单' : '新建维修工单'"
      width="680px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item v-if="!editingId" label="车辆" prop="vehicleId">
          <el-select v-model="form.vehicleId" placeholder="请选择车辆" filterable class="w-full">
            <el-option
              v-for="item in vehicles"
              :key="item.id"
              :label="item.plateNo"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="车辆">
          <el-input :model-value="editingPlateNo" disabled />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="维修类型" prop="repairType">
              <el-select v-model="form.repairType" class="w-full">
                <el-option
                  v-for="(label, key) in REPAIR_TYPE_MAP"
                  :key="key"
                  :label="label"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="维修负责人">
              <el-select
                v-model="form.repairManId"
                placeholder="选填"
                clearable
                filterable
                class="w-full"
              >
                <el-option
                  v-for="item in repairMen"
                  :key="item.id"
                  :label="item.realName || item.username"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="进厂时间">
              <el-date-picker
                v-model="form.inAt"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                placeholder="选择时间"
                class="w-full"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="故障描述">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>

    </el-dialog>


    <el-drawer v-model="detailVisible" title="工单详情" size="860px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="工单号">{{ detail.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusOf(detail.status).type" effect="plain">
              {{ statusOf(detail.status).label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="车牌号">{{ detail.plateNo || '-' }}</el-descriptions-item>
          <el-descriptions-item label="维修类型">
            {{ REPAIR_TYPE_MAP[detail.repairType] || detail.repairType }}
          </el-descriptions-item>
          <el-descriptions-item label="维修负责人">
            {{ detail.repairManName || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="进厂时间">{{ formatDate(detail.inAt) }}</el-descriptions-item>
          <el-descriptions-item label="出厂时间">{{ formatDate(detail.outAt) }}</el-descriptions-item>
          <el-descriptions-item label="配件成本">
            {{ formatMoney(detail.totalPartsCost, true) }}
          </el-descriptions-item>
          <el-descriptions-item label="工时费">
            {{ formatMoney(detail.totalLaborCost, true) }}
          </el-descriptions-item>
          <el-descriptions-item label="合计">
            {{ formatMoney(totalCostOf(detail), true) }}
          </el-descriptions-item>
          <el-descriptions-item label="故障描述" :span="2">
            {{ detail.description || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ detail.remark || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="drawer-title">领料记录</div>
        <el-table :data="detail.parts" border max-height="320">
          <el-table-column prop="partCode" label="配件编码" width="130" show-overflow-tooltip />
          <el-table-column prop="partName" label="配件名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="规格" min-width="110" show-overflow-tooltip>
            <template #default="{ row }">{{ row.spec || '-' }}</template>
          </el-table-column>
          <el-table-column label="数量" width="90" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="单位" width="70" align="center">
            <template #default="{ row }">{{ row.unit || '-' }}</template>
          </el-table-column>
          <el-table-column label="成本" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.cost) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无领料记录（出库审核通过后自动写入）" :image-size="70" />
          </template>
        </el-table>

        <div class="drawer-actions">
          <el-button v-if="detail.status === 1" @click="openEdit(detail)">编辑</el-button>
          <el-button v-if="detail.status === 1" type="primary" @click="handleStart(detail)">
            开始维修
          </el-button>
          <el-button v-if="detail.status === 2" type="success" @click="handleFinish(detail)">
            完工
          </el-button>
          <el-button v-if="detail.status === 3" type="success" @click="openSettle(detail)">
            结算
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="settleVisible" title="工单结算" width="460px" :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="配件成本">
          <span>{{ formatMoney(settleTarget?.totalPartsCost, true) }}</span>
        </el-form-item>
        <el-form-item label="工时费" required>
          <el-input-number
            v-model="settleForm.totalLaborCost"
            :min="0"
            :precision="2"
            :controls="false"
            class="w-full"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="settleForm.remark" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settleVisible = false">取消</el-button>
        <el-button type="primary" :loading="settling" @click="handleSettle">确认结算</el-button>
      </template>
    </el-dialog>
  </div>
</template>


<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import { getUserList, type UserOption } from '@/api/user'
import { getAllVehicles, type VehicleOption } from '@/api/vehicle'
import {
  createWorkOrder,
  finishWorkOrder,
  getWorkOrderDetail,
  getWorkOrderList,
  settleWorkOrder,
  startWorkOrder,
  updateWorkOrder,
  type WorkOrderDetail,
  type WorkOrderOption,
  type WorkOrderPayload,
  type WorkOrderQuery,
  type WorkOrderUpdatePayload
} from '@/api/workOrder'
import { useUserStore } from '@/stores/user'
import { formatDate, formatMoney, formatQuantity } from '@/utils/format'

const route = useRoute()
const userStore = useUserStore()

type TagType = 'info' | 'warning' | 'primary' | 'success'

const STATUS_MAP: Record<number, { label: string; type: TagType }> = {
  1: { label: '待修', type: 'info' },
  2: { label: '维修中', type: 'warning' },
  3: { label: '已完工', type: 'primary' },
  4: { label: '已结算', type: 'success' }
}

const REPAIR_TYPE_MAP: Record<string, string> = {
  MAINTENANCE: '保养',
  REPAIR: '维修',
  ACCIDENT: '事故'
}

interface WorkOrderForm {
  vehicleId: number | undefined
  repairType: string
  description: string
  repairManId: number | undefined
  inAt: string
  remark: string
}

const search = reactive<WorkOrderQuery>({
  keyword: '',
  vehicleId: undefined,
  repairType: undefined,
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<WorkOrderOption[]>([])
const vehicles = ref<VehicleOption[]>([])
const repairMen = ref<UserOption[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const editingPlateNo = ref('')
const formRef = ref<FormInstance>()
const form = reactive<WorkOrderForm>(emptyForm())

const detailVisible = ref(false)
const detail = ref<WorkOrderDetail | null>(null)

const settleVisible = ref(false)
const settling = ref(false)
const settleTarget = ref<WorkOrderDetail | null>(null)
const settleForm = reactive<{ totalLaborCost: number | undefined; remark: string }>({
  totalLaborCost: undefined,
  remark: ''
})

const rules: FormRules = {
  vehicleId: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  repairType: [{ required: true, message: '请选择维修类型', trigger: 'change' }]
}

const canLoadUsers = computed(() => ['admin', 'leader'].includes(userStore.role))

function emptyForm(): WorkOrderForm {
  return {
    vehicleId: undefined,
    repairType: 'REPAIR',
    description: '',
    repairManId: undefined,
    inAt: '',
    remark: ''
  }
}

function statusOf(status: number) {
  return STATUS_MAP[status] ?? { label: '未知', type: 'info' as TagType }
}

function totalCostOf(row: WorkOrderOption): number {
  const parts = Number(row.totalPartsCost ?? 0)
  const labor = Number(row.totalLaborCost ?? 0)
  return parts + labor
}

async function loadOptions() {
  try {
    vehicles.value = await getAllVehicles()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
  if (!canLoadUsers.value) {
    return
  }
  try {
    const res = await getUserList({ page: 1, pageSize: 200, status: 1 })
    repairMen.value = res.data.list
  } catch {
    // 非管理员角色无用户查询权限，忽略即可
  }
}


async function loadData() {
  loading.value = true
  try {
    const res = await getWorkOrderList({
      ...search,
      keyword: search.keyword?.trim() || undefined,
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
  search.vehicleId = undefined
  search.repairType = undefined
  search.status = undefined
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function openCreate() {
  editingId.value = null
  editingPlateNo.value = ''
  Object.assign(form, emptyForm())
  form.inAt = formatDate(new Date())
  dialogVisible.value = true
}

function openEdit(row: WorkOrderOption) {
  editingId.value = row.id
  editingPlateNo.value = row.plateNo || '-'
  Object.assign(form, {
    vehicleId: row.vehicleId,
    repairType: row.repairType,
    description: row.description ?? '',
    repairManId: row.repairManId ?? undefined,
    inAt: row.inAt ?? '',
    remark: row.remark ?? ''
  })
  dialogVisible.value = true
}

function resetForm() {
  editingId.value = null
  editingPlateNo.value = ''
  Object.assign(form, emptyForm())
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      const payload: WorkOrderUpdatePayload = {
        repairType: form.repairType,
        description: form.description.trim() || null,
        repairManId: form.repairManId ?? null,
        inAt: form.inAt || null,
        remark: form.remark.trim() || null
      }
      const res = await updateWorkOrder(editingId.value, payload)
      ElMessage.success('工单已更新')
      if (detailVisible.value) {
        detail.value = res.data
      }
    } else {
      const payload: WorkOrderPayload = {
        vehicleId: form.vehicleId as number,
        repairType: form.repairType,
        description: form.description.trim() || null,
        repairManId: form.repairManId ?? null,
        inAt: form.inAt || null,
        remark: form.remark.trim() || null
      }
      const res = await createWorkOrder(payload)
      ElMessage.success('工单已创建')
      detail.value = res.data
      detailVisible.value = true
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function openDetail(row: WorkOrderOption) {
  try {
    const res = await getWorkOrderDetail(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleStart(row: WorkOrderDetail) {
  try {
    await ElMessageBox.confirm(`确认开始维修工单「${row.orderNo}」吗？`, '开始维修', {
      type: 'warning'
    })
    const res = await startWorkOrder(row.id)
    detail.value = res.data
    ElMessage.success('工单已进入维修中')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

async function handleFinish(row: WorkOrderDetail) {
  try {
    await ElMessageBox.confirm(
      `确认工单「${row.orderNo}」已完工吗？系统将自动汇总领料成本。`,
      '完工确认',
      { type: 'warning' }
    )
    const res = await finishWorkOrder(row.id)
    detail.value = res.data
    ElMessage.success('工单已完工')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

function openSettle(row: WorkOrderDetail) {
  settleTarget.value = row
  settleForm.totalLaborCost = row.totalLaborCost === null ? 0 : Number(row.totalLaborCost)
  settleForm.remark = ''
  settleVisible.value = true
}

async function handleSettle() {
  if (!settleTarget.value) {
    return
  }
  if (settleForm.totalLaborCost === undefined || settleForm.totalLaborCost === null) {
    ElMessage.warning('请填写工时费')
    return
  }
  settling.value = true
  try {
    const res = await settleWorkOrder(
      settleTarget.value.id,
      settleForm.totalLaborCost,
      settleForm.remark.trim() || undefined
    )
    detail.value = res.data
    settleVisible.value = false
    ElMessage.success('工单已结算')
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    settling.value = false
  }
}

watch(
  () => route.query.vehicleId,
  (value) => {
    search.vehicleId = value ? Number(value) : undefined
    pagination.page = 1
    void loadData()
  }
)

onMounted(async () => {
  const vehicleId = route.query.vehicleId
  if (vehicleId) {
    search.vehicleId = Number(vehicleId)
  }
  await loadOptions()
  await loadData()
})
</script>

<style scoped lang="scss">
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

