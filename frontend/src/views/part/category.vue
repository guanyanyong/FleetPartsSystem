<template>
  <div class="page-container category-page">
    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="table-toolbar__left">
          <span class="table-toolbar__title">配件分类</span>
          <el-select
            v-model="statusFilter"
            class="status-filter"
            placeholder="全部状态"
            clearable
            @change="loadData"
          >
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </div>
        <div>
          <el-button :icon="Refresh" @click="loadData">刷新</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate()">新增一级分类</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        border
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="name" label="分类名称" min-width="240" show-overflow-tooltip />
        <el-table-column label="层级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.parentId ? 'info' : 'primary'" effect="plain" size="small">
              {{ row.parentId ? '二级' : '一级' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" width="100" align="center">
          <template #default="{ row }">{{ row.sort ?? 0 }}</template>
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
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.parentId" link type="primary" @click="openCreate(row as PartCategory)">
              新增子分类
            </el-button>
            <el-button link type="primary" @click="openEdit(row as PartCategory)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row as PartCategory)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无分类数据" />
        </template>
      </el-table>

      <div class="table-tip">
        提示：删除分类时，若该分类下存在子分类或已关联配件，后端将拒绝删除。
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      :close-on-click-modal="false"
      @closed="formRef?.clearValidate()"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="上级分类">
          <el-input :model-value="parentName" disabled placeholder="无（一级分类）" />
        </el-form-item>
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" maxlength="50" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number
            v-model="form.sort"
            :min="0"
            :max="9999"
            :precision="0"
            controls-position="right"
            class="full-width"
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  createPartCategory,
  deletePartCategory,
  getPartCategoryTree,
  updatePartCategory,
  type PartCategory
} from '@/api/part'
import { formatDate } from '@/utils/format'

interface CategoryForm {
  name: string
  parentId: number | null
  sort: number | undefined
  status: number
}

const loading = ref(false)
const tableData = ref<PartCategory[]>([])
const statusFilter = ref<number | undefined>(undefined)

const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const submitting = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const parentCategory = ref<PartCategory | null>(null)

const form = reactive<CategoryForm>({
  name: '',
  parentId: null,
  sort: 0,
  status: 1
})

const parentName = computed(() => {
  if (form.parentId === null) {
    return ''
  }
  return parentCategory.value?.name ?? `分类 #${form.parentId}`
})

const dialogTitle = computed(() =>
  dialogMode.value === 'create'
    ? form.parentId === null
      ? '新增一级分类'
      : '新增子分类'
    : '编辑分类'
)

const rules: FormRules<CategoryForm> = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 50, message: '分类名称不能超过 50 个字符', trigger: 'blur' }
  ],
  sort: [{ required: true, message: '请输入排序值', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

async function loadData() {
  loading.value = true
  try {
    const res = await getPartCategoryTree(statusFilter.value)
    tableData.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

/** 在整棵分类树中查找父级节点 */
function findParent(parentId: number): PartCategory | null {
  return tableData.value.find((item) => item.id === parentId) ?? null
}

function openCreate(parent?: PartCategory) {
  dialogMode.value = 'create'
  editingId.value = null
  parentCategory.value = parent ?? null
  form.name = ''
  form.parentId = parent ? parent.id : null
  form.sort = 0
  form.status = 1
  dialogVisible.value = true
}

function openEdit(row: PartCategory) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  parentCategory.value = row.parentId ? findParent(row.parentId) : null
  form.name = row.name
  form.parentId = row.parentId ?? null
  form.sort = row.sort ?? 0
  form.status = row.status
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  const parentId = form.parentId
  const siblings = parentId === null
    ? tableData.value
    : (findParent(parentId)?.children ?? [])
  const duplicated = siblings.some(
    (item) =>
      item.name.trim() === form.name.trim() && item.id !== (dialogMode.value === 'edit' ? editingId.value : null)
  )
  if (duplicated) {
    ElMessage.warning('同级分类下已存在同名分类')
    return
  }

  const payload = {
    name: form.name.trim(),
    parentId,
    sort: form.sort ?? 0,
    status: form.status
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createPartCategory(payload)
      ElMessage.success('分类新增成功')
    } else if (editingId.value !== null) {
      await updatePartCategory(editingId.value, payload)
      ElMessage.success('分类更新成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: PartCategory) {
  const hasChildren = (row.children?.length ?? 0) > 0
  const tip = hasChildren
    ? `分类「${row.name}」下存在子分类，确定要尝试删除吗？`
    : `确定要删除分类「${row.name}」吗？`
  try {
    await ElMessageBox.confirm(tip, '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await deletePartCategory(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理（存在子分类或关联配件时返回 409）
  }
}

onMounted(() => {
  void loadData()
})
</script>

<style scoped lang="scss">
.category-page {
  .table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    &__left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    &__title {
      font-size: 15px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .status-filter {
    width: 120px;
  }

  .table-tip {
    margin-top: 12px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .full-width {
    width: 100%;
  }
}
</style>

