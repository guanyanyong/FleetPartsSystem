<template>
  <div class="page-container">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="单号">
          <el-input
            v-model="search.orderNo"
            placeholder="盘点单号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="仓库">
          <el-select
            v-model="search.warehouseId"
            placeholder="全部仓库"
            clearable
            class="filter-select"
          >
            <el-option
              v-for="item in warehouses"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="search.status" placeholder="全部状态" clearable class="filter-select">
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
        <span class="table-toolbar__title">盘点单列表</span>
        <div class="table-toolbar__actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新建盘点单</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="orderNo" label="盘点单号" min-width="180" show-overflow-tooltip />
        <el-table-column label="仓库" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.warehouseName || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusOf(row.status).type" effect="plain">
              {{ statusOf(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="盘点时间" width="170">
          <template #default="{ row }">{{ formatDate(row.stocktakeAt) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as StocktakeOrder)">
              {{ row.status === 2 ? '继续盘点' : '详情' }}
            </el-button>
            <el-button
              v-if="row.status === 1"
              link
              type="success"
              @click="handleStart(row as StocktakeOrder)"
            >
              开始盘点
            </el-button>
            <el-button
              v-if="row.status === 1 || row.status === 2"
              link
              type="danger"
              @click="handleCancel(row as StocktakeOrder)"
            >
              作废
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无盘点单" />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="新建盘点单"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="盘点仓库" prop="warehouseId">
          <el-select v-model="form.warehouseId" placeholder="请选择仓库" filterable class="w-full">
            <el-option
              v-for="item in warehouses"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="盘点说明（选填）"
          />
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="创建后将按所选仓库的现有库存自动生成盘点快照"
        />
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  cancelStocktakeOrder,
  createStocktakeOrder,
  getStocktakeOrderList,
  startStocktakeOrder,
  type StocktakeOrder,
  type StocktakeOrderQuery
} from '@/api/stocktake'
import { getAllWarehouses, type Warehouse } from '@/api/warehouse'
import { formatDate } from '@/utils/format'

const router = useRouter()

type TagType = 'info' | 'primary' | 'success' | 'danger'

const STATUS_MAP: Record<number, { label: string; type: TagType }> = {
  1: { label: '草稿', type: 'info' },
  2: { label: '盘点中', type: 'primary' },
  3: { label: '已完成', type: 'success' },
  4: { label: '已作废', type: 'danger' }
}

const search = reactive<StocktakeOrderQuery>({
  orderNo: '',
  warehouseId: undefined,
  status: undefined
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<StocktakeOrder[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<{ warehouseId: number | undefined; remark: string }>({
  warehouseId: undefined,
  remark: ''
})

const rules: FormRules = {
  warehouseId: [{ required: true, message: '请选择盘点仓库', trigger: 'change' }]
}

function statusOf(status: number) {
  return STATUS_MAP[status] ?? { label: '未知', type: 'info' as TagType }
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
    const res = await getStocktakeOrderList({
      ...search,
      orderNo: search.orderNo?.trim() || undefined,
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
  search.orderNo = ''
  search.warehouseId = undefined
  search.status = undefined
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function openCreate() {
  dialogVisible.value = true
}

function resetForm() {
  form.warehouseId = undefined
  form.remark = ''
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    const res = await createStocktakeOrder({
      warehouseId: form.warehouseId as number,
      remark: form.remark.trim() || null
    })
    ElMessage.success('盘点单创建成功，请开始盘点')
    dialogVisible.value = false
    await router.push(`/stocktake/${res.data.id}`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

function openDetail(row: StocktakeOrder) {
  void router.push(`/stocktake/${row.id}`)
}

async function handleStart(row: StocktakeOrder) {
  try {
    await startStocktakeOrder(row.id)
    ElMessage.success('已开始盘点')
    openDetail(row)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleCancel(row: StocktakeOrder) {
  try {
    await ElMessageBox.confirm(`确定作废盘点单「${row.orderNo}」吗？`, '作废确认', {
      type: 'warning'
    })
    await cancelStocktakeOrder(row.id)
    ElMessage.success('已作废')
    void loadData()
  } catch {
    // 取消操作或接口错误
  }
}

onMounted(async () => {
  await loadWarehouses()
  await loadData()
})
</script>

