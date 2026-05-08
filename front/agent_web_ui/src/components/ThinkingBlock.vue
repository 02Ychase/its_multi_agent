<template>
  <div class="thinking-block" @click="$emit('toggle')">
    <div class="thinking-header">
      <el-icon :class="{ 'is-collapsed': collapsed }"><ArrowDown /></el-icon>
      <span>{{ isProcessing && isLast ? '思考中...' : '思考过程' }}</span>
    </div>
    <div v-show="!collapsed" class="thinking-content">
      <div class="markdown-body" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: String,
  collapsed: Boolean,
  isProcessing: Boolean,
  isLast: Boolean
})

defineEmits(['toggle'])

marked.setOptions({ breaks: true, gfm: true })

const renderedContent = computed(() => {
  if (!props.content) return ''
  try { return DOMPurify.sanitize(marked.parse(props.content)) } catch { return DOMPurify.sanitize(props.content) }
})
</script>

<style scoped>
.thinking-block {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
  overflow: hidden;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  user-select: none;
  transition: color var(--transition-fast);
}

.thinking-header:hover {
  color: var(--text-secondary);
}

.thinking-header .el-icon {
  transition: transform var(--transition-fast);
  font-size: 14px;
}

.thinking-header .el-icon.is-collapsed {
  transform: rotate(-90deg);
}

.thinking-content {
  padding: 0 var(--space-4) var(--space-4);
  border-top: 1px solid var(--color-border);
}

.thinking-content .markdown-body {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.7;
}
</style>
