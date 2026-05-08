<template>
  <div :class="['message-wrapper', message.type]">
    <!-- User message -->
    <div v-if="message.type === 'user'" class="message user-message">
      <div class="message-bubble user-bubble">
        <div class="message-text">{{ message.content }}</div>
      </div>
    </div>

    <!-- Assistant message -->
    <div v-else-if="message.type === 'assistant'" class="message assistant-message">
      <div class="message-avatar">
        <img src="/its-logo.svg" alt="ITS" class="avatar-img" />
      </div>
      <div class="message-bubble assistant-bubble">
        <div class="markdown-body" v-html="renderedContent"></div>
      </div>
    </div>

    <!-- Thinking block -->
    <ThinkingBlock
      v-else-if="message.type === 'THINKING'"
      :content="message.content"
      :collapsed="message.collapsed"
      :is-processing="isProcessing"
      :is-last="isLast"
      @toggle="$emit('toggleThinking')"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import ThinkingBlock from './ThinkingBlock.vue'

const props = defineProps({
  message: Object,
  isProcessing: Boolean,
  isLast: Boolean
})

defineEmits(['toggleThinking'])

marked.setOptions({ breaks: true, gfm: true })

const renderedContent = computed(() => {
  if (!props.message?.content) return ''
  try { return DOMPurify.sanitize(marked.parse(props.message.content)) } catch { return DOMPurify.sanitize(props.message.content) }
})
</script>

<style scoped>
.message-wrapper {
  margin-bottom: var(--space-4);
}

.message {
  display: flex;
  gap: var(--space-3);
  max-width: 800px;
  margin: 0 auto;
}

.user-message {
  justify-content: flex-end;
}

.assistant-message {
  justify-content: flex-start;
}

.message-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background-color: var(--color-accent-light);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
}

.avatar-img {
  width: 24px;
  height: 24px;
}

.message-bubble {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  max-width: 720px;
  line-height: 1.7;
}

.user-bubble {
  background-color: var(--color-accent);
  color: var(--color-on-primary);
  font-size: var(--text-base);
}

.assistant-bubble {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--text-primary);
  font-size: var(--text-base);
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
