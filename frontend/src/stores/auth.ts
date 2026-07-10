import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getMe, type LoginPayload, type UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('qi_token') || '')
  const user = ref<UserInfo | null>(null)

  async function login(username: string, password: string) {
    const payload: LoginPayload = { username, password }
    const res = await loginApi(payload)
    token.value = res.access_token
    localStorage.setItem('qi_token', res.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await getMe()
    } catch {
      // ignore — interceptor handles 401
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('qi_token')
  }

  // 初始化：如果有 token 则尝试获取用户信息
  function init() {
    if (token.value) {
      fetchUser()
    }
  }

  return { token, user, login, logout, fetchUser, init }
})
