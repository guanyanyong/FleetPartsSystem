import { ref } from 'vue'

import { defineStore } from 'pinia'

const COLLAPSE_KEY = 'app:sidebar-collapsed'

/** 首次访问时：窄屏（手机）默认折叠侧边栏，避免内容区被挤压 */
function readInitialCollapsed(): boolean {
  const saved = localStorage.getItem(COLLAPSE_KEY)
  if (saved === '1') {
    return true
  }
  if (saved === '0') {
    return false
  }
  return window.innerWidth <= 768
}

export const useAppStore = defineStore('app', () => {
  /** 侧边栏是否折叠，刷新后保持上次状态 */
  const sidebarCollapsed = ref<boolean>(readInitialCollapsed())

  function setSidebarCollapsed(collapsed: boolean): void {
    sidebarCollapsed.value = collapsed
    localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
  }

  function toggleSidebar(): void {
    setSidebarCollapsed(!sidebarCollapsed.value)
  }

  return {
    sidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar
  }
})
