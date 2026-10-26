# 车队配件库存管理系统 - 前端开发需求文档

## 一、项目概述

为车队配件库存管理系统开发 Web 前端，支持配件管理、入库、出库、扫码、盘点、调拨、维修工单、报表等功能。

- 前端框架：Vue 3 + Vite + TypeScript
- UI 组件库：Element Plus
- 状态管理：Pinia
- 路由：Vue Router 4
- HTTP：Axios
- 图表：ECharts
- 扫码：html5-qrcode（手机摄像头）+ 扫码枪键盘输入
- 条码/二维码生成：qrcode.js + JsBarcode
- 打印：window.print + CSS @media print

## 二、技术栈详细

| 类别 | 选型 | 版本 |
|---|---|---|
| 框架 | Vue | 3.4+ |
| 构建 | Vite | 5+ |
| 语言 | TypeScript | 5+ |
| UI | Element Plus | 2.6+ |
| 状态 | Pinia | 2+ |
| 路由 | Vue Router | 4+ |
| HTTP | Axios | 1+ |
| 图表 | ECharts | 5+ |
| 二维码 | qrcode | 1.5+ |
| 一维码 | jsbarcode | 3.11+ |
| 扫码 | html5-qrcode | 2.3+ |
| 日期 | dayjs | 1.11+ |
| 工具 | lodash-es | 4+ |

## 三、目录结构

```
src/
├── api/                    # 接口封装
│   ├── auth.ts
│   ├── user.ts
│   ├── vehicle.ts
│   ├── part.ts
│   ├── inventory.ts
│   ├── inventoryItem.ts
│   ├── inbound.ts
│   ├── outbound.ts
│   ├── transfer.ts
│   ├── stocktake.ts
│   ├── workOrder.ts
│   └── report.ts
├── assets/                 # 静态资源
├── components/             # 公共组件
│   ├── ScanInput.vue       # 扫码输入框
│   ├── QrCode.vue          # 二维码生成
│   ├── Barcode.vue         # 一维码生成
│   ├── LabelCard.vue       # 单张标签（40×40mm）
│   ├── LabelPrint.vue      # 标签打印（支持手机查看/单张打印）
│   ├── PartSelect.vue      # 配件选择器
│   ├── VehicleSelect.vue   # 车辆选择器
│   ├── WarehouseSelect.vue # 仓库选择器
│   └── PageTable.vue       # 通用分页表格
├── composables/            # 组合式函数
│   ├── useScan.ts          # 扫码逻辑
│   ├── usePrint.ts         # 打印逻辑
│   └── usePermission.ts    # 权限
├── layouts/                # 布局
│   ├── DefaultLayout.vue
│   └── BlankLayout.vue
├── router/                 # 路由
│   └── index.ts
├── stores/                 # Pinia
│   ├── user.ts
│   ├── app.ts
│   └── cart.ts             # 出库单临时明细
├── styles/                 # 全局样式
│   ├── index.scss
│   └── print.scss
├── types/                  # TS 类型
│   ├── api.d.ts
│   ├── part.d.ts
│   ├── inventory.d.ts
│   └── order.d.ts
├── utils/                  # 工具
│   ├── request.ts          # Axios 封装
│   ├── auth.ts             # Token
│   ├── format.ts           # 格式化
│   └── validate.ts         # 校验
├── views/                  # 页面
│   ├── login/
│   ├── dashboard/
│   ├── part/
│   ├── vehicle/
│   ├── supplier/
│   ├── warehouse/
│   ├── inventory/
│   ├── inbound/
│   ├── outbound/
│   ├── transfer/
│   ├── stocktake/
│   ├── workOrder/
│   ├── report/
│   └── system/
├── App.vue
└── main.ts
```

## 四、页面清单与路由

