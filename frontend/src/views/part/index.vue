<template>
  <div class="page-container part-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="search" inline class="filter-form" @submit.prevent>
        <el-form-item label="配件编码">
          <el-input
            v-model="search.partCode"
            placeholder="请输入配件编码"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="配件名称">
          <el-input
            v-model="search.keyword"
            placeholder="请输入配件名称"
            clearable
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
            filterable
            placeholder="请选择分类"
            class="filter-select"
          />
        </el-form-item>
        <el-form-item label="品牌">
          <el-input
            v-model="search.brand"
            placeholder="请输入品牌"
            clearable
            @keyup.enter="handleSearch"
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
        <span class="table-toolbar__title">配件列表</span>
        <div class="table-toolbar__actions">
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增配件</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe row-key="id">
        <el-table-column prop="partCode" label="编码" width="150" show-overflow-tooltip />
        <el-table-column prop="partName" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="分类" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.categoryName || '-' }}</template>
        </el-table-column>
        <el-table-column label="规格" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column label="品牌" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.brand || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" align="center" />
        <el-table-column label="安全库存" width="110" align="right">
          <template #default="{ row }">{{ formatQuantity(row.safetyStock) }}</template>
        </el-table-column>
        <el-table-column label="当前库存" width="110" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': isLowStock(row as Part) }">
              {{ formatQuantity(row.stockQuantity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="是否按件追踪" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.trackByItem === 1 ? 'success' : 'info'" effect="plain">
              {{ row.trackByItem === 1 ? '按件追踪' : '不追踪' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" effect="plain">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as Part)">编辑</el-button>
            <el-button link type="primary" @click="openDetail(row as Part)">详情</el-button>
            <el-button link type="primary" @click="openQrcode(row as Part)">二维码</el-button>
            <el-button
              link
              :type="row.status === 1 ? 'danger' : 'success'"
              @click="toggleStatus(row as Part)"
            >
              {{ row.status === 1 ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无配件数据" />
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
      width="760px"
      :close-on-click-modal="false"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="配件编码" prop="partCode">
              <el-input v-model="form.partCode" maxlength="50" placeholder="请输入配件编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="配件名称" prop="partName">
              <el-input v-model="form.partName" maxlength="100" placeholder="请输入配件名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categoryTree"
                :props="categoryTreeProps"
                node-key="id"
                check-strictly
                filterable
                placeholder="请选择分类"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌" prop="brand">
              <el-input v-model="form.brand" maxlength="50" placeholder="请输入品牌" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="规格型号" prop="spec">
              <el-input v-model="form.spec" maxlength="100" placeholder="请输入规格型号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="form.unit" maxlength="20" placeholder="如：个 / 套 / 升" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否通用件" prop="isGeneral">
              <el-switch v-model="form.isGeneral" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="安全库存" prop="safetyStock">
              <el-input-number
                v-model="form.safetyStock"
                :min="0"
                :precision="2"
                :step="1"
                controls-position="right"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最高库存" prop="maxStock">
              <el-input-number
                v-model="form.maxStock"
                :min="0"
                :precision="2"
                :step="1"
                controls-position="right"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="保质期天数" prop="shelfLifeDays">
              <el-input-number
                v-model="form.shelfLifeDays"
                :min="0"
                :precision="0"
                :step="30"
                controls-position="right"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="按件追踪" prop="trackByItem">
              <div class="switch-with-tip">
                <el-switch v-model="form.trackByItem" :active-value="1" :inactive-value="0" />
                <span class="form-tip">开启后入库逐件生成二维码</span>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="扫码出库" prop="scanEnabled">
              <div class="switch-with-tip">
                <el-switch v-model="form.scanEnabled" :active-value="1" :inactive-value="0" />
                <span class="form-tip">关闭后仅允许手动出库</span>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="3"
                maxlength="255"
                show-word-limit
                placeholder="请输入备注"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
    <el-drawer v-model="detailVisible" title="配件详情" size="760px" destroy-on-close>
      <div v-loading="detailLoading" class="part-detail">
        <el-descriptions v-if="detailPart" :column="2" border>
          <el-descriptions-item label="配件编码">{{ detailPart.partCode }}</el-descriptions-item>
          <el-descriptions-item label="配件名称">{{ detailPart.partName }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detailPart.categoryName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="规格型号">{{ detailPart.spec || '-' }}</el-descriptions-item>
          <el-descriptions-item label="品牌">{{ detailPart.brand || '-' }}</el-descriptions-item>
          <el-descriptions-item label="单位">{{ detailPart.unit }}</el-descriptions-item>
          <el-descriptions-item label="是否通用件">
            {{ detailPart.isGeneral === 1 ? '是' : '否' }}
          </el-descriptions-item>
          <el-descriptions-item label="是否按件追踪">
            {{ detailPart.trackByItem === 1 ? '是' : '否' }}
          </el-descriptions-item>
          <el-descriptions-item label="安全库存">
            {{ formatQuantity(detailPart.safetyStock) }}
          </el-descriptions-item>
          <el-descriptions-item label="最高库存">
            {{ formatQuantity(detailPart.maxStock) }}
          </el-descriptions-item>
          <el-descriptions-item label="保质期天数">
            {{ detailPart.shelfLifeDays ? `${detailPart.shelfLifeDays} 天` : '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="当前库存">
            {{ formatQuantity(detailPart.stockQuantity) }}
          </el-descriptions-item>
          <el-descriptions-item label="扫码出库">
            {{ detailPart.scanEnabled === 1 ? '允许' : '不允许' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ detailPart.status === 1 ? '启用' : '停用' }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ detailPart.remark || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="暂无配件信息" />

        <template v-if="detailPart">
          <el-divider content-position="left">当前库存（按仓库）</el-divider>
          <el-table
            v-loading="inventoryLoading"
            :data="inventoryRows"
            border
            size="small"
            class="detail-table"
          >
            <el-table-column label="仓库" min-width="120">
              <template #default="{ row }">
                {{ row.warehouseName || `仓库 #${row.warehouseId}` }}
              </template>
            </el-table-column>
            <el-table-column label="库位" min-width="110">
              <template #default="{ row }">{{ row.locationCode || '-' }}</template>
            </el-table-column>
            <el-table-column label="数量" width="100" align="right">
              <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
            </el-table-column>
            <el-table-column label="实例数" width="90" align="right">
              <template #default="{ row }">{{ row.itemCount }}</template>
            </el-table-column>
            <el-table-column label="平均成本" width="110" align="right">
              <template #default="{ row }">{{ formatMoney(row.avgCost) }}</template>
            </el-table-column>
            <el-table-column label="最后入库时间" width="170">
              <template #default="{ row }">{{ formatDate(row.lastInAt) }}</template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无库存记录" :image-size="60" />
            </template>
          </el-table>

          <el-divider content-position="left">适配车型</el-divider>
          <div class="inline-form">
            <el-select
              v-model="modelForm.modelId"
              filterable
              clearable
              placeholder="请选择车型"
              class="inline-form__select"
            >
              <el-option
                v-for="model in vehicleModelOptions"
                :key="model.id"
                :label="`${model.brand} ${model.modelName}`"
                :value="model.id"
              />
            </el-select>
            <el-input
              v-model="modelForm.remark"
              maxlength="100"
              placeholder="备注（可选）"
              class="inline-form__input"
            />
            <el-button type="primary" :loading="modelSubmitting" @click="handleAddModel">
              添加
            </el-button>
          </div>
          <el-table :data="partModels" border size="small" class="detail-table">
            <el-table-column label="品牌" min-width="100">
              <template #default="{ row }">{{ row.brand || '-' }}</template>
            </el-table-column>
            <el-table-column label="车型" min-width="140">
              <template #default="{ row }">{{ row.modelName || `车型 #${row.modelId}` }}</template>
            </el-table-column>
            <el-table-column label="吨位/座位" width="100">
              <template #default="{ row }">{{ row.tonnage || '-' }}</template>
            </el-table-column>
            <el-table-column label="备注" min-width="100">
              <template #default="{ row }">{{ row.remark || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button link type="danger" @click="handleDeleteModel(row as PartVehicleModel)">
                  移除
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无适配车型" :image-size="60" />
            </template>
          </el-table>

          <el-divider content-position="left">单位换算</el-divider>
          <div class="inline-form">
            <el-input
              v-model="unitForm.fromUnit"
              maxlength="20"
              placeholder="源单位"
              class="inline-form__unit"
            />
            <span class="inline-form__sep">=</span>
            <el-input-number
              v-model="unitForm.rate"
              :min="0.0001"
              :precision="4"
              :step="1"
              controls-position="right"
              class="inline-form__rate"
            />
            <el-input
              v-model="unitForm.toUnit"
              maxlength="20"
              placeholder="目标单位"
              class="inline-form__unit"
            />
            <el-button type="primary" :loading="unitSubmitting" @click="handleAddUnit">
              添加
            </el-button>
          </div>
          <el-table :data="unitConversions" border size="small" class="detail-table">
            <el-table-column label="换算关系" min-width="200">
              <template #default="{ row }">
                1 {{ row.fromUnit }} = {{ row.rate }} {{ row.toUnit }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button link type="danger" @click="handleDeleteUnit(row as PartUnitConversion)">
                  删除
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无单位换算" :image-size="60" />
            </template>
          </el-table>
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="qrVisible" title="配件二维码" width="360px" destroy-on-close align-center>
      <div class="qr-dialog">
        <QrCode v-if="qrContent" ref="partQrRef" :value="qrContent" :size="200" />
        <p class="qr-dialog__value">{{ qrContent }}</p>
        <p class="form-tip">二维码内容为配件编码，可用于标签打印或扫码识别</p>
      </div>
      <template #footer>
        <el-button @click="qrVisible = false">关闭</el-button>
        <el-button type="primary" :icon="Download" @click="handleDownloadQrcode">
          下载二维码
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

import { Download, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import { getInventoryList, type InventoryDetail } from '@/api/inventory'
import {
  addPartModel,
  addPartUnitConversion,
  createPart,
  deletePartModel,
  deletePartUnitConversion,
  getPartCategoryTree,
  getPartDetail,
  getPartList,
  getPartModels,
  getPartUnitConversions,
  updatePart,
  type Part,
  type PartCategory,
  type PartUnitConversion,
  type PartVehicleModel
} from '@/api/part'
import { getVehicleModelOptions, type VehicleModelOption } from '@/api/vehicle'
import QrCode from '@/components/QrCode.vue'
import { downloadCsv, type CsvColumn } from '@/utils/export'
import { formatDate, formatDay, formatMoney, formatQuantity } from '@/utils/format'

/** 搜索条件 */
interface PartSearchForm {
  partCode: string
  keyword: string
  categoryId: number | undefined
  brand: string
}

/** 新增 / 编辑表单 */
interface PartForm {
  partCode: string
  partName: string
  categoryId: number | undefined
  spec: string
  brand: string
  unit: string
  isGeneral: number
  safetyStock: number | undefined
  maxStock: number | undefined
  shelfLifeDays: number | undefined
  trackByItem: number
  scanEnabled: number
  remark: string
  status: number
}

const categoryTreeProps = { label: 'name', children: 'children' }

const search = reactive<PartSearchForm>({
  partCode: '',
  keyword: '',
  categoryId: undefined,
  brand: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const tableData = ref<Part[]>([])
const categoryTree = ref<PartCategory[]>([])
const loading = ref(false)
const exporting = ref(false)

const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const submitting = ref(false)

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增配件' : '编辑配件'))

function createEmptyForm(): PartForm {
  return {
    partCode: '',
    partName: '',
    categoryId: undefined,
    spec: '',
    brand: '',
    unit: '个',
    isGeneral: 0,
    safetyStock: 0,
    maxStock: 0,
    shelfLifeDays: 0,
    trackByItem: 0,
    scanEnabled: 1,
    remark: '',
    status: 1
  }
}

const form = reactive<PartForm>(createEmptyForm())

const rules: FormRules<PartForm> = {
  partCode: [
    { required: true, message: '请输入配件编码', trigger: 'blur' },
    { max: 50, message: '配件编码不能超过 50 个字符', trigger: 'blur' }
  ],
  partName: [
    { required: true, message: '请输入配件名称', trigger: 'blur' },
    { max: 100, message: '配件名称不能超过 100 个字符', trigger: 'blur' }
  ],
  categoryId: [{ required: true, message: '请选择配件分类', trigger: 'change' }],
  unit: [
    { required: true, message: '请输入单位', trigger: 'blur' },
    { max: 20, message: '单位不能超过 20 个字符', trigger: 'blur' }
  ],
  brand: [{ max: 50, message: '品牌不能超过 50 个字符', trigger: 'blur' }],
  spec: [{ max: 100, message: '规格型号不能超过 100 个字符', trigger: 'blur' }],
  remark: [{ max: 255, message: '备注不能超过 255 个字符', trigger: 'blur' }],
  maxStock: [
    {
      validator: (_rule, value, callback) => {
        const safetyStock = Number(form.safetyStock ?? 0)
        if (typeof value === 'number' && value < safetyStock) {
          callback(new Error('最高库存不能小于安全库存'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

/** 当前库存低于安全库存时高亮（安全库存为 0 视为未设置，不高亮） */
function isLowStock(row: Part): boolean {
  const safetyStock = Number(row.safetyStock ?? 0)
  if (!Number.isFinite(safetyStock) || safetyStock <= 0) {
    return false
  }
  const stock = Number(row.stockQuantity ?? 0)
  return Number.isFinite(stock) && stock < safetyStock
}

async function loadCategoryTree() {
  try {
    const res = await getPartCategoryTree()
    categoryTree.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

/** 查询条件转换：空字符串不参与查询 */
function buildQuery() {
  return {
    partCode: search.partCode.trim() || undefined,
    keyword: search.keyword.trim() || undefined,
    categoryId: search.categoryId || undefined,
    brand: search.brand.trim() || undefined
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await getPartList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...buildQuery()
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
  search.partCode = ''
  search.keyword = ''
  search.categoryId = undefined
  search.brand = ''
  pagination.page = 1
  void loadData()
}

function handleSizeChange() {
  pagination.page = 1
  void loadData()
}

/** 单次导出上限，避免误操作拉取过多数据 */
const MAX_EXPORT_ROWS = 10000

/** 导出当前筛选条件下的配件（CSV，可用 Excel 打开） */
async function handleExport() {
  exporting.value = true
  try {
    const pageSize = 200
    const rows: Part[] = []
    let page = 1
    let total = 0

    do {
      const res = await getPartList({ page, pageSize, ...buildQuery() })
      rows.push(...res.data.list)
      total = res.data.total
      page += 1
      if (res.data.list.length === 0 || rows.length >= MAX_EXPORT_ROWS) {
        break
      }
    } while (rows.length < total)

    if (rows.length === 0) {
      ElMessage.warning('当前筛选条件下没有可导出的数据')
      return
    }

    const columns: CsvColumn<Part>[] = [
      { label: '配件编码', value: (row) => row.partCode },
      { label: '配件名称', value: (row) => row.partName },
      { label: '分类', value: (row) => row.categoryName ?? '' },
      { label: '规格', value: (row) => row.spec ?? '' },
      { label: '品牌', value: (row) => row.brand ?? '' },
      { label: '单位', value: (row) => row.unit },
      { label: '安全库存', value: (row) => row.safetyStock ?? 0 },
      { label: '当前库存', value: (row) => row.stockQuantity ?? 0 },
      { label: '最高库存', value: (row) => row.maxStock ?? 0 },
      { label: '按件追踪', value: (row) => (row.trackByItem === 1 ? '是' : '否') },
      { label: '扫码管理', value: (row) => (row.scanEnabled === 1 ? '是' : '否') },
      { label: '状态', value: (row) => (row.status === 1 ? '启用' : '停用') },
      { label: '备注', value: (row) => row.remark ?? '' }
    ]

    downloadCsv(`配件列表_${formatDay(new Date())}.csv`, columns, rows)
    if (rows.length < total) {
      ElMessage.warning(`数据量较大，仅导出前 ${rows.length} 条（共 ${total} 条）`)
    } else {
      ElMessage.success(`已导出 ${rows.length} 条配件数据`)
    }
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    exporting.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  Object.assign(form, createEmptyForm())
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: Part) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  Object.assign(form, createEmptyForm(), {
    partCode: row.partCode,
    partName: row.partName,
    categoryId: row.categoryId ?? undefined,
    spec: row.spec ?? '',
    brand: row.brand ?? '',
    unit: row.unit,
    isGeneral: row.isGeneral,
    safetyStock: row.safetyStock ?? 0,
    maxStock: row.maxStock ?? 0,
    shelfLifeDays: row.shelfLifeDays ?? 0,
    trackByItem: row.trackByItem,
    scanEnabled: row.scanEnabled,
    remark: row.remark ?? '',
    status: row.status
  })
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function handleDialogClosed() {
  formRef.value?.clearValidate()
}

/** 空字符串统一转 null，避免后端校验失败 */
function emptyToNull(value: string) {
  const text = value.trim()
  return text === '' ? null : text
}

async function handleSubmit() {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  const payload = {
    partCode: form.partCode.trim(),
    partName: form.partName.trim(),
    categoryId: form.categoryId ?? null,
    spec: emptyToNull(form.spec),
    brand: emptyToNull(form.brand),
    unit: form.unit.trim(),
    isGeneral: form.isGeneral,
    safetyStock: form.safetyStock ?? 0,
    maxStock: form.maxStock ?? 0,
    shelfLifeDays: form.shelfLifeDays ?? 0,
    trackByItem: form.trackByItem,
    scanEnabled: form.scanEnabled,
    remark: emptyToNull(form.remark),
    status: form.status
  }

  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createPart(payload)
      ElMessage.success('配件新增成功')
    } else if (editingId.value !== null) {
      await updatePart(editingId.value, payload)
      ElMessage.success('配件更新成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: Part) {
  const nextStatus = row.status === 1 ? 0 : 1
  const action = nextStatus === 1 ? '启用' : '停用'
  try {
    await ElMessageBox.confirm(`确定要${action}配件「${row.partName}」吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await updatePart(row.id, { status: nextStatus })
    ElMessage.success(`${action}成功`)
    await loadData()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

// ---------------------------------------------------------------- 配件详情

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailPart = ref<Part | null>(null)
const partModels = ref<PartVehicleModel[]>([])
const unitConversions = ref<PartUnitConversion[]>([])
const inventoryRows = ref<InventoryDetail[]>([])
const inventoryLoading = ref(false)

const qrVisible = ref(false)
const qrContent = ref('')
const partQrRef = ref<{ getDataUrl: () => string } | null>(null)

const vehicleModelOptions = ref<VehicleModelOption[]>([])
const modelForm = reactive<{ modelId: number | undefined; remark: string }>({
  modelId: undefined,
  remark: ''
})
const modelSubmitting = ref(false)

const unitForm = reactive<{ fromUnit: string; toUnit: string; rate: number | undefined }>({
  fromUnit: '',
  toUnit: '',
  rate: undefined
})
const unitSubmitting = ref(false)

async function ensureVehicleModelOptions() {
  if (vehicleModelOptions.value.length > 0) {
    return
  }
  try {
    vehicleModelOptions.value = await getVehicleModelOptions()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadPartModels(partId: number) {
  try {
    const res = await getPartModels(partId)
    partModels.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadUnitConversions(partId: number) {
  try {
    const res = await getPartUnitConversions(partId)
    unitConversions.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function loadInventory(partId: number) {
  inventoryLoading.value = true
  try {
    // 后端单页最多 200 条，配件库存通常按仓库/库位拆分，足够覆盖
    const res = await getInventoryList({ page: 1, pageSize: 200, partId })
    inventoryRows.value = res.data.list
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    inventoryLoading.value = false
  }
}

async function openDetail(row: Part) {
  detailVisible.value = true
  detailLoading.value = true
  detailPart.value = null
  partModels.value = []
  unitConversions.value = []
  inventoryRows.value = []
  modelForm.modelId = undefined
  modelForm.remark = ''
  unitForm.fromUnit = row.unit
  unitForm.toUnit = ''
  unitForm.rate = undefined

  try {
    const res = await getPartDetail(row.id)
    detailPart.value = res.data
  } catch {
    // 错误提示由 request 拦截器统一处理
  }

  await Promise.all([
    loadPartModels(row.id),
    loadUnitConversions(row.id),
    loadInventory(row.id),
    ensureVehicleModelOptions()
  ])
  detailLoading.value = false
}

/** 查看配件二维码（内容为配件编码） */
function openQrcode(row: Part) {
  qrContent.value = row.partCode
  qrVisible.value = true
}

/** 下载配件二维码 PNG */
function handleDownloadQrcode() {
  const dataUrl = partQrRef.value?.getDataUrl() ?? ''
  if (!dataUrl) {
    ElMessage.warning('二维码尚未生成，请稍后重试')
    return
  }
  const link = document.createElement('a')
  link.href = dataUrl
  // 去掉文件名中 Windows 不允许的字符
  link.download = `配件二维码_${qrContent.value.replace(/[\\/:*?"<>|]/g, '_')}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

async function handleAddModel() {
  if (!detailPart.value) {
    return
  }
  if (!modelForm.modelId) {
    ElMessage.warning('请先选择车型')
    return
  }
  if (partModels.value.some((item) => item.modelId === modelForm.modelId)) {
    ElMessage.warning('该车型已添加')
    return
  }

  modelSubmitting.value = true
  try {
    await addPartModel(detailPart.value.id, {
      modelId: modelForm.modelId,
      remark: emptyToNull(modelForm.remark)
    })
    ElMessage.success('适配车型添加成功')
    modelForm.modelId = undefined
    modelForm.remark = ''
    await loadPartModels(detailPart.value.id)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    modelSubmitting.value = false
  }
}

async function handleDeleteModel(row: PartVehicleModel) {
  if (!detailPart.value) {
    return
  }
  try {
    await ElMessageBox.confirm('确定要移除该适配车型吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await deletePartModel(detailPart.value.id, row.modelId)
    ElMessage.success('移除成功')
    await loadPartModels(detailPart.value.id)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleAddUnit() {
  if (!detailPart.value) {
    return
  }
  const fromUnit = unitForm.fromUnit.trim()
  const toUnit = unitForm.toUnit.trim()
  if (!fromUnit || !toUnit) {
    ElMessage.warning('请填写源单位和目标单位')
    return
  }
  if (fromUnit === toUnit) {
    ElMessage.warning('源单位与目标单位不能相同')
    return
  }
  if (!unitForm.rate || unitForm.rate <= 0) {
    ElMessage.warning('请输入大于 0 的换算比例')
    return
  }

  unitSubmitting.value = true
  try {
    await addPartUnitConversion(detailPart.value.id, {
      fromUnit,
      toUnit,
      rate: unitForm.rate
    })
    ElMessage.success('单位换算添加成功')
    unitForm.toUnit = ''
    unitForm.rate = undefined
    await loadUnitConversions(detailPart.value.id)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    unitSubmitting.value = false
  }
}

async function handleDeleteUnit(row: PartUnitConversion) {
  if (!detailPart.value) {
    return
  }
  try {
    await ElMessageBox.confirm('确定要删除该单位换算吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await deletePartUnitConversion(detailPart.value.id, row.id)
    ElMessage.success('删除成功')
    await loadUnitConversions(detailPart.value.id)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

onMounted(() => {
  void loadCategoryTree()
  void loadData()
})
</script>

<style scoped lang="scss">
.part-page {
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
  width: 200px;
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

  &__actions {
    display: flex;
    align-items: center;
    gap: 8px;
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

.switch-with-tip {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

.part-detail {
  min-height: 200px;
}

.inline-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;

  &__select {
    width: 240px;
  }

  &__input {
    width: 200px;
  }

  &__unit {
    width: 120px;
  }

  &__rate {
    width: 140px;
  }

  &__sep {
    color: var(--el-text-color-secondary);
  }
}

.detail-table {
  margin-bottom: 8px;
}

.qr-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 0 4px;

  &__value {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    text-align: center;
    word-break: break-all;
  }

  .form-tip {
    text-align: center;
  }
}
</style>
