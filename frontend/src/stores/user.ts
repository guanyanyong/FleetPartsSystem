import { computed, ref } from 'vue'

import { defineStore } from 'pinia'

import {
  getUserInfo as getUserInfoApi,
  login as loginApi,
  logout as logoutApi,
  type LoginParams,
  type LoginResult,
  type UserInfo
} from '@/api/auth'
import { getToken, removeToken, setToken } from '@/utils/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(getToken())
  const userInfo = ref<UserInfo | null>(null)

  const isLogin = computed(() => Boolean(token.value))
  const role = computed(() => userInfo.value?.role || '')
  const displayName = computed(() => userInfo.value?.realName || userInfo.value?.username || '')

  /** 登录：保存 token 与用户信息 */
  async function login(form: LoginParams): Promise<LoginResult> {
    const res = await loginApi(form)
    token.value = res.data.token
    setToken(res.data.token)
    userInfo.value = res.data.userInfo
    return res.data
  }

  /** 刷新页面后拉取当前用户信息 */
  async function fetchUserInfo(): Promise<UserInfo> {
    const res = await getUserInfoApi()
    userInfo.value = res.data
    return res.data
  }

  /**
   * 退出登录
   * @param remote 是否调用后端退出接口（401 等异常场景传 false，仅清理本地状态）
   */
  async function logout(remote = false): Promise<void> {
    if (remote && token.value) {
      try {
        await logoutApi()
      } catch {
        // 退出接口异常不阻塞本地清理
      }
    }
    token.value = ''
    userInfo.value = null
    removeToken()
  }

  return {
    token,
    userInfo,
    isLogin,
    role,
    displayName,
    login,
    fetchUserInfo,
    logout
  }
})
