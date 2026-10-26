<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="900px"
    append-to-body
    destroy-on-close
    @opened="focusSearch"
  >
    <el-form :model="search" inline class="part-select__search" @submit.prevent>
      <el-form-item label="关键字">
        <el-input
          ref="keywordRef"
          v-model="search.keyword"
          placeholder="配件编码 / 名称"
          clearable
          class="part-select__keyword"
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item label="分类">
        <el-tree-select
          v-model="search.categoryId"
          :data="categoryTree"
          :props="categoryTreeProps"
          node-key="id"
          check-strictly
          clearable
          placeholder="全部分类"
          class="part-select__category"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button :icon="Refresh" @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="tableData"
      row-key="id"
      height="380px"
      border
      highlight-current-row
      @selection-change="handleSelectionChange"
      @current-change="handleCurrentChange"
    >
      <el-table-column v-if="multiple" type="selection" width="45" reserve-selection />
      <el-table-column v-else width="45" align="center">
        <template #default="{ row }">
          <el-radio v-model="singleId" :label="row.id"><span /></el-radio>
        </template>
      </el-table-column>
      <el-table-column prop="partCode" label="配件编码" min-width="130" />
      <el-table-column prop="partName" label="配件名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="spec" label="规格型号" min-width="140" show-overflow-tooltip />
      <el-table-column prop="unit" label="单位" width="70" align="center" />
      <el-table-column prop="brand" label="品牌" min-width="100" show-overflow-tooltip />
      <el-table-column label="库存" width="90" align="right">
        <template #default="{ row }">{{ formatQuantity(row.stockQuantity) }}</template>
      </el-table-column>
      <el-table-column label="追踪方式" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.trackByItem === 1 ? 'warning' : 'info'" size="small">
            {{ row.trackByItem === 1 ? '逐件' : '数量' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <div class="part-select__pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="loadData"
        @size-change="handleSizeChange"
      />
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleConfirm">
        确定{{ multiple && selectedRows.length ? `（${selectedRows.length}）` : '' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'

import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, type InputInstance, type TableInstance } from 'element-plus'

import {
  getPartCategoryTree,
  getPartList,
  type Part,
  type PartCategory
} from '@/api/part'
import { formatQuantity } from '@/utils/format'

interface Props {
  /** 控制弹窗显隐 */
  modelValue: boolean
  /** 是否多选 */
  multiple?: boolean
  /** 已选配件ID，用于打开时回显当前页的选中状态 */
  selectedIds?: number[]
  /** 弹窗标题 */
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  multiple: false,
  selectedIds: () => [],
  title: '选择配件'
})

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'confirm', parts: Part[]): void
}>()

const categoryTreeProps = { label: 'name', children: 'children' }

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const search = reactive<{
  keyword: string
  categoryId: number | undefined
}>({
  keyword: '',
  categoryId: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<Part[]>([])
const categoryTree = ref<PartCategory[]>([])
const loading = ref(false)

const keywordRef = ref<InputInstance>()
const tableRef = ref<TableInstance>()
const selectedRows = ref<Part[]>([])
const singleId = ref<number | undefined>()

function focusSearch() {
  keywordRef.value?.focus()
}

async function loadCategories() {
  try {
    const res = await getPartCategoryTree()
    categoryTree.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getPartList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: search.keyword.trim() || undefined,
      categoryId: search.categoryId ?? undefined,
      status: 1
    })
    tableData.value = res.data.list
    pagination.total = res.data.total

    await nextTick()
    tableRef.value?.clearSelection()
    const selectedIdSet = new Set(props.selectedIds)
    tableData.value.forEach((row) => {
      if (selectedIdSet.has(row.id)) {
        tableRef.value?.toggleRowSelection(row, true)
      }
    })
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
  search.categoryId = undefined
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function handleSelectionChange(rows: Part[]) {
  selectedRows.value = rows
}

function handleCurrentChange(row: Part | null) {
  if (props.multiple || !row) {
    return
  }
  singleId.value = row.id
  selectedRows.value = [row]
}

function handleConfirm() {
  if (props.multiple) {
    if (!selectedRows.value.length) {
      ElMessage.warning('请至少选择一个配件')
      return
    }
    emit('confirm', [...selectedRows.value])
  } else {
    const row = tableData.value.find((item) => item.id === singleId.value)
    if (!row) {
      ElMessage.warning('请选择一个配件')
      return
    }
    emit('confirm', [row])
  }
  visible.value = false
}

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      return
    }
    selectedRows.value = []
    singleId.value = props.multiple ? undefined : props.selectedIds[0]
    pagination.page = 1
    void loadCategories()
    void loadData()
  },
  { immediate: true }
)
</script>

<style scoped>
.part-select__search {
  margin-bottom: 4px;
}

.part-select__keyword {
  width: 220px;
}

.part-select__category {
  width: 180px;
}

.part-select__pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