| 路由 | 页面 | 功能 |
|---|---|---|
| /login | 登录页 | 用户名密码登录 |
| /dashboard | 首页看板 | 库存概览、预警、待办 |
| /part | 配件管理 | 列表、新增、编辑、详情、二维码 |
| /part/category | 配件分类 | 树形分类管理 |
| /vehicle | 车辆管理 | 列表、新增、编辑、详情 |
| /vehicle/model | 车型管理 | 列表、新增、编辑 |
| /supplier | 供应商管理 | 列表、新增、编辑 |
| /warehouse | 仓库管理 | 列表、新增、编辑 |
| /warehouse/location | 库位管理 | 列表、新增、编辑、库位二维码 |
| /inventory | 库存查询 | 按配件/仓库汇总查询 |
| /inventory/item | 库存件查询 | 单件实例查询、二维码打印 |
| /inbound | 入库单列表 | 列表、新建、详情、审核 |
| /inbound/create | 新建入库单 | 扫码入库、手动添加 |
| /inbound/:id | 入库单详情 | 查看、审核、打印标签 |
| /outbound | 出库单列表 | 列表、新建、详情、审核 |
| /outbound/create | 新建出库单 | 扫码出库、手动添加 |
| /outbound/:id | 出库单详情 | 查看、审核 |
| /transfer | 调拨单列表 | 列表、新建、详情 |
| /stocktake | 盘点单列表 | 列表、新建、详情、扫码盘点 |
| /workOrder | 维修工单 | 列表、新建、详情、领料 |
| /report/inventory | 库存报表 | 库存明细、库存汇总 |
| /report/transaction | 流水报表 | 出入库流水 |
| /report/vehicle-cost | 单车成本 | 按车辆统计维修成本 |
| /system/user | 用户管理 | 列表、新增、编辑、角色 |
| /system/log | 操作日志 | 列表、筛选 |

## 五、核心页面详细需求

### 1. 登录页 /login

- 用户名、密码输入
- 登录按钮
- 登录成功后存 token 到 localStorage
- 跳转 /dashboard

### 2. 首页看板 /dashboard

卡片区：
- 配件总数
- 库存总价值
- 低于安全库存配件数（红色）
- 今日入库单数
- 今日出库单数
- 待审核单据数

图表区：
- 近 30 天出入库趋势（折线图）
- 库存分类占比（饼图）
- 低库存 Top10（柱状图）

列表区：
- 库存预警列表（前 10 条）
- 待办事项

### 3. 配件管理 /part

列表页：
- 搜索：配件编码、名称、分类、品牌
- 表格列：编码、名称、分类、规格、品牌、单位、安全库存、当前库存、是否按件追踪、状态、操作
- 操作：编辑、详情、查看二维码、启用/停用
- 顶部按钮：新增配件、导出

新增/编辑弹窗：
- 配件编码（自动生成或手填）
- 配件名称
- 分类（树形选择）
- 规格型号
- 品牌
- 单位
- 是否通用件
- 安全库存
- 最高库存
- 保质期天数
- **是否按件追踪**（开关，说明：开启后入库逐件生成二维码）
- 是否允许扫码出库
- 备注

详情页：
- 基本信息
- 适配车型列表（可增删）
- 单位换算列表（可增删）
- 当前库存（按仓库）
- 最近流水

### 4. 配件分类 /part/category

- 树形表格
- 新增、编辑、删除
- 支持二级分类

### 5. 车辆管理 /vehicle

列表：
- 搜索：车牌号、车型、部门
- 表格列：车牌号、车型、VIN、部门、状态、里程、操作
- 操作：编辑、详情、维修记录

新增/编辑：
- 车牌号
- 车型（下拉）
- VIN
- 发动机号
- 购置日期
- 所属部门
- 状态
- 当前里程
- 备注

### 6. 仓库与库位 /warehouse

仓库列表：
- 名称、地址、负责人、状态、操作

库位管理：
- 按仓库筛选
- 库位编码、二维码、状态
- 支持批量生成库位
- 库位二维码打印

### 7. 库存查询 /inventory

