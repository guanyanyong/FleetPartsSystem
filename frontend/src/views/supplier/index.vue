<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="名称 / 联系人 / 电话"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="主营品类">
          <el-input
            v-model="search.mainCategory"
            placeholder="主营品类"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部" clearable class="filter-select">
            <el-option label="合作中" :value="1" />
            <el-option label="已停用" :value="0" />
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
        <span class="table-toolbar__title">供应商列表</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新增供应商</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="name" label="供应商名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="联系人" width="120">
          <template #default="{ row }">{{ row.contact || '-' }}</template>
        </el-table-column>
        <el-table-column label="电话" width="150">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="主营品类" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.mainCategory || '-' }}</template>
        </el-table-column>
        <el-table-column label="账期" width="120">
          <template #default="{ row }">{{ row.paymentTerm || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="plain">
              {{ row.status === 1 ? '合作中' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="地址" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.address || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as Supplier)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row as Supplier)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无供应商" />
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
      :title="editingId ? '编辑供应商' : '新增供应商'"
      width="640px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="100" placeholder="供应商名称" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="form.contact" maxlength="50" placeholder="联系人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电话" prop="phone">
              <el-input v-model="form.phone" maxlength="20" placeholder="联系电话" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主营品类">
              <el-input v-model="form.mainCategory" maxlength="100" placeholder="如：轮胎" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="账期">
              <el-input v-model="form.paymentTerm" maxlength="50" placeholder="如：月结 30 天" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="地址">
          <el-input v-model="form.address" maxlength="255" placeholder="详细地址" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="合作中"
            inactive-text="停用"
          />
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

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createSupplier,
  deleteSupplier,
  getSupplierList,
  updateSupplier,
  type Supplier,
  type SupplierPayload,
  type SupplierQuery
} from '@/api/supplier'

interface SupplierForm {
  name: string
  contact: string
  phone: string
  address: string
  mainCategory: string
  paymentTerm: string
  status: number
}

const search = reactive<SupplierQuery>({
  keyword: '',
  mainCategory: '',
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<Supplier[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<SupplierForm>(emptyForm())

const rules: FormRules = {
  name: [{ required: true, message: '请输入供应商名称', trigger: 'blur' }],
  phone: [
    {
      pattern: /^[0-9+\-() ]{6,20}$/,
      message: '电话格式不正确',
      trigger: 'blur'
    }
  ]
}

function emptyForm(): SupplierForm {
  return {
    name: '',
    contact: '',
    phone: '',
    address: '',
    mainCategory: '',
    paymentTerm: '',
    status: 1
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getSupplierList({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      mainCategory: search.mainCategory?.trim() || undefined,
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
  search.mainCategory = ''
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

function openEdit(row: Supplier) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    contact: row.contact ?? '',
    phone: row.phone ?? '',
    address: row.address ?? '',
    mainCategory: row.mainCategory ?? '',
    paymentTerm: row.paymentTerm ?? '',
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
  const payload: SupplierPayload = {
    name: form.name.trim(),
    contact: form.contact.trim() || null,
    phone: form.phone.trim() || null,
    address: form.address.trim() || null,
    mainCategory: form.mainCategory.trim() || null,
    paymentTerm: form.paymentTerm.trim() || null,
    status: form.status
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateSupplier(editingId.value, payload)
      ElMessage.success('供应商已更新')
    } else {
      await createSupplier(payload)
      ElMessage.success('供应商已新增')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Supplier) {
  try {
    await ElMessageBox.confirm(
      `确定删除供应商「${row.name}」吗？存在关联入库单时无法删除。`,
      '删除确认',
      { type: 'warning' }
    )
    await deleteSupplier(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

onMounted(loadData)
</script>
