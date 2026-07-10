import http from './index'

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id?: number
  username: string
  role?: string
  email?: string
  [key: string]: unknown
}

export function login(payload: LoginPayload): Promise<LoginResponse> {
  return http.post('/auth/login', payload) as unknown as Promise<LoginResponse>
}

export function getMe(): Promise<UserInfo> {
  return http.get('/auth/me') as unknown as Promise<UserInfo>
}