- 搜索：配件、仓库、库位
- 表格：配件编码、名称、规格、仓库、库位、数量、实例数、平均成本、最后入库时间
- 低库存高亮
- 导出 Excel

### 8. 库存件查询 /inventory/item（核心）

- 搜索：item_code、qrcode、配件、状态、批次
- 表格：item_code、配件名称、规格、批次、仓库、库位、状态、入库时间、出库时间、车辆
- 操作：查看二维码、打印标签、查看流水

二维码打印：
- 单个打印
- 批量选择打印
- 标签格式见"标签打印"章节

### 9. 入库单列表 /inbound

- 搜索：单号、供应商、状态、日期范围
- 表格：单号、供应商、仓库、类型、总金额、状态、经办人、入库时间、操作
- 操作：详情、审核、作废、打印标签
- 顶部：新建入库单

### 10. 新建入库单 /inbound/create（核心）

表单：
- 供应商（下拉）
- 入库仓库（下拉）
- 入库类型（采购/退货/调拨/调整）
- 备注

明细区：
- **扫码输入框**（始终聚焦，扫码枪回车触发）
- 手动添加按钮（弹出配件选择器）
- 明细表格：配件编码、名称、规格、单位、数量、单价、金额、批次、生产日期、到期日期、库位、操作（删除）
- 合计金额

扫码逻辑：
- 扫到配件码 → 调 `/api/part/scan` → 返回配件信息 → 追加一行，数量默认 1
- 已存在则数量 +1
- 支持手动修改数量、单价、批次

底部按钮：
- 保存草稿
- 提交审核

### 11. 入库单详情 /inbound/:id

- 基本信息
- 明细表格
- 状态流转按钮：审核通过、作废
- 审核通过后：
  - 若明细中 `track_by_item=1`，弹出提示"已生成 N 个库存件二维码，是否立即打印？"
  - 跳转标签打印页

### 12. 出库单列表 /outbound

同入库单列表结构。

### 13. 新建出库单 /outbound/create（核心）

表单：
- 出库仓库（下拉）
- 出库类型（维修领料/销售/退货/调拨/报废）
- 关联车辆（下拉，可空）
- 关联维修工单（下拉，可空）
- 领用人（下拉）
- 备注

明细区：
- **扫码输入框**（始终聚焦）
- 手动添加按钮
- 明细表格：配件编码、名称、规格、单位、数量、成本、金额、批次、库位、扫码时间、操作
- 合计金额

扫码逻辑（重点）：
- 扫到库存件二维码 → 调 `/api/inventory-item/scan?code=xxx`
- 校验返回 `status == 1`（在库）
- 若已出库/锁定/报废，弹出错误提示，不追加
- 追加一行，写入 `inventory_item_id`、`scan_code`、`scan_type`、`scan_at`
- 同一个件重复扫 → 提示"该件已在明细中"
- 数量固定为 1（单件追踪件）
- 非追踪件：手动选择配件 + 输入数量

底部按钮：
- 保存草稿
- 提交审核

### 14. 出库单详情 /outbound/:id

- 基本信息
- 明细表格（显示每个库存件的 item_code）
- 状态流转：审核通过、作废
- 审核通过后：
  - 库存件 status 改为 3
  - 更新库存
  - 写流水

### 15. 调拨单 /transfer

- 列表、新建、详情
- 新建：调出仓库、调入仓库、明细（配件、数量、调出库位、调入库位）
- 支持扫码选择库存件

### 16. 盘点单 /stocktake（核心）

新建盘点单：
- 选择仓库
- 选择盘点范围（全部/按分类/按库位）

盘点页：
- **扫码输入框**
- 扫到库存件 → 显示该件信息 → 标记为"已盘"
- 未扫到的件显示"未盘"
- 支持手动录入实盘数量
- 差异高亮

盘点完成：
- 生成差异汇总
- 盘盈盘亏走库存流水
- 盘亏的库存件 status 改为 5

### 17. 维修工单 /workOrder

列表：
- 单号、车辆、类型、状态、进厂时间、出厂时间、配件成本、工时费

