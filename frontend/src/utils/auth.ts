const TOKEN_KEY = 'token'

/** 读取本地保存的 access token */
export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/** 保存 access token（登录成功后调用） */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 清除 access token（退出登录或 401 时调用） */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
