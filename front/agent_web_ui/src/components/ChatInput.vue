<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        class="chat-textarea"
        placeholder="请输入您的问题..."
        :disabled="isProcessing"
        rows="1"
        @input="autoResize"
        @keydown="handleKeydown"
      />
      <button
        class="send-btn"
        :class="{ 'cancel': isProcessing, 'disabled': !inputText.trim() && !isProcessing }"
        :disabled="!inputText.trim() && !isProcessing"
        @click="handleClick"
      >
        <el-icon v-if="isProcessing" :size="18"><VideoPause /></el-icon>
        <el-icon v-else :size="18"><Promotion /></el-icon>
      </button>
    </div>
    <div class="input-hint">
      <span>按 Enter 发送，Shift + Enter 换行</span>
      <span class="shortcut-hint">
        <kbd>Ctrl</kbd> + <kbd>K</kbd> 新建会话
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'

const props = defineProps({
  isProcessing: Boolean
})

const emit = defineEmits(['send', 'cancel'])

const inputText = ref('')
const textareaRef = ref(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleClick()
  }
}

function handleClick() {
  if (props.isProcessing) {
    emit('cancel')
  } else if (inputText.value.trim()) {
    emit('send', inputText.value)
    inputText.value = ''
    nextTick(() => {
      if (textareaRef.value) {
        textareaRef.value.style.height = 'auto'
      }
    })
  }
}
</script>

<style scoped>
.chat-input-container {
  padding: var(--space-4) var(--space-6);
  background-color: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input-wrapper:focus-within {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-light);
}

.chat-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.6;
  resize: none;
  min-height: 24px;
  max-height: 160px;
}

.chat-textarea::placeholder {
  color: var(--text-muted);
}

.chat-textarea:disabled {
  opacity: 0.6;
}

.send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  border: none;
  background-color: var(--color-accent);
  color: var(--color-on-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color var(--transition-fast);
}

.send-btn:hover:not(:disabled) {
  background-color: var(--color-accent-hover);
}

.send-btn.cancel {
  background-color: var(--color-destructive);
}

.send-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-hint {
  max-width: 800px;
  margin: var(--space-2) auto 0;
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.shortcut-hint kbd {
  background-color: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: var(--font-mono);
  font-size: 11px;
}
</style>
