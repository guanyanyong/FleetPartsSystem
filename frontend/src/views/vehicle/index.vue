<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="车牌号 / VIN / 发动机号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="车型">
          <el-select v-model="search.modelId" placeholder="全部车型" clearable filterable class="filter-select">
            <el-option
              v-for="item in models"
              :key="item.id"
              :label="`${item.brand} ${item.modelName}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input
            v-model="search.department"
            placeholder="所属部门"
            clearable
            @keyup.enter="handleSearch"
          />
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
        <span class="table-toolbar__title">车辆列表</span>
        <div class="table-toolbar__actions">
          <el-button :icon="Setting" @click="goModels">车型管理</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增车辆</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="plateNo" label="车牌号" width="130" />
        <el-table-column label="车型" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ [row.brand, row.modelName].filter(Boolean).join(' ') || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="VIN" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.vin || '-' }}</template>
        </el-table-column>
        <el-table-column label="所属部门" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusOf(row.status).type" effect="plain">
              {{ statusOf(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="里程(km)" width="120" align="right">
          <template #default="{ row }">{{ formatNumber(row.mileage) }}</template>
        </el-table-column>
        <el-table-column label="购置日期" width="120" align="center">
          <template #default="{ row }">{{ formatDay(row.purchaseDate) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as VehicleOption)">编辑</el-button>
            <el-button link type="primary" @click="openDetail(row as VehicleOption)">详情</el-button>
            <el-button link type="primary" @click="goWorkOrders(row as VehicleOption)">
              维修记录
            </el-button>
            <el-button link type="danger" @click="handleDelete(row as VehicleOption)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无车辆" />
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
      :title="editingId ? '编辑车辆' : '新增车辆'"
      width="720px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车牌号" prop="plateNo">
              <el-input v-model="form.plateNo" maxlength="20" placeholder="请输入车牌号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车型">
              <el-select v-model="form.modelId" placeholder="请选择车型" clearable filterable class="w-full">
                <el-option
                  v-for="item in models"
                  :key="item.id"
                  :label="`${item.brand} ${item.modelName}`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="VIN">
              <el-input v-model="form.vin" maxlength="50" placeholder="车架号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发动机号">
              <el-input v-model="form.engineNo" maxlength="50" placeholder="发动机号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="购置日期">
              <el-date-picker
                v-model="form.purchaseDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                class="w-full"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属部门">
              <el-input v-model="form.department" maxlength="50" placeholder="车队 / 部门" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" class="w-full">
                <el-option
                  v-for="(item, key) in STATUS_MAP"
                  :key="key"
                  :label="item.label"
                  :value="Number(key)"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前里程">
              <el-input-number
                v-model="form.mileage"
                :min="0"
                :precision="0"
                :controls="false"
                class="w-full"
                placeholder="km"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="3"
                maxlength="255"
                show-word-limit
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="车辆详情" size="560px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="车牌号">{{ detail.plateNo }}</el-descriptions-item>
        <el-descriptions-item label="车型">
          {{ [detail.brand, detail.modelName].filter(Boolean).join(' ') || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="VIN">{{ detail.vin || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发动机号">{{ detail.engineNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="所属部门">{{ detail.department || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusOf(detail.status).type" effect="plain">
            {{ statusOf(detail.status).label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="当前里程">
          {{ formatNumber(detail.mileage) }} km
        </el-descriptions-item>
        <el-descriptions-item label="购置日期">{{ formatDay(detail.purchaseDate) }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ detail.remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(detail.createdAt) }}</el-descriptions-item>
      </el-descriptions>
      <div class="drawer-actions">
        <el-button v-if="detail" @click="goWorkOrders(detail)">查看维修记录</el-button>
        <el-button v-if="detail" type="primary" @click="openEdit(detail)">编辑</el-button>
      </div>
    </el-drawer>
  </div>
</template>


<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Plus, Refresh, Search, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createVehicle,
  deleteVehicle,
  getVehicleList,
  getVehicleModelList,
  updateVehicle,
  type VehicleModelOption,
  type VehicleOption,
  type VehiclePayload,
  type VehicleQuery
} from '@/api/vehicle'
import { formatDate, formatDay, formatNumber } from '@/utils/format'

const router = useRouter()

type TagType = 'success' | 'warning' | 'info' | 'danger'

const STATUS_MAP: Record<number, { label: string; type: TagType }> = {
  1: { label: '在用', type: 'success' },
  2: { label: '维修', type: 'warning' },
  3: { label: '停用', type: 'info' },
  4: { label: '报废', type: 'danger' }
}

interface VehicleForm {
  plateNo: string
  modelId: number | undefined
  vin: string
  engineNo: string
  purchaseDate: string | null
  department: string
  status: number
  mileage: number | undefined
  remark: string
}

const search = reactive<VehicleQuery>({
  keyword: '',
  modelId: undefined,
  department: '',
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<VehicleOption[]>([])
const models = ref<VehicleModelOption[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<VehicleForm>(emptyForm())

const detailVisible = ref(false)
const detail = ref<VehicleOption | null>(null)

const rules: FormRules = {
  plateNo: [{ required: true, message: '请输入车牌号', trigger: 'blur' }]
}

function emptyForm(): VehicleForm {
  return {
    plateNo: '',
    modelId: undefined,
    vin: '',
    engineNo: '',
    purchaseDate: null,
    department: '',
    status: 1,
    mileage: 0,
    remark: ''
  }
}

function statusOf(status: number) {
  return STATUS_MAP[status] ?? { label: '未知', type: 'info' as TagType }
}

async function loadModels() {
  try {
    const res = await getVehicleModelList({ page: 1, pageSize: 200, status: 1 })
    models.value = res.data.list
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getVehicleList({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      department: search.department?.trim() || undefined,
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
  search.modelId = undefined
  search.department = ''
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
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: VehicleOption) {
  editingId.value = row.id
  Object.assign(form, {
    plateNo: row.plateNo,
    modelId: row.modelId ?? undefined,
    vin: row.vin ?? '',
    engineNo: row.engineNo ?? '',
    purchaseDate: row.purchaseDate ?? null,
    department: row.department ?? '',
    status: row.status,
    mileage: row.mileage ?? 0,
    remark: row.remark ?? ''
  })
  dialogVisible.value = true
}

function resetForm() {
  editingId.value = null
  Object.assign(form, emptyForm())
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  const payload: VehiclePayload = {
    plateNo: form.plateNo.trim(),
    modelId: form.modelId ?? null,
    vin: form.vin.trim() || null,
    engineNo: form.engineNo.trim() || null,
    purchaseDate: form.purchaseDate,
    department: form.department.trim() || null,
    status: form.status,
    mileage: form.mileage ?? 0,
    remark: form.remark.trim() || null
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateVehicle(editingId.value, payload)
      ElMessage.success('车辆信息已更新')
    } else {
      await createVehicle(payload)
      ElMessage.success('车辆已新增')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

function openDetail(row: VehicleOption) {
  detail.value = row
  detailVisible.value = true
}

async function handleDelete(row: VehicleOption) {
  try {
    await ElMessageBox.confirm(`确定删除车辆「${row.plateNo}」吗？`, '删除确认', {
      type: 'warning'
    })
    await deleteVehicle(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

function goModels() {
  void router.push('/vehicle/model')
}

function goWorkOrders(row: VehicleOption) {
  void router.push({ path: '/workOrder', query: { vehicleId: String(row.id) } })
}

onMounted(async () => {
  await loadModels()
  await loadData()
})
</script>

<style scoped lang="scss">
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>

