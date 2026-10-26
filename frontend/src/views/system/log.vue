<template>
  <div class="page-container">
    <el-alert
      v-if="unavailable"
      class="page-alert"
      type="warning"
      show-icon
      :closable="false"
      title="操作日志接口尚未开放"
      description="后端 /operation-logs 接口上线前无法查询日志，当前页面会自动重试。"
    />

    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="内容 / 单号 / 操作人"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="模块">
          <el-select
            v-model="search.module"
            placeholder="全部模块"
            clearable
            filterable
            allow-create
            default-first-option
            class="filter-select"
          >
            <el-option v-for="item in MODULE_OPTIONS" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            value-format="YYYY-MM-DD HH:mm:ss"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            class="date-range"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">操作日志</span>
        <div class="table-toolbar__actions">
          <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column label="操作时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="模块" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.module" effect="plain">{{ row.module }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.action || '-' }}</template>
        </el-table-column>
        <el-table-column label="关联单据" width="130">
          <template #default="{ row }">
            {{ row.refType ? `${row.refType}#${row.refId ?? '-'}` : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="扫码内容" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.scanCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="日志内容" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">{{ row.content || '-' }}</template>
        </el-table-column>
        <el-table-column label="用户ID" width="90" align="center">
          <template #default="{ row }">{{ row.userId ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="IP" width="130">
          <template #default="{ row }">{{ row.ip || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as OperationLog)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="unavailable ? '接口未开放，暂无数据' : '暂无操作日志'" />
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

    <el-drawer v-model="detailVisible" title="日志详情" size="560px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="日志ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">
            {{ formatDate(detail.createdAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ detail.userId ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ detail.module || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作">{{ detail.action || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联单据">
            {{ detail.refType ? `${detail.refType}#${detail.refId ?? '-'}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="扫码内容">{{ detail.scanCode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="IP">{{ detail.ip || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="drawer-title">日志内容</div>
        <pre class="log-content">{{ detail.content || '-' }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { Refresh, Search } from '@element-plus/icons-vue'

import { getOperationLogList, type OperationLog, type OperationLogQuery } from '@/api/user'
import { formatDate } from '@/utils/format'

const MODULE_OPTIONS = [
  'auth',
  'part',
  'inbound',
  'outbound',
  'transfer',
  'stocktake',
  'workOrder',
  'vehicle',
  'user'
]

const search = reactive<OperationLogQuery>({
  keyword: '',
  module: undefined,
  userId: undefined,
  startTime: undefined,
  endTime: undefined
})

const dateRange = ref<[string, string] | null>(null)
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tableData = ref<OperationLog[]>([])
const loading = ref(false)
const unavailable = ref(false)

const detailVisible = ref(false)
const detail = ref<OperationLog | null>(null)

async function loadData() {
  loading.value = true
  search.startTime = dateRange.value?.[0]
  search.endTime = dateRange.value?.[1]
  try {
    const res = await getOperationLogList({
      ...search,
      keyword: search.keyword?.trim() || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    tableData.value = res.data.list
    pagination.total = res.data.total
    unavailable.value = false
  } catch {
    // 接口未开放（404）或无权限（403）时降级为空列表
    tableData.value = []
    pagination.total = 0
    unavailable.value = true
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
  search.module = undefined
  search.userId = undefined
  search.startTime = undefined
  search.endTime = undefined
  dateRange.value = null
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

function openDetail(row: OperationLog) {
  detail.value = row
  detailVisible.value = true
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.page-alert {
  margin-bottom: 12px;
}

.date-range {
  width: 360px;
}

.drawer-title {
  margin: 20px 0 12px;
  font-weight: 600;
}

.log-content {
  margin: 0;
  padding: 12px;
  max-height: 420px;
  overflow: auto;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>
