<template>
  <div class="page-container inventory-item-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="关键字">
          <el-input
            v-model="search.keyword"
            placeholder="库存件编码 / 二维码 / 序列号 / 批次号"
            clearable
            class="filter-input"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="配件">
          <el-input
            :model-value="selectedPartLabel"
            readonly
            placeholder="全部配件"
            class="filter-input part-filter"
            @click="openPartSelect"
          >
            <template v-if="search.partId" #suffix>
              <el-icon class="part-filter__clear" @click.stop="clearPartFilter">
                <CircleClose />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="仓库">
          <el-select
            v-model="search.warehouseId"
            placeholder="全部仓库"
            clearable
            filterable
            class="filter-select"
            @change="handleWarehouseChange"
          >
            <el-option
              v-for="warehouse in warehouseOptions"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="库位">
          <el-select
            v-model="search.locationId"
            placeholder="全部库位"
            clearable
            filterable
            :disabled="!search.warehouseId"
            class="filter-select"
          >
            <el-option
              v-for="location in locationOptions"
              :key="location.id"
              :label="location.locationCode"
              :value="location.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="search.status"
            placeholder="全部状态"
            clearable
            class="filter-select"
          >
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="批次号">
          <el-input
            v-model="search.batchNo"
            placeholder="请输入批次号"
            clearable
            class="filter-input is-short"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__title">库存件列表</span>
        <div class="table-toolbar__actions">
          <el-checkbox
            v-if="isMobile"
            :model-value="allPageSelected"
            :indeterminate="partPageSelected"
            :disabled="!tableData.length"
            class="table-toolbar__check-all"
            @change="toggleSelectAllPage"
          >
            全选本页
          </el-checkbox>
          <span class="table-toolbar__tip">已选择 {{ selectedCount }} 件</span>
          <el-button
            type="success"
            :icon="Printer"
            :disabled="!selectedCount"
            @click="handleBatchPrint"
          >
            批量打印标签
          </el-button>
        </div>
      </div>

      <el-table
        v-if="!isMobile"
        ref="tableRef"
        v-loading="loading"
        :data="tableData"
        border
        stripe
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" align="center" reserve-selection />
        <el-table-column prop="itemCode" label="库存件编码" width="160" show-overflow-tooltip />
        <el-table-column label="配件" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="part-cell">
              <span>{{ row.partName || '-' }}</span>
              <span class="part-cell__code">{{ row.partCode || `配件 #${row.partId}` }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="规格型号" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="仓库 / 库位" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.warehouseName || `仓库 #${row.warehouseId}` }}
            <span v-if="row.locationCode"> / {{ row.locationCode }}</span>
          </template>
        </el-table-column>
        <el-table-column label="批次号" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.batchNo || '-' }}</template>
        </el-table-column>
        <el-table-column label="到期日期" width="120">
          <template #default="{ row }">
            <span :class="{ 'text-danger': isExpiringSoon(row.expireDate) }">
              {{ formatDate(row.expireDate, 'YYYY-MM-DD') }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="单位成本" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.unitCost) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusMeta(row.status).type" size="small">
              {{ row.statusText || statusMeta(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="入库时间" width="170">
          <template #default="{ row }">{{ formatDate(row.inAt || row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as InventoryItemDetail)">详情</el-button>
            <el-button
              v-if="canEditItem"
              link
              type="primary"
              @click="openEdit(row as InventoryItemDetail)"
            >
              编辑
            </el-button>
            <el-button link type="success" @click="handleRowPrint(row as InventoryItemDetail)">打印标签</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 手机端用卡片列表替代宽表格，避免横向滚动 -->
      <div v-else v-loading="loading" class="item-cards">
        <el-empty v-if="!tableData.length" description="暂无库存件" :image-size="72" />

        <article
          v-for="row in tableData"
          :key="row.id"
          class="item-card"
          :class="{ 'is-selected': isRowSelected(row) }"
        >
          <div class="item-card__head">
            <el-checkbox
              :model-value="isRowSelected(row)"
              class="item-card__check"
              :aria-label="`选择库存件 ${row.itemCode}`"
              @change="toggleRowSelect(row)"
            />
            <span class="item-card__code">{{ row.itemCode }}</span>
            <el-tag :type="statusMeta(row.status).type" size="small">
              {{ row.statusText || statusMeta(row.status).label }}
            </el-tag>
          </div>

          <div class="item-card__part">
            <span class="item-card__name">{{ row.partName || '-' }}</span>
            <span class="item-card__sub">
              {{ row.partCode || `配件 #${row.partId}` }}
              <template v-if="row.spec"> · {{ row.spec }}</template>
            </span>
          </div>

          <div class="item-card__meta">
            <div class="item-card__field">
              <span>仓库 / 库位</span>
              <b>
                {{ row.warehouseName || `仓库 #${row.warehouseId}` }}
                <template v-if="row.locationCode"> / {{ row.locationCode }}</template>
              </b>
            </div>
            <div class="item-card__field">
              <span>批次号</span>
              <b>{{ row.batchNo || '-' }}</b>
            </div>
            <div class="item-card__field">
              <span>入库时间</span>
              <b>{{ formatDate(row.inAt || row.createdAt) }}</b>
            </div>
            <div class="item-card__field">
              <span>到期日期</span>
              <b :class="{ 'text-danger': isExpiringSoon(row.expireDate) }">
                {{ formatDate(row.expireDate, 'YYYY-MM-DD') }}
              </b>
            </div>
          </div>

          <div class="item-card__actions">
            <el-button size="small" @click="openDetail(row)">详情</el-button>
            <el-button v-if="canEditItem" size="small" type="primary" plain @click="openEdit(row)">
              编辑
            </el-button>
            <el-button size="small" type="success" plain @click="handleRowPrint(row)">
              打印标签
            </el-button>
          </div>
        </article>
      </div>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'"
          :pager-count="isMobile ? 5 : 7"
          :small="isMobile"
          background
          @size-change="handleSizeChange"
          @current-change="loadList"
        />
      </div>
    </el-card>

    <el-drawer
      v-model="detailVisible"
      title="库存件详情"
      :size="isMobile ? '100%' : '640px'"
    >
      <div v-loading="detailLoading" class="item-detail">
        <template v-if="currentItem">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="库存件编码">
              {{ currentItem.itemCode }}
            </el-descriptions-item>
            <el-descriptions-item label="二维码">
              {{ currentItem.qrcode || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="配件">
              {{ currentItem.partName || '-' }}
              <span class="item-detail__muted">
                （{{ currentItem.partCode || `#${currentItem.partId}` }}）
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="规格型号">
              {{ currentItem.spec || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="仓库 / 库位">
              {{ currentItem.warehouseName || `仓库 #${currentItem.warehouseId}` }}
              <span v-if="currentItem.locationCode"> / {{ currentItem.locationCode }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="批次号 / 序列号">
              {{ currentItem.batchNo || '-' }} / {{ currentItem.serialNo || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="生产 / 到期日期">
              {{ formatDate(currentItem.productionDate, 'YYYY-MM-DD') }} /
              {{ formatDate(currentItem.expireDate, 'YYYY-MM-DD') }}
            </el-descriptions-item>
            <el-descriptions-item label="单位成本">
              {{ formatMoney(currentItem.unitCost) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusMeta(currentItem.status).type" size="small">
                {{ currentItem.statusText || statusMeta(currentItem.status).label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="入库时间">
              {{ formatDate(currentItem.inAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="出库时间">
              {{ formatDate(currentItem.outAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="关联车辆 / 工单">
              {{ currentItem.vehicleId ? `车辆 #${currentItem.vehicleId}` : '-' }} /
              {{ currentItem.workOrderId ? `工单 #${currentItem.workOrderId}` : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="备注">
              {{ currentItem.remark || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="item-detail__section">库存流水</div>
          <el-table v-loading="txLoading" :data="transactions" border size="small">
            <el-table-column label="时间" width="155">
              <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
            </el-table-column>
            <el-table-column label="业务类型" width="100">
              <template #default="{ row }">{{ bizTypeText(row.bizType) }}</template>
            </el-table-column>
            <el-table-column prop="changeQty" label="变更" width="80" align="right" />
            <el-table-column prop="beforeQty" label="变更前" width="80" align="right" />
            <el-table-column prop="afterQty" label="变更后" width="80" align="right" />
            <el-table-column label="关联单号" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ row.refNo || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作人" width="100">
              <template #default="{ row }">
                {{ row.operatorId ? `用户 #${row.operatorId}` : '-' }}
              </template>
            </el-table-column>
          </el-table>

          <div class="item-detail__pagination">
            <el-pagination
              v-model:current-page="txPagination.page"
              v-model:page-size="txPagination.pageSize"
              :total="txPagination.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              small
              @size-change="handleTxSizeChange"
              @current-change="loadTransactions"
            />
          </div>
        </template>
        <el-empty v-else-if="!detailLoading" description="未找到库存件" />
      </div>

      <template #footer>
        <div class="item-detail__footer">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button
            v-if="currentItem && canEditItem"
            type="primary"
            plain
            @click="openEdit(currentItem as InventoryItemDetail)"
          >
            编辑
          </el-button>
          <el-button
            v-if="currentItem"
            type="success"
            :icon="Printer"
            @click="printCurrent"
          >
            打印标签
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="editVisible"
      title="编辑库存件"
      :width="isMobile ? '100%' : '560px'"
      :close-on-click-modal="false"
      class="item-edit-dialog"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="96px"
        class="item-edit"
        @submit.prevent
      >
        <!-- 编码 / 二维码 / 数量由系统与单据维护，只读展示 -->
        <el-descriptions :column="2" border size="small" class="item-edit__locked">
          <el-descriptions-item label="库存件编码">
            {{ editingItem?.itemCode || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="数量">1</el-descriptions-item>
          <el-descriptions-item label="二维码" :span="2">
            {{ editingItem?.qrcode || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <div class="item-edit__tip">
          编码、二维码、数量与状态由入库 / 出库 / 调拨 / 盘点单据维护，此处不可修改。
        </div>

        <el-form-item label="仓库" prop="warehouseId">
          <el-select
            v-model="editForm.warehouseId"
            placeholder="请选择仓库"
            filterable
            :disabled="!canChangeLocation"
            class="item-edit__control"
            @change="handleEditWarehouseChange"
          >
            <el-option
              v-for="warehouse in warehouseOptions"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
            <el-option
              v-if="editWarehouseFallback"
              :label="editWarehouseFallback.name"
              :value="editWarehouseFallback.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="库位" prop="locationId">
          <el-select
            v-model="editForm.locationId"
            placeholder="不指定库位（仓库级存放）"
            filterable
            clearable
            :disabled="!canChangeLocation || !editForm.warehouseId"
            class="item-edit__control"
          >
            <el-option
              v-for="location in editLocationOptions"
              :key="location.id"
              :label="location.locationCode"
              :value="location.id"
            />
            <el-option
              v-if="editLocationFallback"
              :label="editLocationFallback.name"
              :value="editLocationFallback.id"
            />
          </el-select>
        </el-form-item>
        <div v-if="!canChangeLocation" class="item-edit__tip">
          仅「在库」状态的库存件可调整仓库 / 库位，其它资料仍可修改。
        </div>

        <el-form-item label="批次号" prop="batchNo">
          <el-input
            v-model="editForm.batchNo"
            maxlength="50"
            clearable
            placeholder="请输入批次号"
            class="item-edit__control"
          />
        </el-form-item>
        <el-form-item label="序列号" prop="serialNo">
          <el-input
            v-model="editForm.serialNo"
            maxlength="100"
            clearable
            placeholder="请输入序列号 / 出厂编号"
            class="item-edit__control"
          />
        </el-form-item>
        <el-form-item label="生产日期" prop="productionDate">
          <el-date-picker
            v-model="editForm.productionDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择生产日期"
            class="item-edit__control"
          />
        </el-form-item>
        <el-form-item label="到期日期" prop="expireDate">
          <el-date-picker
            v-model="editForm.expireDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择到期日期"
            class="item-edit__control"
          />
        </el-form-item>
        <el-form-item label="单位成本" prop="unitCost">
          <el-input-number
            v-model="editForm.unitCost"
            :min="0"
            :precision="4"
            :step="1"
            controls-position="right"
            class="item-edit__control"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input
            v-model="editForm.remark"
            type="textarea"
            :rows="2"
            maxlength="255"
            show-word-limit
            placeholder="请输入备注"
            class="item-edit__control"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="item-edit__footer">
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <PartSelect
      v-model="partDialogVisible"
      :selected-ids="search.partId ? [search.partId] : []"
      title="选择配件"
      @confirm="handlePartConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { CircleClose, Printer, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules, type TableInstance } from 'element-plus'

import {
  getInventoryItemDetail,
  getInventoryItemList,
  getInventoryItemTransactions,
  updateInventoryItem,
  type InventoryItemDetail,
  type InventoryItemStatus,
  type InventoryItemQuery,
  type InventoryItemUpdatePayload,
  type InventoryTransaction
} from '@/api/inventoryItem'
import type { Part } from '@/api/part'
import {
  getAllWarehouses,
  getAllWarehouseLocations,
  type Warehouse,
  type WarehouseLocation
} from '@/api/warehouse'
import PartSelect from '@/components/PartSelect.vue'
import { useUserStore } from '@/stores/user'
import { formatDate, formatMoney } from '@/utils/format'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

interface ItemSearch {
  keyword: string
  partId: number | undefined
  warehouseId: number | undefined
  locationId: number | undefined
  status: InventoryItemStatus | undefined
  batchNo: string
}

/** 编辑库存件表单：只包含可编辑的资料字段 */
interface ItemEditForm {
  warehouseId: number | undefined
  locationId: number | null
  batchNo: string
  serialNo: string
  productionDate: string | null
  expireDate: string | null
  unitCost: number | undefined
  remark: string
}

const statusMap: Record<InventoryItemStatus, { label: string; type: TagType }> = {
  1: { label: '在库', type: 'success' },
  2: { label: '锁定', type: 'warning' },
  3: { label: '已出库', type: 'info' },
  4: { label: '已报废', type: 'danger' },
  5: { label: '已盘亏', type: 'danger' }
}

const statusOptions: Array<{ value: InventoryItemStatus; label: string }> = [
  { value: 1, label: statusMap[1].label },
  { value: 2, label: statusMap[2].label },
  { value: 3, label: statusMap[3].label },
  { value: 4, label: statusMap[4].label },
  { value: 5, label: statusMap[5].label }
]

const bizTypeMap: Record<string, string> = {
  INBOUND: '入库',
  OUTBOUND: '出库',
  ADJUST: '库存调整',
  TRANSFER: '调拨',
  SCRAP: '报废',
  INVENTORY_CHECK: '盘点'
}

const router = useRouter()
const tableRef = ref<TableInstance>()
const userStore = useUserStore()
/** 编辑库存件：后端仅管理员 / 库管可写（见 docs/backend-requirements.md 11.2） */
const canEditItem = computed(() => ['admin', 'keeper'].includes(userStore.role))

/** 手机端断点：与页面样式中的 @media (max-width: 767px) 保持一致 */
const MOBILE_QUERY = '(max-width: 767px)'
const mobileQuery = window.matchMedia(MOBILE_QUERY)
const isMobile = ref(mobileQuery.matches)

const search = reactive<ItemSearch>({
  keyword: '',
  partId: undefined,
  warehouseId: undefined,
  locationId: undefined,
  status: undefined,
  batchNo: ''
})

const partDialogVisible = ref(false)
const selectedPart = ref<Part | null>(null)

const selectedPartLabel = computed(() => {
  const part = selectedPart.value
  return part ? `${part.partName}（${part.partCode}）` : ''
})

const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const tableData = ref<InventoryItemDetail[]>([])
/** 桌面端表格勾选结果 */
const selection = ref<InventoryItemDetail[]>([])
/** 手机端卡片勾选结果（不受分页影响，可跨页保留） */
const mobileSelection = ref<InventoryItemDetail[]>([])
const loading = ref(false)

/** 当前生效的勾选集合：手机端读卡片，桌面端读表格 */
const selectedRows = computed(() => (isMobile.value ? mobileSelection.value : selection.value))
const selectedCount = computed(() => selectedRows.value.length)
const selectedIdSet = computed(() => new Set(selectedRows.value.map((row) => row.id)))
const allPageSelected = computed(
  () => tableData.value.length > 0 && tableData.value.every((row) => selectedIdSet.value.has(row.id))
)
const partPageSelected = computed(
  () => !allPageSelected.value && tableData.value.some((row) => selectedIdSet.value.has(row.id))
)

const warehouseOptions = ref<Warehouse[]>([])
const locationOptions = ref<WarehouseLocation[]>([])

const detailVisible = ref(false)
const detailLoading = ref(false)
const currentItem = ref<InventoryItemDetail | null>(null)
const transactions = ref<InventoryTransaction[]>([])
const txLoading = ref(false)
const txPagination = reactive({ page: 1, pageSize: 10, total: 0 })

/** 编辑弹窗状态 */
const editVisible = ref(false)
const editSubmitting = ref(false)
const editFormRef = ref<FormInstance>()
const editingItem = ref<InventoryItemDetail | null>(null)
/** 编辑弹窗内按所选仓库加载的库位选项（与列表筛选的 locationOptions 隔离） */
const editLocationOptions = ref<WarehouseLocation[]>([])

/** 仅「在库」实例可调整仓库 / 库位（其余状态后端返回 2002/2003/2004） */
const canChangeLocation = computed(() => editingItem.value?.status === 1)

function createEmptyEditForm(): ItemEditForm {
  return {
    warehouseId: undefined,
    locationId: null,
    batchNo: '',
    serialNo: '',
    productionDate: null,
    expireDate: null,
    unitCost: undefined,
    remark: ''
  }
}

const editForm = reactive<ItemEditForm>(createEmptyEditForm())

/** 库存件所属仓库若已停用，不在启用仓库列表中，这里补一条展示项避免下拉显示空白 */
const editWarehouseFallback = computed<{ id: number; name: string } | null>(() => {
  const item = editingItem.value
  if (!item?.warehouseId) {
    return null
  }
  if (warehouseOptions.value.some((warehouse) => warehouse.id === item.warehouseId)) {
    return null
  }
  return {
    id: item.warehouseId,
    name: item.warehouseName || `仓库 #${item.warehouseId}`
  }
})

/** 同理：所在库位若已停用，补一条展示项（仅当未切换仓库 / 库位时） */
const editLocationFallback = computed<{ id: number; name: string } | null>(() => {
  const item = editingItem.value
  const locationId = item?.locationId
  if (!item || !locationId || editForm.locationId !== locationId) {
    return null
  }
  if (editForm.warehouseId !== item.warehouseId) {
    return null
  }
  if (editLocationOptions.value.some((location) => location.id === locationId)) {
    return null
  }
  return { id: locationId, name: item.locationCode || `库位 #${locationId}` }
})

const editRules: FormRules<ItemEditForm> = {
  warehouseId: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  batchNo: [{ max: 50, message: '批次号不能超过 50 个字符', trigger: 'blur' }],
  serialNo: [{ max: 100, message: '序列号不能超过 100 个字符', trigger: 'blur' }],
  unitCost: [
    { required: true, message: '请输入单位成本', trigger: 'blur' },
    { type: 'number', min: 0, message: '单位成本不能为负数', trigger: 'blur' }
  ],
  expireDate: [
    {
      validator: (_rule: unknown, value: string | null, callback: (error?: Error) => void) => {
        if (value && editForm.productionDate && value < editForm.productionDate) {
          callback(new Error('到期日期不能早于生产日期'))
          return
        }
        callback()
      },
      trigger: 'change'
    }
  ],
  remark: [{ max: 255, message: '备注不能超过 255 个字符', trigger: 'blur' }]
}

function statusMeta(status: InventoryItemStatus): { label: string; type: TagType } {
  return statusMap[status] ?? { label: '未知', type: 'info' }
}

function bizTypeText(bizType: string): string {
  return bizTypeMap[bizType] ?? bizType
}

/** 到期日期在 30 天内高亮提示 */
function isExpiringSoon(value: string | null): boolean {
  if (!value) {
    return false
  }
  const expire = new Date(value).getTime()
  if (Number.isNaN(expire)) {
    return false
  }
  const diff = expire - Date.now()
  return diff >= 0 && diff <= 30 * 24 * 60 * 60 * 1000
}

/** 手机端卡片是否已勾选 */
function isRowSelected(row: InventoryItemDetail): boolean {
  return selectedIdSet.value.has(row.id)
}

/** 手机端卡片勾选切换 */
function toggleRowSelect(row: InventoryItemDetail): void {
  const selected = mobileSelection.value.some((item) => item.id === row.id)
  mobileSelection.value = selected
    ? mobileSelection.value.filter((item) => item.id !== row.id)
    : [...mobileSelection.value, row]
}

/** 手机端「全选本页」，已选中的其它页数据保持不动 */
function toggleSelectAllPage(value: string | number | boolean): void {
  if (value) {
    const merged = new Map(mobileSelection.value.map((item) => [item.id, item]))
    tableData.value.forEach((row) => merged.set(row.id, row))
    mobileSelection.value = Array.from(merged.values())
    return
  }
  const pageIds = new Set(tableData.value.map((row) => row.id))
  mobileSelection.value = mobileSelection.value.filter((item) => !pageIds.has(item.id))
}

/** 视口在手机/桌面间切换时，表格与卡片两套勾选状态无法复用，统一清空 */
function handleViewportChange(): void {
  const mobile = mobileQuery.matches
  if (mobile === isMobile.value) {
    return
  }
  isMobile.value = mobile
  selection.value = []
  mobileSelection.value = []
  tableRef.value?.clearSelection()
}

async function loadWarehouses() {
  try {
    warehouseOptions.value = await getAllWarehouses(1)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function openPartSelect() {
  partDialogVisible.value = true
}

function handlePartConfirm(parts: Part[]) {
  const part = parts[0]
  if (!part) {
    return
  }
  selectedPart.value = part
  search.partId = part.id
}

function clearPartFilter() {
  selectedPart.value = null
  search.partId = undefined
}

async function loadLocations(warehouseId: number) {
  locationOptions.value = []
  try {
    locationOptions.value = await getAllWarehouseLocations(warehouseId)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleWarehouseChange(value: number | undefined) {
  search.locationId = undefined
  if (typeof value === 'number' && value > 0) {
    void loadLocations(value)
  } else {
    locationOptions.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const params: InventoryItemQuery = {
      page: pagination.page,
      pageSize: pagination.pageSize
    }
    const keyword = search.keyword.trim()
    const batchNo = search.batchNo.trim()
    if (keyword) {
      params.keyword = keyword
    }
    if (search.partId) {
      params.partId = search.partId
    }
    if (search.warehouseId) {
      params.warehouseId = search.warehouseId
    }
    if (search.locationId) {
      params.locationId = search.locationId
    }
    if (search.status) {
      params.status = search.status
    }
    if (batchNo) {
      params.batchNo = batchNo
    }

    const res = await getInventoryItemList(params)
    tableData.value = res.data.list
    pagination.total = res.data.total
  } catch {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  void loadList()
}

function handleReset() {
  search.keyword = ''
  search.partId = undefined
  search.warehouseId = undefined
  search.locationId = undefined
  search.status = undefined
  search.batchNo = ''
  selectedPart.value = null
  locationOptions.value = []
  tableRef.value?.clearSelection()
  selection.value = []
  mobileSelection.value = []
  pagination.page = 1
  pagination.total = 0
  void loadList()
}

function handleSizeChange() {
  pagination.page = 1
  void loadList()
}

function handleSelectionChange(rows: InventoryItemDetail[]) {
  selection.value = rows
}

function goPrint(ids: number[]) {
  const unique = Array.from(new Set(ids.filter((id) => Boolean(id))))
  if (!unique.length) {
    ElMessage.warning('请选择需要打印标签的库存件')
    return
  }
  void router.push({ path: '/inventory/item/print', query: { ids: unique.join(',') } })
}

function handleBatchPrint() {
  goPrint(selectedRows.value.map((row) => row.id))
}

function handleRowPrint(row: InventoryItemDetail) {
  if (!row.id) {
    ElMessage.warning('该库存件缺少ID，无法打印标签')
    return
  }
  // 单张打印走 ?id= 直达，链接可直接在手机浏览器打开
  void router.push({ path: '/inventory/item/print', query: { id: String(row.id) } })
}

function printCurrent() {
  const item = currentItem.value
  if (item) {
    handleRowPrint(item)
  }
}

async function loadTransactions() {
  const id = currentItem.value?.id
  if (!id) {
    return
  }

  txLoading.value = true
  try {
    const res = await getInventoryItemTransactions(id, {
      page: txPagination.page,
      pageSize: txPagination.pageSize
    })
    transactions.value = res.data.list
    txPagination.total = res.data.total
  } catch {
    transactions.value = []
    txPagination.total = 0
  } finally {
    txLoading.value = false
  }
}

function handleTxSizeChange() {
  txPagination.page = 1
  void loadTransactions()
}

async function openDetail(row: InventoryItemDetail) {
  detailVisible.value = true
  currentItem.value = null
  transactions.value = []
  txPagination.page = 1
  txPagination.total = 0
  detailLoading.value = true
  try {
    const res = await getInventoryItemDetail(row.id)
    currentItem.value = res.data
    await loadTransactions()
  } catch {
    currentItem.value = null
  } finally {
    detailLoading.value = false
  }
}

/** 编辑弹窗内按所选仓库加载启用库位 */
async function loadEditLocations(warehouseId: number | undefined) {
  editLocationOptions.value = []
  if (typeof warehouseId !== 'number' || warehouseId <= 0) {
    return
  }
  try {
    editLocationOptions.value = await getAllWarehouseLocations(warehouseId)
  } catch {
    editLocationOptions.value = []
  }
}

/** 切换仓库后库位必须重选（跨仓库库位无意义） */
function handleEditWarehouseChange(value: number | undefined) {
  editForm.locationId = null
  void loadEditLocations(value)
}

/** 用库存件详情回填编辑表单 */
function fillEditForm(item: InventoryItemDetail) {
  editingItem.value = item
  editForm.warehouseId = item.warehouseId || undefined
  editForm.locationId = item.locationId ?? null
  editForm.batchNo = item.batchNo ?? ''
  editForm.serialNo = item.serialNo ?? ''
  editForm.productionDate = item.productionDate || null
  editForm.expireDate = item.expireDate || null
  editForm.unitCost =
    item.unitCost === null || item.unitCost === undefined ? undefined : Number(item.unitCost)
  editForm.remark = item.remark ?? ''
}

/** 打开编辑弹窗：先用列表行回填，再拉详情校准最新数据 */
async function openEdit(row: InventoryItemDetail) {
  if (!canEditItem.value) {
    ElMessage.warning('仅管理员 / 库管可编辑库存件')
    return
  }
  if (!row.id) {
    ElMessage.warning('该库存件缺少ID，无法编辑')
    return
  }

  fillEditForm(row)
  editVisible.value = true
  void loadEditLocations(row.warehouseId)
  void nextTick(() => editFormRef.value?.clearValidate())

  try {
    const res = await getInventoryItemDetail(row.id)
    if (editingItem.value?.id === res.data.id) {
      fillEditForm(res.data)
      if (res.data.warehouseId !== row.warehouseId) {
        await loadEditLocations(res.data.warehouseId)
        editForm.locationId = res.data.locationId ?? null
      }
    }
  } catch {
    // 详情接口异常时以列表行数据继续编辑
  }
}

/** 提交编辑：仅提交发生变化的字段，位置类字段仅在「在库」时可改 */
async function submitEdit() {
  const form = editFormRef.value
  const item = editingItem.value
  if (!form || !item) {
    return
  }
  const valid = await form.validate().catch(() => false)
  if (!valid) {
    return
  }

  const payload: InventoryItemUpdatePayload = {
    batchNo: editForm.batchNo.trim() || null,
    serialNo: editForm.serialNo.trim() || null,
    productionDate: editForm.productionDate,
    expireDate: editForm.expireDate,
    unitCost: Number(editForm.unitCost ?? 0),
    remark: editForm.remark.trim() || null
  }
  // 仓库 / 库位仅在发生变化（且允许调整）时提交，避免非在库实例被拒绝
  if (canChangeLocation.value) {
    if (editForm.warehouseId && editForm.warehouseId !== item.warehouseId) {
      payload.warehouseId = editForm.warehouseId
      payload.locationId = editForm.locationId ?? null
    } else if ((editForm.locationId ?? null) !== (item.locationId ?? null)) {
      payload.locationId = editForm.locationId ?? null
    }
  }

  editSubmitting.value = true
  try {
    const res = await updateInventoryItem(item.id, payload)
    ElMessage.success('库存件已更新')
    editVisible.value = false
    // 详情抽屉打开时同步最新数据与流水（位置变更会新增调拨流水）
    if (currentItem.value?.id === res.data.id) {
      currentItem.value = res.data
      txPagination.page = 1
      void loadTransactions()
    }
    void loadList()
  } finally {
    editSubmitting.value = false
  }
}

onMounted(() => {
  mobileQuery.addEventListener('change', handleViewportChange)
  void loadWarehouses()
  void loadList()
})

onBeforeUnmount(() => {
  mobileQuery.removeEventListener('change', handleViewportChange)
})
</script>

<style scoped lang="scss">
.inventory-item-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card :deep(.el-form-item) {
  margin-right: 16px;
  margin-bottom: 0;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 0;
}

.filter-input {
  width: 220px;

  &.is-short {
    width: 160px;
  }
}

.filter-select {
  width: 160px;
}

.part-filter {
  cursor: pointer;

  :deep(.el-input__inner) {
    cursor: pointer;
  }

  &__clear {
    cursor: pointer;

    &:hover {
      color: var(--el-color-primary);
    }
  }
}

.table-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.table-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.table-toolbar__check-all {
  margin-right: 0;
}

.table-toolbar__tip {
  font-size: 12px;
  color: #909399;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ---------------- 手机端卡片列表 ---------------- */
.item-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background-color: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &.is-selected {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--el-color-primary-light-7) inset;
  }

  &__head {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__check {
    flex: none;
    margin-right: 0;
  }

  &__code {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-regular);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__part {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  &__name {
    overflow: hidden;
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__sub {
    overflow: hidden;
    font-size: 12px;
    color: #909399;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__meta {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 12px;
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
    font-size: 12px;

    span {
      color: #909399;
    }

    b {
      overflow: hidden;
      font-weight: 500;
      color: var(--el-text-color-regular);
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  &__actions {
    display: flex;
    gap: 8px;

    :deep(.el-button) {
      flex: 1;
      margin-left: 0;
    }
  }
}

.part-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.4;

  &__code {
    font-size: 12px;
    color: #909399;
  }
}

.text-danger {
  font-weight: 600;
  color: #f56c6c;
}

.item-detail {
  min-height: 200px;

  &__muted {
    font-size: 12px;
    color: #909399;
  }

  &__section {
    margin: 20px 0 12px;
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
}

.item-detail__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;

  :deep(.el-button) {
    margin-left: 0;
  }
}

.item-edit {
  &__locked {
    margin-bottom: 8px;
  }

  &__tip {
    margin: 0 0 16px;
    font-size: 12px;
    line-height: 1.5;
    color: #909399;
  }

  &__control {
    width: 100%;
  }
}

.item-edit__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;

  :deep(.el-button) {
    margin-left: 0;
  }
}

@media (max-width: 767px) {
  .inventory-item-page {
    gap: 8px;
  }

  .filter-card,
  .table-card {
    :deep(.el-card__body) {
      padding: 12px;
    }
  }

  .filter-form {
    gap: 0;
  }

  .filter-card :deep(.el-form-item) {
    display: flex;
    width: 100%;
    margin: 0 0 12px;
  }

  .filter-card :deep(.el-form-item__label) {
    flex: none;
    width: 64px;
    padding-right: 8px;
    text-align: left;
  }

  .filter-card :deep(.el-form-item__content) {
    flex: 1;
    min-width: 0;
  }

  .filter-input,
  .filter-select,
  .filter-input.is-short {
    width: 100%;
  }

  .filter-card .filter-actions {
    margin-bottom: 0 !important;

    :deep(.el-form-item__content) {
      gap: 8px;
    }

    :deep(.el-button) {
      flex: 1;
      margin-left: 0;
    }
  }

  .table-toolbar {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
  }

  .table-toolbar__actions {
    justify-content: space-between;
    gap: 8px;

    :deep(.el-button) {
      flex: 1 1 100%;
      margin-left: 0;
    }
  }

  .pagination-bar {
    justify-content: center;
    margin-top: 12px;
  }

  .item-detail__footer {
    :deep(.el-button) {
      flex: 1;
    }
  }
}
</style>

