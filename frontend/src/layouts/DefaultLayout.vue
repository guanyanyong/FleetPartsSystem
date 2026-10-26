<template>
  <el-container class="app-layout">
    <el-aside class="app-sidebar" :width="asideWidth">
      <div class="app-logo">
        <el-icon class="app-logo__icon" :size="24"><Van /></el-icon>
        <span v-show="!sidebarCollapsed" class="app-logo__text">{{ appTitle }}</span>
      </div>

      <el-scrollbar class="app-menu-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          :collapse-transition="false"
          background-color="#001529"
          text-color="rgba(255, 255, 255, 0.72)"
          active-text-color="#409eff"
          router
          unique-opened
        >
          <template v-for="item in menuItems" :key="item.path || item.title">
            <el-sub-menu v-if="item.children?.length" :index="item.path || item.title">
              <template #title>
                <el-icon v-if="item.icon">
                  <component :is="item.icon" />
                </el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="child.path || ''"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item v-else :index="item.path || ''">
              <el-icon v-if="item.icon">
                <component :is="item.icon" />
              </el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="app-body">
      <el-header class="app-header" height="56px">
        <div class="app-header__left">
          <el-button text class="collapse-btn" @click="appStore.toggleSidebar()">
            <el-icon :size="20">
              <Expand v-if="sidebarCollapsed" />
              <Fold v-else />
            </el-icon>
          </el-button>

          <el-breadcrumb separator="/">
            <el-breadcrumb-item
              v-for="(crumb, index) in breadcrumbs"
              :key="`${crumb.title}-${index}`"
              :to="crumb.path && index < breadcrumbs.length - 1 ? { path: crumb.path } : undefined"
            >
              {{ crumb.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="app-header__right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-trigger">
              <el-avatar :size="30" class="user-avatar">{{ avatarText }}</el-avatar>
              <span class="user-name">{{ displayName || '未登录' }}</span>
              <el-tag v-if="roleName" size="small" type="info" effect="plain">
                {{ roleName }}
              </el-tag>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  {{ userStore.userInfo?.username || '-' }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { ArrowDown, Expand, Fold, SwitchButton, Van } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { menuItems, type MenuItem } from '@/router'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'

interface BreadcrumbItem {
  title: string
  path?: string
}

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '车队配件库存管理系统'

const ROLE_NAMES: Record<string, string> = {
  admin: '管理员',
  keeper: '库管员',
  purchaser: '采购员',
  leader: '领导',
  readonly: '只读'
}

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
const asideWidth = computed(() => (sidebarCollapsed.value ? '64px' : '220px'))
const displayName = computed(() => userStore.displayName)
const roleName = computed(() => ROLE_NAMES[userStore.role] || '')
const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase() || 'U')

/** 当前高亮菜单：新建/详情页复用列表页路径 */
const activeMenu = computed(() => {
  const current = route.path
  const paths: string[] = []
  menuItems.forEach((item) => {
    if (item.children?.length) {
      item.children.forEach((child) => {
        if (child.path) {
          paths.push(child.path)
        }
      })
    } else if (item.path) {
      paths.push(item.path)
    }
  })

  const matched = paths
    .filter((path) => current === path || current.startsWith(`${path}/`))
    .sort((a, b) => b.length - a.length)[0]

  return matched || current
})

/** 在菜单树中找到与当前路径匹配的分组/菜单项，用于面包屑 */
function findMenuTrail(path: string): { group?: MenuItem; item?: MenuItem } {
  let best: { group?: MenuItem; item?: MenuItem } = {}
  let bestLength = -1

  menuItems.forEach((group) => {
    const candidates = group.children?.length ? group.children : [group]
    candidates.forEach((item) => {
      if (!item.path) {
        return
      }
      const matched = path === item.path || path.startsWith(`${item.path}/`)
      if (matched && item.path.length > bestLength) {
        bestLength = item.path.length
        best = group.children?.length ? { group, item } : { item }
      }
    })
  })

  return best
}

const breadcrumbs = computed<BreadcrumbItem[]>(() => {
  const list: BreadcrumbItem[] = [{ title: '首页看板', path: '/dashboard' }]
  const trail = findMenuTrail(route.path)

  const append = (title?: string, path?: string) => {
    if (!title || list.some((item) => item.title === title)) {
      return
    }
    list.push({ title, path })
  }

  append(trail.group?.title)
  append(trail.item?.title, trail.item?.path)
  append(route.meta.title)

  return list
})

async function handleCommand(command: string | number | object) {
  if (command !== 'logout') {
    return
  }

  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  await userStore.logout(true)
  ElMessage.success('已退出登录')
  await router.replace('/login')
}
</script>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  overflow: hidden;
}

.app-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #001529;
  transition: width 0.2s ease;
}

.app-logo {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 56px;
  overflow: hidden;
  color: #fff;
  background-color: #002140;

  &__icon {
    color: #409eff;
  }

  &__text {
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
  }
}

.app-menu-scroll {
  flex: 1;
  min-height: 0;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu:not(.el-menu--collapse)) {
  width: 100%;
}

:deep(.el-menu--collapse) {
  width: 64px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 48px;
  line-height: 48px;
}

:deep(.el-menu-item.is-active) {
  background-color: #1f2d3d;
}

.app-body {
  flex-direction: column;
  min-width: 0;
}

.app-header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;

  &__left,
  &__right {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
}

.collapse-btn {
  padding: 6px;
  color: #606266;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
  outline: none;

  &:hover {
    background-color: #f5f7fa;
  }
}

.user-avatar {
  color: #fff;
  background-color: #409eff;
}

.user-name {
  max-width: 140px;
  overflow: hidden;
  font-size: 14px;
  color: #303133;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-main {
  padding: 16px;
  overflow: auto;
  background-color: #f0f2f5;
}

@media (max-width: 768px) {
  .user-name,
  .app-header :deep(.el-tag) {
    display: none;
  }
}
</style>