新建/编辑：
- 车辆（下拉）
- 维修类型
- 故障描述
- 维修负责人
- 进厂时间

详情：
- 基本信息
- 领料记录（关联出库单明细）
- 配件成本合计
- 工时费
- 总成本

领料按钮：
- 跳转到新建出库单，自动带入 work_order_id 和 vehicle_id

### 18. 报表

**库存报表 /report/inventory**
- 按配件汇总
- 按仓库汇总
- 按分类汇总
- 导出 Excel

**流水报表 /report/transaction**
- 时间范围、配件、仓库、业务类型筛选
- 表格：时间、配件、仓库、业务类型、变动数量、变动前后、关联单号、操作人

**单车成本 /report/vehicle-cost**
- 按车辆统计
- 时间范围筛选
- 表格：车牌号、维修次数、配件成本、工时费、总成本
- 图表：Top10 车辆成本柱状图

### 19. 系统管理

**用户管理 /system/user**
- 列表、新增、编辑、重置密码、启用/停用
- 角色分配

**操作日志 /system/log**
- 列表、筛选（用户、模块、时间）
- 查看详情

## 六、核心组件需求

### 1. ScanInput.vue（扫码输入框）

Props：
- placeholder
- disabled
- autoFocus（默认 true）

Events：
- scan（code: string）

逻辑：
- 始终聚焦
- 监听 keydown Enter
- 扫码枪输入完成后触发 scan 事件
- 清空输入框
- 支持手动输入后回车

```vue
<template>
  <el-input
    ref="inputRef"
    v-model="code"
    :placeholder="placeholder"
    :disabled="disabled"
    clearable
    @keydown.enter="handleEnter"
  >
    <template #prefix>
      <el-icon><Scan /></el-icon>
    </template>
  </el-input>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'

const props = defineProps<{
  placeholder?: string
  disabled?: boolean
  autoFocus?: boolean
}>()

const emit = defineEmits<{
  (e: 'scan', code: string): void
}>()

const code = ref('')
const inputRef = ref()

function handleEnter() {
  const val = code.value.trim()
  if (val) {
    emit('scan', val)
    code.value = ''
  }
  nextTick(() => inputRef.value?.focus())
}

onMounted(() => {
  if (props.autoFocus !== false) {
    nextTick(() => inputRef.value?.focus())
  }
})
</script>
```

### 2. QrCode.vue（二维码生成）

Props：
- value: string
- size: number（默认 150）

用 `qrcode` 库生成 canvas。

### 3. Barcode.vue（一维码生成）

Props：
- value: string
- format: string（默认 CODE128）
- width、height

用 `jsbarcode` 库生成 svg。

### 4. LabelPrint.vue（标签打印）

Props：
- items: Array<{ itemCode, partName, spec, batchNo, qrcode, locationCode }>
- 标签尺寸：固定 40mm × 40mm（正方形标签纸，组件内不再提供尺寸切换）

功能：
- 渲染 N 个标签
- 每个标签含：配件名、规格、item_code、二维码、批次、库位（由 LabelCard.vue 渲染，固定 40mm × 40mm）
- 打印按钮触发 window.print（支持打印全部 / 单张打印）
- 点击任一标签打开放大预览（手机浏览器可用），预览内可「打印此标签」「单独打开」（新窗口打开 `/inventory/item/print?id=xx`）
- 复制到 Excel：预览弹窗底部「复制」复制当前标签一行，工具栏「复制全部」复制所有标签（一条一行）；
  字段顺序固定 `配件名 → 规格型号 → 库位 → 批次号 → 库存编码`，中间用制表符 `\t` 分隔（`src/utils/clipboard.ts` 的 `toTsvRow`）
- 纸张可选：标签纸 40×40（`@page size: 40mm 40mm`，一页一张）或 A4（`@page size: A4`，一页多张），偏好存 `localStorage: fleetparts:label-paper`
- CSS @media print 控制打印样式

