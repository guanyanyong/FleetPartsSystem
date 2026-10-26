import request from '@/utils/request'

export type UserRole = 'admin' | 'keeper' | 'purchaser' | 'leader' | 'readonly'

/** 登录请求体，与后端 LoginRequest 对应 */
export interface LoginParams {
  username: string
  password: string
}

/** 当前用户信息，与后端 AuthUserVO 对应（响应为 camelCase） */
export interface UserInfo {
  id: number
  username: string
  realName: string | null
  role: UserRole
  defaultWarehouseId: number | null
}

/** 登录响应 data，与后端 LoginVO 对应 */
export interface LoginResult {
  token: string
  tokenType: string
  expiresIn: number
  userInfo: UserInfo
}

/** 账号密码登录 */
export function login(data: LoginParams) {
  return request.post<LoginResult>('/auth/login', data)
}

/** 获取当前登录用户信息 */
export function getUserInfo() {
  return request.get<UserInfo>('/auth/me')
}

/** 退出登录（JWT 无状态，服务端仅记录日志） */
export function logout() {
  return request.post<null>('/auth/logout')
}
