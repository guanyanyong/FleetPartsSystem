<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="品牌 / 型号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部" clearable class="filter-select">
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
        <span class="table-toolbar__title">车型列表</span>
        <div class="table-toolbar__actions">
          <el-button :icon="ArrowLeft" @click="goBack">返回车辆列表</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增车型</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="brand" label="品牌" min-width="140" show-overflow-tooltip />
        <el-table-column prop="modelName" label="型号" min-width="180" show-overflow-tooltip />
        <el-table-column label="吨位 / 座位" width="130">
          <template #default="{ row }">{{ row.tonnage || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="plain">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as VehicleModelOption)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row as VehicleModelOption)">
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无车型" />
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
      :title="editingId ? '编辑车型' : '新增车型'"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="品牌" prop="brand">
          <el-input v-model="form.brand" maxlength="50" placeholder="如：东风" />
        </el-form-item>
        <el-form-item label="型号" prop="modelName">
          <el-input v-model="form.modelName" maxlength="100" placeholder="如：天龙 KL" />
        </el-form-item>
        <el-form-item label="吨位/座位">
          <el-input v-model="form.tonnage" maxlength="20" placeholder="如：30 吨 / 5 座" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ArrowLeft, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createVehicleModel,
  deleteVehicleModel,
  getVehicleModelList,
  updateVehicleModel,
  type VehicleModelOption,
  type VehicleModelPayload,
  type VehicleModelQuery
} from '@/api/vehicle'
import { formatDate } from '@/utils/format'

const router = useRouter()

interface ModelForm {
  brand: string
  modelName: string
  tonnage: string
  remark: string
  status: number
}

const search = reactive<VehicleModelQuery>({
  keyword: '',
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<VehicleModelOption[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<ModelForm>(emptyForm())

const rules: FormRules = {
  brand: [{ required: true, message: '请输入品牌', trigger: 'blur' }],
  modelName: [{ required: true, message: '请输入型号', trigger: 'blur' }]
}

function emptyForm(): ModelForm {
  return { brand: '', modelName: '', tonnage: '', remark: '', status: 1 }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getVehicleModelList({
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

function openEdit(row: VehicleModelOption) {
  editingId.value = row.id
  Object.assign(form, {
    brand: row.brand,
    modelName: row.modelName,
    tonnage: row.tonnage ?? '',
    remark: row.remark ?? '',
    status: row.status
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
  const payload: VehicleModelPayload = {
    brand: form.brand.trim(),
    modelName: form.modelName.trim(),
    tonnage: form.tonnage.trim() || null,
    remark: form.remark.trim() || null,
    status: form.status
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateVehicleModel(editingId.value, payload)
      ElMessage.success('车型已更新')
    } else {
      await createVehicleModel(payload)
      ElMessage.success('车型已新增')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: VehicleModelOption) {
  try {
    await ElMessageBox.confirm(
      `确定删除车型「${row.brand} ${row.modelName}」吗？已被车辆引用时无法删除。`,
      '删除确认',
      { type: 'warning' }
    )
    await deleteVehicleModel(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

function goBack() {
  void router.push('/vehicle')
}

onMounted(loadData)
</script>
