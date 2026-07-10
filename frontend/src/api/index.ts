import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：附加 Bearer token
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('qi_token')
    if (token) {
      config.headers = config.headers ?? {}
      ;(config.headers as Record<string, string>).Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：直接返回 data，401 时登出并跳转登录
http.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const status = error?.response?.status
    if (status === 401) {
      const { useAuthStore } = await import('@/stores/auth')
      const auth = useAuthStore()
      auth.logout()
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.error('登录已过期，请重新登录')
        router.replace('/login')
      }
    } else {
      const detail = error?.response?.data?.detail
      const msg = (typeof detail === 'string' ? detail : '') || error?.message || '请求失败'
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

// 泛型请求包装，interceptor 已返回 data，此处断言为 T
export function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  return http.request(config) as unknown as Promise<T>
}

export default http
