import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useUserStore } from '@/stores/user'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面标题，用于面包屑与 document.title */
    title?: string
    /** Element Plus 图标组件名 */
    icon?: string
    /** 是否在侧边栏隐藏（新建、详情等页面） */
    hidden?: boolean
  }
}

export interface MenuItem {
  title: string
  icon?: string
  path?: string
  children?: MenuItem[]
}

/**
 * 侧边栏菜单：与 frontend-requirements.md「四、页面清单与路由」保持一致。
 * 仅展示一级/二级菜单页面，新建页与详情页通过列表页进入。
 */
export const menuItems: MenuItem[] = [
  { path: '/dashboard', title: '首页看板', icon: 'Odometer' },
  {
    title: '配件管理',
    icon: 'Box',
    children: [
      { path: '/part', title: '配件列表' },
      { path: '/part/category', title: '配件分类' }
    ]
  },
  {
    title: '车辆管理',
    icon: 'Van',
    children: [
      { path: '/vehicle', title: '车辆列表' },
      { path: '/vehicle/model', title: '车型管理' }
    ]
  },
  { path: '/supplier', title: '供应商管理', icon: 'OfficeBuilding' },
  {
    title: '仓库管理',
    icon: 'House',
    children: [
      { path: '/warehouse', title: '仓库列表' },
      { path: '/warehouse/location', title: '库位管理' }
    ]
  },
  {
    title: '库存管理',
    icon: 'Goods',
    children: [
      { path: '/inventory', title: '库存查询' },
      { path: '/inventory/item', title: '库存件查询' }
    ]
  },
  { path: '/inbound', title: '入库管理', icon: 'Download' },
  { path: '/outbound', title: '出库管理', icon: 'Upload' },
  { path: '/transfer', title: '调拨管理', icon: 'Switch' },
  { path: '/stocktake', title: '盘点管理', icon: 'DocumentChecked' },
  { path: '/workOrder', title: '维修工单', icon: 'Tools' },
  {
    title: '报表中心',
    icon: 'DataAnalysis',
    children: [
      { path: '/report/inventory', title: '库存报表' },
      { path: '/report/transaction', title: '流水报表' },
      { path: '/report/vehicle-cost', title: '单车成本' }
    ]
  },
  {
    title: '系统管理',
    icon: 'Setting',
    children: [
      { path: '/system/user', title: '用户管理' },
      { path: '/system/log', title: '操作日志' }
    ]
  }
]

