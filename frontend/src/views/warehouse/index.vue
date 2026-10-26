<template>
  <div class="page-container warehouse-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="仓库名称">
          <el-input
            v-model="search.keyword"
            placeholder="请输入仓库名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select
            v-model="search.keeperId"
            clearable
            filterable
            placeholder="请选择负责人"
            class="filter-select"
          >
            <el-option
              v-for="user in userOptions"
              :key="user.id"
              :label="userLabel(user)"
              :value="user.id"
            />
          </el-select>
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
        <span class="table-toolbar__title">仓库列表</span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增仓库</el-button>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="name" label="仓库名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="地址" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.address || '-' }}</template>
        </el-table-column>
        <el-table-column label="负责人" min-width="120">
          <template #default="{ row }">{{ keeperNameOf(row as Warehouse) }}</template>
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
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as Warehouse)">编辑</el-button>
            <el-button
              link
              :type="row.status === 1 ? 'warning' : 'success'"
              @click="toggleStatus(row as Warehouse)"
            >
              {{ row.status === 1 ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click="handleDelete(row as Warehouse)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无仓库数据" />
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
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="仓库名称" prop="name">
          <el-input v-model="form.name" maxlength="50" placeholder="请输入仓库名称" />
        </el-form-item>
        <el-form-item label="仓库地址" prop="address">
          <el-input
            v-model="form.address"
            type="textarea"
            :rows="2"
            maxlength="255"
            show-word-limit
            placeholder="请输入仓库地址"
          />
        </el-form-item>
        <el-form-item label="负责人" prop="keeperId">
          <el-select
            v-model="form.keeperId"
            clearable
            filterable
            placeholder="请选择负责人"
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
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import { getUserList, type UserOption } from '@/api/user'
import {
  createWarehouse,
  deleteWarehouse,
  getWarehouseList,
  updateWarehouse,
  type Warehouse
} from '@/api/warehouse'
import { useUserStore } from '@/stores/user'
import { formatDate } from '@/utils/format'

interface WarehouseForm {
  name: string
  address: string
  keeperId: number | undefined
  status: number
}

const search = reactive<{
  keyword: string
  keeperId: number | undefined
  status: number | undefined
}>({
  keyword: '',
  keeperId: undefined,
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<Warehouse[]>([])
const loading = ref(false)
const userOptions = ref<UserOption[]>([])
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增仓库' : '编辑仓库'))

function createEmptyForm(): WarehouseForm {
  return { name: '', address: '', keeperId: undefined, status: 1 }
}

const form = reactive<WarehouseForm>(createEmptyForm())

const rules: FormRules<WarehouseForm> = {
  name: [
    { required: true, message: '请输入仓库名称', trigger: 'blur' },
    { max: 50, message: '仓库名称不能超过 50 个字符', trigger: 'blur' }
  ],
  address: [{ max: 255, message: '仓库地址不能超过 255 个字符', trigger: 'blur' }]
}

function userLabel(user: UserOption) {
  return user.realName ? `${user.realName}（${user.username}）` : user.username
}

/** 后端列表可能只返回 keeperId，优先使用 keeperName，否则从用户选项中反查 */
function keeperNameOf(row: Warehouse) {
  if (row.keeperName) {
    return row.keeperName
  }
  if (row.keeperId === null || row.keeperId === undefined) {
    return '-'
  }
  const matched = userOptions.value.find((user) => user.id === row.keeperId)
  return matched ? userLabel(matched) : `用户 #${row.keeperId}`
}

async function loadUserOptions() {
  // 后端仅 admin / leader 可访问用户列表，其余角色不请求以免弹出 403 提示
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

async function loadData() {
  loading.value = true
  try {
    const res = await getWarehouseList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: search.keyword.trim() || undefined,
      keeperId: search.keeperId ?? undefined,
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
  search.keyword = ''
  search.keeperId = undefined
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

function openEdit(row: Warehouse) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, createEmptyForm(), {
    name: row.name,
    address: row.address ?? '',
    keeperId: row.keeperId ?? undefined,
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
  if (!valid) {
    return
  }

  const address = form.address.trim()
  const payload = {
    name: form.name.trim(),
    address: address === '' ? null : address,
    keeperId: form.keeperId ?? null,
    status: form.status
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createWarehouse(payload)
      ElMessage.success('仓库新增成功')
    } else if (editingId.value !== null) {
      await updateWarehouse(editingId.value, payload)
      ElMessage.success('仓库更新成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: Warehouse) {
  const nextStatus = row.status === 1 ? 0 : 1
  const action = nextStatus === 1 ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(`确定要${action}仓库「${row.name}」吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await updateWarehouse(row.id, { status: nextStatus })
    ElMessage.success(`${action}成功`)
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleDelete(row: Warehouse) {
  try {
    await ElMessageBox.confirm(
      `确定要删除仓库「${row.name}」吗？仓库下存在库位或库存时将无法删除。`,
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
    await deleteWarehouse(row.id)
    ElMessage.success('删除成功')
    if (tableData.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理（仍被引用时返回 409）
  }
}

onMounted(() => {
  void loadUserOptions()
  void loadData()
})
</script>

<style scoped lang="scss">
.warehouse-page {
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
</style>