标签样式：

```
┌─────────────────────┐
│ 机油滤芯             │
│ 0986AF1             │
│ IT20261022000001    │
│ 批次：B20261001      │
│ ┌─────────┐         │
│ │  QR     │         │
│ └─────────┘         │
│ 库位：A-01-03        │
└─────────────────────┘
```

### 5. PartSelect.vue（配件选择器）

- 弹窗形式
- 搜索配件
- 单选/多选
- 返回选中配件

### 6. VehicleSelect.vue（车辆选择器）

- 下拉搜索
- 显示车牌号 + 车型

### 7. PageTable.vue（通用分页表格）

- 封装 el-table + el-pagination
- 支持 loading
- 支持列配置

## 七、状态管理与 API 封装

### stores/user.ts

```ts
import { defineStore } from 'pinia'
import { login, getUserInfo } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null as any
  }),
  actions: {
    async login(form: { username: string; password: string }) {
      const res = await login(form)
      this.token = res.data.token
      localStorage.setItem('token', res.data.token)
    },
    async fetchUserInfo() {
      const res = await getUserInfo()
      this.userInfo = res.data
    },
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
    }
  }
})
```

### stores/cart.ts（出库单临时明细）

```ts
import { defineStore } from 'pinia'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [] as any[]
  }),
  actions: {
    addItem(item: any) {
      const exist = this.items.find(i => i.inventoryItemId === item.inventoryItemId)
      if (exist) {
        throw new Error('该件已在明细中')
      }
      this.items.push(item)
    },
    removeItem(index: number) {
      this.items.splice(index, 1)
    },
    clear() {
      this.items = []
    }
  }
})
```

### utils/request.ts（Axios 封装）

```ts
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000
})

request.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

request.interceptors.response.use(
  res => {
    if (res.data.code !== 200) {
      ElMessage.error(res.data.message || '请求失败')
      return Promise.reject(res.data)
    }
    return res.data
  },
  err => {
    if (err.response?.status === 401) {
      useUserStore().logout()
      window.location.href = '/login'
    }
    ElMessage.error(err.message || '网络错误')
    return Promise.reject(err)
  }
)

export default request
```

## 八、扫码出库完整交互流程

```
1. 用户进入 /outbound/create
2. 选择出库仓库、车辆、工单
3. 光标自动聚焦到扫码框
4. 用户用扫码枪扫描库存件二维码
5. ScanInput 触发 scan 事件，code = "IT20261022000001"
6. 调用 GET /api/inventory-item/scan?code=IT20261022000001
7. 后端返回：
   - 若 status=1：返回配件信息 + 实例信息
   - 若 status!=1：返回错误"该件已出库"
8. 前端校验：
   - 若已在明细中，提示"该件已在明细中"
   - 否则追加一行，写入 inventory_item_id、scan_code、scan_type=QRCODE、scan_at
9. 继续扫码，重复 4-8
10. 点击"提交审核"
11. 后端校验库存、更新实例状态、写流水
12. 提示成功，跳转出库单详情
```

## 九、标签打印需求

### 打印页面 /inventory/item/print?ids=1,2,3（单张直达：/inventory/item/print?id=1）

- 接收库存件ID列表（`ids=1,2,3`）或单个库存件ID（`id=1`）
- 渲染标签
- 每个标签：
  - 配件名称
  - 规格
  - item_code
  - 二维码（qrcode 内容 = item_code）
  - 批次号
  - 库位
- 打印按钮
- 标签尺寸固定 40mm × 40mm（正方形标签纸）；打印纸张可选「标签纸 40×40（一页一张）」或「A4（一页多张）」
- 点击任一标签可放大预览，并支持「打印此标签」「单独打开」（手机浏览器可查看与打印）

### 打印 CSS

