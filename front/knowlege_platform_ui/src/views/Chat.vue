<template>
  <div class="chat-container">
    <div class="chat-box">
      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="empty-state">
          <el-icon :size="56" color="var(--color-accent)"><ChatDotRound /></el-icon>
          <h3>ITS 智能问答</h3>
          <p>基于知识库为您解答技术问题</p>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="message-item"
          :class="msg.role"
        >
          <div class="avatar">
            <el-avatar :size="36" :style="{ backgroundColor: msg.role === 'user' ? '#0369A1' : '#E0F2FE', color: msg.role === 'user' ? '#fff' : '#0369A1', fontWeight: 600, fontSize: '14px' }">
              {{ msg.role === 'user' ? 'U' : 'AI' }}
            </el-avatar>
          </div>
          <div class="content">
            <div class="bubble">
              <div v-if="msg.loading" class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
              <div v-else v-html="formatContent(msg.content)" class="markdown-body"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="input"
          placeholder="请输入您的问题..."
          :rows="2"
          type="textarea"
          resize="none"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button type="primary" class="send-btn" @click="handleSend" :loading="loading" :disabled="!input.trim()">
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { queryKnowledge } from '@/api/knowledge'
import { Promotion, ChatDotRound } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const input = ref('')
const loading = ref(false)
const messages = ref([])
const messagesRef = ref(null)

marked.setOptions({ breaks: true, gfm: true })

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const formatContent = (text) => {
  if (!text) return ''
  try { return DOMPurify.sanitize(marked.parse(text)) } catch { return DOMPurify.sanitize(text) }
}

const handleSend = async () => {
  if (!input.value.trim() || loading.value) return

  const question = input.value
  input.value = ''

  messages.value.push({ role: 'user', content: question })
  scrollToBottom()

  loading.value = true
  messages.value.push({ role: 'assistant', content: '', loading: true })
  scrollToBottom()

  try {
    const res = await queryKnowledge({ question })
    const botMsg = messages.value[messages.value.length - 1]
    botMsg.loading = false
    botMsg.content = res.answer
  } catch {
    const botMsg = messages.value[messages.value.length - 1]
    botMsg.loading = false
    botMsg.content = '抱歉，查询出错，请稍后重试。'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style lang="scss" scoped>
.chat-container {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.chat-box {
  flex: 1;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages {
  flex: 1;
  padding: 24px;
  overflow-y: auto;

  .empty-state {
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: var(--text-muted);
    gap: 12px;

    h3 {
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary);
    }

    p {
      font-size: 14px;
    }
  }
}

.message-item {
  display: flex;
  margin-bottom: 20px;
  max-width: 720px;

  &.user {
    margin-left: auto;
    flex-direction: row-reverse;

    .content {
      align-items: flex-end;

      .bubble {
        background-color: var(--color-accent);
        color: var(--color-on-primary);
        border-top-right-radius: 4px;
      }
    }

    .avatar {
      margin-left: 12px;
      margin-right: 0;
    }
  }

  &.assistant {
    margin-right: auto;

    .content {
      align-items: flex-start;

      .bubble {
        background-color: var(--color-surface-raised);
        color: var(--text-primary);
        border: 1px solid var(--color-border);
        border-top-left-radius: 4px;
      }
    }

    .avatar {
      margin-right: 12px;
    }
  }
}

.content {
  display: flex;
  flex-direction: column;
  max-width: 75%;

  .bubble {
    padding: 12px 16px;
    border-radius: 12px;
    line-height: 1.7;
    font-size: 14px;
    word-break: break-word;

    :deep(.markdown-body) {
      color: inherit;
      background: transparent;

      p { margin: 0 0 10px 0; &:last-child { margin-bottom: 0; } }
      a { color: var(--color-accent); text-decoration: none; &:hover { text-decoration: underline; } }
      ul, ol { padding-left: 20px; margin: 4px 0; }
      code {
        background-color: rgba(0, 0, 0, 0.06);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9em;
      }
      pre {
        background-color: var(--color-surface);
        border: 1px solid var(--color-border);
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
        code { background: transparent; padding: 0; }
      }
      img { max-width: 100%; border-radius: 8px; margin: 8px 0; }
      blockquote {
        border-left: 3px solid var(--color-accent);
        padding-left: 12px;
        color: var(--text-secondary);
        margin: 8px 0;
      }
      table {
        border-collapse: collapse;
        th, td { border: 1px solid var(--color-border); padding: 6px 10px; }
        th { background-color: var(--color-surface-raised); font-weight: 600; }
      }
    }
  }
}

.input-area {
  padding: 16px 20px;
  background-color: var(--color-surface);
  border-top: 1px solid var(--color-border);
  display: flex;
  gap: 12px;
  align-items: flex-end;

  :deep(.el-textarea__inner) {
    border-radius: 10px;
    font-family: var(--font-sans);
    font-size: 14px;
    padding: 10px 14px;
  }

  .send-btn {
    height: 42px;
    padding: 0 20px;
    border-radius: 10px;
    font-weight: 600;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;

  span {
    display: inline-block;
    width: 7px;
    height: 7px;
    background-color: var(--color-muted);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
