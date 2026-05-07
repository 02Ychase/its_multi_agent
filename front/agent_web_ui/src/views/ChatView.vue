<template>
  <div class="chat-layout">
    <Sidebar
      :expanded="sidebarExpanded"
      :selected-nav="chat.selectedNavItem"
      :selected-session-id="chat.selectedSessionId"
      :sessions="chat.sessions"
      :is-loading-sessions="chat.isLoadingSessions"
      @toggle="sidebarExpanded = !sidebarExpanded"
      @new-session="chat.createNewSession"
      @select-nav="handleNavSelect"
      @select-session="chat.selectSession"
      @delete-session="handleDeleteSession"
    />

    <div class="chat-main">
      <!-- Top bar -->
      <div class="top-bar">
        <div class="top-bar-left">
          <span class="current-title">{{ currentTitle }}</span>
        </div>
        <UserAvatar
          :username="auth.username"
          @logout="handleLogout"
        />
      </div>

      <!-- Messages area -->
      <div class="chat-message-container" ref="messagesRef">
        <!-- Welcome screen -->
        <div v-if="chat.chatMessages.length === 0 && !chat.selectedNavItem" class="welcome-screen">
          <img src="/its-logo.svg" alt="ITS" class="welcome-logo" />
          <h2 class="welcome-title">ITS 智能客服</h2>
          <p class="welcome-subtitle">多智能体协作 · 知识库检索 · 联网搜索</p>
          <div class="welcome-chips">
            <div class="chip" @click="quickSend('电脑蓝屏了怎么办')">
              <el-icon><Monitor /></el-icon>
              <span>电脑蓝屏了怎么办</span>
            </div>
            <div class="chip" @click="quickSend('如何恢复出厂设置')">
              <el-icon><RefreshRight /></el-icon>
              <span>如何恢复出厂设置</span>
            </div>
            <div class="chip" @click="quickSend('附近有哪些服务网点')">
              <el-icon><Location /></el-icon>
              <span>附近有哪些服务网点</span>
            </div>
          </div>
        </div>

        <!-- Nav info pages -->
        <div v-else-if="chat.selectedNavItem && chat.chatMessages.length === 0" class="nav-info-page">
          <el-icon :size="48" class="nav-info-icon">
            <Document v-if="chat.selectedNavItem === 'knowledge'" />
            <Location v-else-if="chat.selectedNavItem === 'service'" />
            <Search v-else />
          </el-icon>
          <h3>{{ navLabels[chat.selectedNavItem] }}</h3>
          <p>请在下方输入您的问题</p>
        </div>

        <!-- Messages -->
        <ChatMessage
          v-for="(msg, index) in chat.chatMessages"
          :key="index"
          :message="msg"
          :is-processing="chat.isProcessing"
          :is-last="index === chat.chatMessages.length - 1"
          @toggle-thinking="chat.toggleThinking(index)"
        />
      </div>

      <!-- Input -->
      <ChatInput
        :is-processing="chat.isProcessing"
        @send="handleSend"
        @cancel="chat.cancelRequest"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { Monitor, RefreshRight, Location, Document, Search } from '@element-plus/icons-vue'
import Sidebar from '../components/Sidebar.vue'
import UserAvatar from '../components/UserAvatar.vue'
import ChatMessage from '../components/ChatMessage.vue'
import ChatInput from '../components/ChatInput.vue'

const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()

const sidebarExpanded = ref(true)
const messagesRef = ref(null)

const navLabels = {
  knowledge: '知识库查询',
  service: '服务站查询',
  network: '联网搜索'
}

const currentTitle = computed(() => {
  if (chat.selectedNavItem) return navLabels[chat.selectedNavItem]
  if (chat.selectedSessionId) {
    const session = chat.sessions.find(s => s.session_id === chat.selectedSessionId)
    return session?.memory?.[0]?.content?.substring(0, 30) || '当前会话'
  }
  return 'ITS 智能客服'
})

function handleNavSelect(key) {
  chat.selectNavItem(key)
}

async function handleDeleteSession(sessionId) {
  await chat.deleteSession(sessionId)
}

function handleSend(text) {
  if (chat.selectedNavItem) {
    const prefix = {
      knowledge: '请查询知识库：',
      service: '请查询服务站：',
      network: '请联网搜索：'
    }
    chat.sendMessage((prefix[chat.selectedNavItem] || '') + text)
  } else {
    chat.sendMessage(text)
  }
}

function quickSend(text) {
  chat.sendMessage(text)
}

function handleLogout() {
  auth.logout()
  chat.clearChat()
  router.push('/login')
}

function handleKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    chat.createNewSession()
  }
}

watch(() => auth.isLoggedIn, (val) => {
  if (val) chat.fetchSessions()
})

onMounted(() => {
  if (auth.isLoggedIn) chat.fetchSessions()
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: var(--color-background);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  min-height: 56px;
  background-color: var(--color-surface);
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.current-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.chat-message-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

/* Welcome Screen */
.welcome-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.welcome-logo {
  width: 64px;
  height: 64px;
  margin-bottom: var(--space-6);
  opacity: 0.9;
}

.welcome-title {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.welcome-subtitle {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-bottom: var(--space-10);
}

.welcome-chips {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  justify-content: center;
}

.chip {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background-color: var(--color-accent-light);
}

/* Nav Info Page */
.nav-info-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-muted);
}

.nav-info-icon {
  margin-bottom: var(--space-4);
  opacity: 0.5;
  color: var(--color-accent);
}

.nav-info-page h3 {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.nav-info-page p {
  font-size: var(--text-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    z-index: 50;
    height: 100vh;
  }

  .sidebar.collapsed {
    width: 0;
    border: none;
  }

  .welcome-chips {
    flex-direction: column;
    align-items: center;
  }

  .chat-message-container {
    padding: var(--space-4);
  }
}
</style>