打印用 `@page` 由 `LabelPrint.vue` 在运行时注入（`<style id="fleetparts-label-page-style">`），
标签纸模式输出 `@page { size: 40mm 40mm; margin: 0 }`，A4 模式输出 `@page { size: A4 portrait; margin: 6mm }`，
因此 SCSS 的 `@media print { @page { ... } }` 里不要写死 `size`，避免与纸张切换冲突。

```scss
@media print {
  .no-print { display: none !important; }
  .label {
    page-break-inside: avoid;
    width: 40mm;
    height: 40mm;
    padding: 2mm;
    border: none;
    font-size: 10px;
  }
  .label__qr {
    width: 18mm;
    height: 18mm;
  }
  /* 标签纸 40×40：一张标签一页；A4 模式不加，一页多张 */
  .label-print--paper-label .label-print__cell {
    break-after: page;
    page-break-after: always;
  }
}
```

## 十、权限控制

### 角色

| 角色 | 权限 |
|---|---|
| admin | 全部 |
| keeper | 入库、出库、盘点、调拨、库存查询 |
| purchaser | 入库、供应商、配件查询 |
| leader | 报表、审批、查询 |
| readonly | 只读 |

### 前端权限

- 路由守卫：未登录跳 /login
- 按钮级：`v-permission="'inbound:create'"`
- 菜单级：根据角色动态渲染

## 十一、环境变量

`.env.development`：
```
VITE_API_BASE_URL=http://localhost:8080/api
VITE_APP_TITLE=车队配件库存管理系统
```

`.env.production`：
```
VITE_API_BASE_URL=/api
VITE_APP_TITLE=车队配件库存管理系统
```

## 十二、给 DeepSeek 的前端生成提示

```
请根据以上 frontend-requirements.md 文档，用 Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router 生成完整前端项目，要求：

1. 生成 package.json、vite.config.ts、tsconfig.json、index.html
2. 生成 src/main.ts、src/App.vue
3. 生成 src/router/index.ts，包含所有路由和路由守卫
4. 生成 src/stores/user.ts、app.ts、cart.ts
5. 生成 src/utils/request.ts、auth.ts、format.ts
6. 生成 src/api/ 下所有接口封装
7. 生成 src/components/ 下所有公共组件，重点是 ScanInput.vue、QrCode.vue、LabelPrint.vue
8. 生成 src/views/ 下所有页面，优先完成：
   - login
   - dashboard
   - part（列表+新增+编辑）
   - inventory/item（库存件查询+二维码打印）
   - inbound/create（扫码入库）
   - outbound/create（扫码出库）
   - stocktake（扫码盘点）
9. 所有页面用 Element Plus 组件
10. 所有 API 调用用 request.ts 封装
11. 扫码功能用 ScanInput 组件 + html5-qrcode（手机端）
12. 二维码生成用 qrcode 库
13. 标签打印用 LabelPrint 组件 + window.print
14. 代码用 <script setup lang="ts"> 语法
15. 样式用 scss
16. 生成 README.md 说明启动方式

请先输出项目文件树，再逐个输出文件内容。
```

## 十三、开发优先级

### 第一阶段（MVP）
- 登录、布局、路由
- 配件管理
- 仓库/库位管理
- 入库单（含扫码入库）
- 出库单（含扫码出库）
- 库存件查询 + 二维码打印
- 库存查询

### 第二阶段
- 车辆管理
- 供应商管理
- 盘点单（扫码盘点）
- 调拨单
- 维修工单
- 报表

### 第三阶段
- 系统管理
- 权限细化
- 操作日志
- 数据看板优化

## 十四、验收标准

1. 能登录，token 正确存储
2. 配件能增删改查，能设置 track_by_item
3. 入库单能创建、审核，审核后 track_by_item=1 的配件生成 N 个库存件二维码
4. 库存件能查询、打印二维码标签
5. 出库单能扫码出库，扫已出库的件提示错误
6. 出库审核后库存件 status 改为 3，库存数量正确扣减
7. 盘点单能扫码盘点，差异正确计算
8. 所有列表支持分页、搜索
9. 所有表单有校验
10. 打印标签格式正确，能批量打印