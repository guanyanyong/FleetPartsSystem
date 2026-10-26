import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig
} from 'axios'
import { ElMessage } from 'element-plus'

import { getToken, removeToken } from '@/utils/auth'

declare module 'axios' {
  export interface AxiosRequestConfig<D = any> {
    /**
     * 静默请求：业务/网络错误不弹出全局提示，由调用方自行降级处理。
     * 用于「后端可选接口」探测，例如扫码接口未实现时的回退查询。
     */
    silent?: boolean
  }
}

/** 后端统一响应结构：{ code, message, data } */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/**
 * 业务异常：保留后端业务错误码。
 *
 * 扫码出库等场景需要按错误码（2002/2003/2004/4001）给出不同的提示文案，
 * 因此统一把 `body.code` 挂到 Error 上，页面可通过 `(error as ApiError).code` 读取。
 */
export class ApiError extends Error {
  readonly code?: number

  constructor(message: string, code?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

/** 业务错误响应体（FastAPI HTTPException / 参数校验） */
interface ErrorPayload {
  code?: number
  message?: string
  detail?: string | Array<{ msg?: string }>
}

export interface RequestInstance {
  request<T = unknown>(config: AxiosRequestConfig): Promise<ApiResponse<T>>
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
}

const service = axios.create({
  // 开发环境为 /api（由 vite 代理重写到 /api/v1），生产环境为 /api/v1
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/** 请求拦截：自动携带 Authorization: Bearer <token> */
service.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 401 统一处理：清除 token 并跳转登录页，保留原地址便于登录后回跳 */
function redirectToLogin(): void {
  removeToken()
  if (window.location.pathname === '/login') {
    return
  }
  const redirect = `${window.location.pathname}${window.location.search}`
  window.location.replace(`/login?redirect=${encodeURIComponent(redirect)}`)
}

function resolveErrorMessage(error: AxiosError<ErrorPayload>): string {
  const data = error.response?.data
  if (data?.message) {
    return data.message
  }
  if (typeof data?.detail === 'string' && data.detail) {
    return data.detail
  }
  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    return data.detail[0]?.msg || '请求参数错误'
  }
  if (error.response?.status) {
    return `请求失败（${error.response.status}）`
  }
  return error.message || '网络错误'
}

service.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    // 文件下载等非标准响应直接放行
    if (!body || typeof body !== 'object' || typeof body.code === 'undefined') {
      return response
    }

    if (body.code !== 200) {
      const message = body.message || '请求失败'
      if (!response.config.silent) {
        ElMessage.error(message)
      }

      // 登录接口的 401 表示账号密码错误，不触发跳转；其余业务 401 视为登录失效
      if (body.code === 401 && !response.config.url?.includes('/auth/login')) {
        redirectToLogin()
      }

      return Promise.reject(new ApiError(message, body.code))
    }

    return response
  },
  (error: AxiosError<ErrorPayload>) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login')

    // 登录接口自身的 401 表示账号或密码错误，交由 resolveErrorMessage 提示
    if (error.response?.status === 401 && !isLoginRequest) {
      if (!error.config?.silent) {
        ElMessage.error('登录已过期，请重新登录')
      }
      redirectToLogin()
      return Promise.reject(error)
    }

    if (!error.config?.silent) {
      ElMessage.error(resolveErrorMessage(error))
    }
    return Promise.reject(error)
  }
)

/** 统一解包 AxiosResponse，业务代码直接拿到 { code, message, data } */
async function unwrap<T>(promise: Promise<AxiosResponse<ApiResponse<T>>>): Promise<ApiResponse<T>> {
  const response = await promise
  return response.data
}

const request: RequestInstance = {
  request<T = unknown>(config: AxiosRequestConfig) {
    return unwrap<T>(service.request<ApiResponse<T>>(config))
  },
  get<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return unwrap<T>(service.get<ApiResponse<T>>(url, config))
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return unwrap<T>(service.delete<ApiResponse<T>>(url, config))
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return unwrap<T>(service.post<ApiResponse<T>>(url, data, config))
  },
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return unwrap<T>(service.put<ApiResponse<T>>(url, data, config))
  },
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return unwrap<T>(service.patch<ApiResponse<T>>(url, data, config))
  }
}

export default request