/** 业务页面已全部实现，保留统一占位组件以便后续扩展 */

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: () => import('@/layouts/BlankLayout.vue'),
    children: [
      {
        path: '',
        name: 'Login',
        component: () => import('@/views/login/index.vue'),
        meta: { title: '登录', hidden: true }
      }
    ]
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '首页看板', icon: 'Odometer' }
      },
      {
        path: 'part',
        name: 'Part',
        component: () => import('@/views/part/index.vue'),
        meta: { title: '配件列表', icon: 'Box' }
      },
      {
        path: 'part/category',
        name: 'PartCategory',
        component: () => import('@/views/part/category.vue'),
        meta: { title: '配件分类', icon: 'Box' }
      },
      {
        path: 'vehicle',
        name: 'Vehicle',
        component: () => import('@/views/vehicle/index.vue'),
        meta: { title: '车辆列表', icon: 'Van' }
      },
      {
        path: 'vehicle/model',
        name: 'VehicleModel',
        component: () => import('@/views/vehicle/model.vue'),
        meta: { title: '车型管理', icon: 'Van' }
      },
      {
        path: 'supplier',
        name: 'Supplier',
        component: () => import('@/views/supplier/index.vue'),
        meta: { title: '供应商管理', icon: 'OfficeBuilding' }
      },
      {
        path: 'warehouse',
        name: 'Warehouse',
        component: () => import('@/views/warehouse/index.vue'),
        meta: { title: '仓库列表', icon: 'House' }
      },
      {
        path: 'warehouse/location',
        name: 'WarehouseLocation',
        component: () => import('@/views/warehouse/location.vue'),
        meta: { title: '库位管理', icon: 'House' }
      },
      {
        path: 'inventory',
        name: 'Inventory',
        component: () => import('@/views/inventory/index.vue'),
        meta: { title: '库存查询', icon: 'Goods' }
      },
      {
        path: 'inventory/item',
        name: 'InventoryItem',
        component: () => import('@/views/inventory/item.vue'),
        meta: { title: '库存件查询', icon: 'Goods' }
      },
      {
        path: 'inventory/item/print',
        name: 'InventoryItemPrint',
        component: () => import('@/views/inventory/item/print.vue'),
        meta: { title: '库存件标签打印', hidden: true }
      },
      {
        path: 'inbound',
        name: 'Inbound',
        component: () => import('@/views/inbound/index.vue'),
        meta: { title: '入库单列表', icon: 'Download' }
      },
      {
        path: 'inbound/create',
        name: 'InboundCreate',
        component: () => import('@/views/inbound/create.vue'),
        meta: { title: '新建入库单', hidden: true }
      },
      {
        path: 'inbound/:id',
        name: 'InboundDetail',
        component: () => import('@/views/inbound/detail.vue'),
        meta: { title: '入库单详情', hidden: true }
      },
      {
        path: 'outbound',
        name: 'Outbound',
        component: () => import('@/views/outbound/index.vue'),
        meta: { title: '出库单列表', icon: 'Upload' }
      },
      {
        path: 'outbound/create',
        name: 'OutboundCreate',
        component: () => import('@/views/outbound/create.vue'),
        meta: { title: '新建出库单', hidden: true }
      },
      {
        path: 'outbound/:id',
        name: 'OutboundDetail',
        component: () => import('@/views/outbound/detail.vue'),
        meta: { title: '出库单详情', hidden: true }
      },
      {
        path: 'transfer',
        name: 'Transfer',
        component: () => import('@/views/transfer/index.vue'),
        meta: { title: '调拨单列表', icon: 'Switch' }
      },
      {
        path: 'stocktake',
        name: 'Stocktake',
        component: () => import('@/views/stocktake/index.vue'),
        meta: { title: '盘点单列表', icon: 'DocumentChecked' }
      },
      {
        path: 'stocktake/:id',
        name: 'StocktakeDetail',
        component: () => import('@/views/stocktake/detail.vue'),
        meta: { title: '盘点单详情', hidden: true }
      },
      {
        path: 'workOrder',
        name: 'WorkOrder',
        component: () => import('@/views/workOrder/index.vue'),
        meta: { title: '维修工单', icon: 'Tools' }
      },
      {
        path: 'report/inventory',
        name: 'ReportInventory',
        component: () => import('@/views/report/inventory.vue'),
        meta: { title: '库存报表', icon: 'DataAnalysis' }
      },
      {
        path: 'report/transaction',
        name: 'ReportTransaction',
        component: () => import('@/views/report/transaction.vue'),
        meta: { title: '流水报表', icon: 'DataAnalysis' }
      },
      {
        path: 'report/vehicle-cost',
        name: 'ReportVehicleCost',
        component: () => import('@/views/report/vehicleCost.vue'),
        meta: { title: '单车成本', icon: 'DataAnalysis' }
      },
      {
        path: 'system/user',
        name: 'SystemUser',
        component: () => import('@/views/system/user.vue'),
        meta: { title: '用户管理', icon: 'Setting' }
      },
      {
        path: 'system/log',
        name: 'SystemLog',
        component: () => import('@/views/system/log.vue'),
        meta: { title: '操作日志', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

const LOGIN_PATH = '/login'
const HOME_PATH = '/dashboard'

/**
 * 全局登录守卫：
 * - 未登录访问业务页面 -> /login?redirect=原地址
 * - 已登录访问 /login -> /dashboard
 * - 刷新页面后 token 存在但用户信息为空时，拉取 /auth/me
 */
router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (to.path === LOGIN_PATH) {
    return userStore.token ? { path: HOME_PATH } : true
  }

  if (!userStore.token) {
    return { path: LOGIN_PATH, query: { redirect: to.fullPath } }
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch {
      userStore.logout()
      return { path: LOGIN_PATH, query: { redirect: to.fullPath } }
    }
  }

  return true
})

const appTitle = import.meta.env.VITE_APP_TITLE || '车队配件库存管理系统'

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - ${appTitle}` : appTitle
})

export default router


