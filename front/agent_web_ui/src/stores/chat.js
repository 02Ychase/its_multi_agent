import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import { useAuthStore } from './auth'

const API_BASE = import.meta.env.VITE_API_BASE || ''

/**
 * 带自动 token 刷新的 fetch 封装
 * 遇到 401 时自动尝试 refresh token，成功后重试原请求
 */
async function authFetch(url, options = {}) {
  const auth = useAuthStore()
  const headers = { ...options.headers, 'Authorization': `Bearer ${auth.accessToken}` }

  let res = await fetch(url, { ...options, headers })

  if (res.status === 401 && auth.refreshToken) {
    const refreshed = await auth.tryRefreshToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${auth.accessToken}`
      res = await fetch(url, { ...options, headers })
    }
  }

  return res
}

export const useChatStore = defineStore('chat', () => {
  const chatMessages = ref([])
  const sessions = ref([])
  const selectedSessionId = ref('')
  const selectedNavItem = ref('')
  const isProcessing = ref(false)
  const isLoadingSessions = ref(false)
  let reader = null

  function scrollToBottom() {
    setTimeout(() => {
      const el = document.querySelector('.chat-message-container')
      if (el) el.scrollTop = el.scrollHeight
    }, 0)
  }

  async function fetchSessions() {
    const auth = useAuthStore()
    if (!auth.username) return
    isLoadingSessions.value = true
    try {
      const res = await authFetch(`${API_BASE}/api/user_sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (data.success && data.sessions) {
        sessions.value = data.sessions
        if (data.sessions.length > 0 && !selectedSessionId.value) {
          selectSession(data.sessions[0].session_id)
        }
      }
    } catch (e) {
      console.error('Error fetching sessions:', e)
    } finally {
      isLoadingSessions.value = false
      scrollToBottom()
    }
  }

  function createNewSession() {
    const id = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    sessions.value.unshift({
      session_id: id,
      create_time: new Date().toISOString(),
      memory: [],
      total_messages: 0
    })
    chatMessages.value = []
    selectSession(id)
  }

  function selectSession(sessionId) {
    selectedSessionId.value = sessionId
    selectedNavItem.value = ''
    chatMessages.value = []
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session?.memory?.length) {
      let lastType = null
      session.memory.forEach(msg => {
        if (!msg?.content) return
        let type = msg.role === 'process' ? 'THINKING' : msg.role
        if (type === 'THINKING' && lastType === 'THINKING') {
          const last = chatMessages.value[chatMessages.value.length - 1]
          last.content += '\n' + msg.content
        } else {
          chatMessages.value.push({ type, content: msg.content })
        }
        lastType = type
      })
      nextTick(scrollToBottom)
    }
  }

  function selectNavItem(item) {
    selectedNavItem.value = item
    selectedSessionId.value = ''
    chatMessages.value = []
  }

  async function sendMessage(text) {
    const auth = useAuthStore()
    if (!text.trim() || !auth.isLoggedIn) return

    isProcessing.value = true
    chatMessages.value.forEach(msg => {
      if (msg.type === 'THINKING') msg.collapsed = true
    })
    chatMessages.value.push({ type: 'user', content: text.trim() })
    scrollToBottom()

    try {
      const res = await authFetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text.trim(),
          context: { user_id: auth.username, session_id: selectedSessionId.value || '' }
        })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          if (buffer.trim()) processSSEData(buffer)
          break
        }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        for (let i = 0; i < lines.length - 1; i++) {
          if (lines[i].trim()) processSSEData(lines[i])
        }
        buffer = lines[lines.length - 1]
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        chatMessages.value.push({ type: 'assistant', content: `请求失败: ${e.message}` })
      }
    } finally {
      isProcessing.value = false
      reader = null
      scrollToBottom()
      fetchSessions()
    }
  }

  function processSSEData(data) {
    if (typeof data !== 'string' || !data.startsWith('data:')) return
    const jsonStr = data.substring(5).trim()
    if (!jsonStr) return
    try {
      const parsed = JSON.parse(jsonStr)
      let kind, text
      if (parsed.content && typeof parsed.content === 'object') {
        text = parsed.content.text
        kind = parsed.content.kind || parsed.content.type
        if (parsed.status === 'FINISHED') return
      } else if (parsed.type && parsed.content) {
        kind = parsed.type
        text = parsed.content
      }
      if (kind && text) {
        if (kind === 'ANSWER') appendAnswer(text)
        else if (kind === 'THINKING') appendThinking(text)
        else if (kind === 'STRUCTURED') {
          // 结构化数据：作为特殊消息类型存储
          chatMessages.value.push({
            type: 'STRUCTURED',
            cardType: parsed.content.card_type,
            data: parsed.content.data
          })
          chatMessages.value = [...chatMessages.value]
          scrollToBottom()
        }
        else appendThinking(text + '\n')
      }
    } catch (e) {
      console.error('JSON parse error:', e)
    }
  }

  function appendAnswer(text) {
    text = text.replace(/ +/g, ' ').replace(/\n+/g, '\n')
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (!text.trim() && last?.type !== 'assistant') return
    if (last?.type === 'assistant') {
      last.content += text
    } else {
      chatMessages.value.push({ type: 'assistant', content: text })
    }
    chatMessages.value = [...chatMessages.value]
    scrollToBottom()
  }

  function appendThinking(text) {
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last?.type === 'THINKING') {
      last.content += text
      if (isProcessing.value && last.collapsed === undefined) last.collapsed = false
    } else {
      chatMessages.value.push({ type: 'THINKING', content: text, collapsed: false })
    }
    chatMessages.value = [...chatMessages.value]
    scrollToBottom()
  }

  function cancelRequest() {
    if (reader) { reader.cancel(); reader = null }
    isProcessing.value = false
    chatMessages.value.push({ type: 'THINKING', content: '请求已取消\n', collapsed: true })
  }

  function toggleThinking(index) {
    const msg = chatMessages.value[index]
    if (msg?.type === 'THINKING') msg.collapsed = !msg.collapsed
  }

  async function deleteSession(sessionId) {
    const auth = useAuthStore()
    try {
      const res = await authFetch(`${API_BASE}/api/delete_session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      const data = await res.json()
      // Regardless of backend response, force refresh from server
      const wasSelected = selectedSessionId.value === sessionId
      await fetchSessions()
      if (wasSelected) {
        if (sessions.value.length > 0) {
          selectSession(sessions.value[0].session_id)
        } else {
          selectedSessionId.value = ''
          chatMessages.value = []
        }
      }
      return data
    } catch (e) {
      console.error('Error deleting session:', e)
      // Still try to refresh
      await fetchSessions()
      return { success: false, message: e.message }
    }
  }

  function clearChat() {
    chatMessages.value = []
  }

  return {
    chatMessages, sessions, selectedSessionId, selectedNavItem,
    isProcessing, isLoadingSessions,
    fetchSessions, createNewSession, selectSession, selectNavItem,
    sendMessage, cancelRequest, toggleThinking, clearChat, deleteSession
  }
})
