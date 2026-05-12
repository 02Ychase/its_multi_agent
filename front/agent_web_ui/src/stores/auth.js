import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('accessToken') || '')
  const refreshToken = ref(localStorage.getItem('refreshToken') || '')
  const username = ref(localStorage.getItem('currentUserId') || '')

  const isLoggedIn = computed(() => !!accessToken.value && !!username.value)

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
  }

  function setUser(name) {
    username.value = name
    localStorage.setItem('currentUserId', name)
  }

  async function login(user, pass) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '用户名或密码错误')
    }
    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    setUser(data.user.username)
  }

  async function register(user, email, pass) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, email, password: pass })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '注册失败')
    }
  }

  async function tryRefreshToken() {
    if (!refreshToken.value) return false
    try {
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value })
      })
      if (!res.ok) return false
      const data = await res.json()
      accessToken.value = data.access_token
      localStorage.setItem('accessToken', data.access_token)
      return true
    } catch {
      return false
    }
  }

  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    username.value = ''
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('currentUserId')
  }

  return { accessToken, refreshToken, username, isLoggedIn, login, register, logout, setTokens, setUser, tryRefreshToken }
})
