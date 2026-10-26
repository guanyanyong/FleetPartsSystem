<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="用户名 / 姓名 / 手机号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="search.role" placeholder="全部角色" clearable class="filter-select">
            <el-option
              v-for="item in ROLE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
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
        <span class="table-toolbar__title">用户列表</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column label="姓名" width="130">
          <template #default="{ row }">{{ row.realName || '-' }}</template>
        </el-table-column>
        <el-table-column label="手机号" width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110" align="center">
          <template #default="{ row }">
            <el-tag effect="plain">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="默认仓库" min-width="160">
          <template #default="{ row }">{{ warehouseName(row.defaultWarehouseId) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              :before-change="() => confirmStatus(row as UserOption)"
            />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as UserOption)">编辑</el-button>
            <el-button link type="warning" @click="openResetPassword(row as UserOption)">
              重置密码
            </el-button>
            <el-button link type="danger" @click="handleDelete(row as UserOption)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无用户" />
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
      :title="editingId ? '编辑用户' : '新增用户'"
      width="620px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" maxlength="50" :disabled="Boolean(editingId)" />
            </el-form-item>
          </el-col>
          <el-col v-if="!editingId" :span="12">
            <el-form-item label="初始密码" prop="password">
              <el-input v-model="form.password" type="password" show-password maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名">
              <el-input v-model="form.realName" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="form.role" class="w-full">
                <el-option
                  v-for="item in ROLE_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认仓库">
              <el-select
                v-model="form.defaultWarehouseId"
                placeholder="选填"
                clearable
                filterable
                class="w-full"
              >
                <el-option
                  v-for="item in warehouses"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch
                v-model="form.status"
                :active-value="1"
                :inactive-value="0"
                active-text="启用"
                inactive-text="停用"
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

    <el-dialog
      v-model="passwordVisible"
      title="重置密码"
      width="420px"
      :close-on-click-modal="false"
      @closed="resetPasswordForm"
    >
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px">
        <el-form-item label="用户名">
          <span>{{ passwordTarget?.username }}</span>
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="passwordForm.password" type="password" show-password maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="handleResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  ROLE_OPTIONS,
  createUser,
  deleteUser,
  getUserList,
  resetUserPassword,
  setUserStatus,
  updateUser,
  type UserCreatePayload,
  type UserOption,
  type UserQuery,
  type UserUpdatePayload
} from '@/api/user'
import { getAllWarehouses, type Warehouse } from '@/api/warehouse'
import { formatDate } from '@/utils/format'

const ROLE_LABEL: Record<string, string> = Object.fromEntries(
  ROLE_OPTIONS.map((item) => [item.value, item.label])
)

interface UserForm {
  username: string
  password: string
  realName: string
  phone: string
  role: string
  defaultWarehouseId: number | undefined
  status: number
}

const search = reactive<UserQuery>({
  keyword: '',
  role: undefined,
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<UserOption[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<UserForm>(emptyForm())

const passwordVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordTarget = ref<UserOption | null>(null)
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive<{ password: string }>({ password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为 6-50 位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  phone: [{ pattern: /^[0-9+\- ]{6,20}$/, message: '手机号格式不正确', trigger: 'blur' }]
}

const passwordRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为 6-50 位', trigger: 'blur' }
  ]
}

function emptyForm(): UserForm {
  return {
    username: '',
    password: '',
    realName: '',
    phone: '',
    role: 'keeper',
    defaultWarehouseId: undefined,
    status: 1
  }
}

function roleLabel(role: string) {
  return ROLE_LABEL[role] || role
}

function warehouseName(id: number | null) {
  if (!id) {
    return '-'
  }
  return warehouses.value.find((item) => item.id === id)?.name || '-'
}

async function loadWarehouses() {
  try {
    warehouses.value = await getAllWarehouses(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getUserList({
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
  search.role = undefined
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

function openEdit(row: UserOption) {
  editingId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    realName: row.realName ?? '',
    phone: row.phone ?? '',
    role: row.role,
    defaultWarehouseId: row.defaultWarehouseId ?? undefined,
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
  submitting.value = true
  try {
    if (editingId.value) {
      const payload: UserUpdatePayload = {
        realName: form.realName.trim() || null,
        phone: form.phone.trim() || null,
        role: form.role,
        defaultWarehouseId: form.defaultWarehouseId ?? null,
        status: form.status
      }
      await updateUser(editingId.value, payload)
      ElMessage.success('用户已更新')
    } else {
      const payload: UserCreatePayload = {
        username: form.username.trim(),
        password: form.password,
        realName: form.realName.trim() || null,
        phone: form.phone.trim() || null,
        role: form.role,
        defaultWarehouseId: form.defaultWarehouseId ?? null,
        status: form.status
      }
      await createUser(payload)
      ElMessage.success('用户已新增')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function confirmStatus(row: UserOption): Promise<boolean> {
  const next = row.status === 1 ? 0 : 1
  const actionText = next === 1 ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(`确定${actionText}用户「${row.username}」吗？`, `${actionText}确认`, {
      type: 'warning'
    })
    await setUserStatus(row.id, next)
    ElMessage.success(`已${actionText}`)
    return true
  } catch {
    return false
  }
}

function openResetPassword(row: UserOption) {
  passwordTarget.value = row
  passwordForm.password = ''
  passwordVisible.value = true
}

function resetPasswordForm() {
  passwordTarget.value = null
  passwordForm.password = ''
  passwordFormRef.value?.clearValidate()
}

async function handleResetPassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid || !passwordTarget.value) {
    return
  }
  passwordSubmitting.value = true
  try {
    await resetUserPassword(passwordTarget.value.id, passwordForm.password)
    ElMessage.success('密码已重置')
    passwordVisible.value = false
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    passwordSubmitting.value = false
  }
}

async function handleDelete(row: UserOption) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', {
      type: 'warning'
    })
    await deleteUser(row.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    // 取消操作或接口错误
  }
}

onMounted(async () => {
  await loadWarehouses()
  await loadData()
})
</script>
