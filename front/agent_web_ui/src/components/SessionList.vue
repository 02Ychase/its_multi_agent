<template>
  <div class="session-section">
    <div class="section-header" @click="expanded = !expanded">
      <div class="header-left">
        <el-icon><Clock /></el-icon>
        <span>历史会话</span>
      </div>
      <el-icon class="expand-icon" :class="{ expanded }"><ArrowDown /></el-icon>
    </div>

    <div v-show="expanded" class="session-list">
      <div v-if="isLoading" class="session-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="sessions.length === 0" class="session-empty">
        暂无历史对话
      </div>
      <div
        v-for="session in sessions"
        :key="session.session_id"
        :class="['session-item', { active: session.session_id === selectedId }]"
        @click="$emit('select', session.session_id)"
      >
        <el-icon class="session-icon"><ChatDotRound /></el-icon>
        <span class="session-text">{{ session.memory?.[0]?.content || '空对话' }}</span>
        <button
          class="delete-btn"
          title="删除会话"
          @click.stop="handleDelete(session.session_id)"
        >
          <el-icon :size="16"><Delete /></el-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Clock, ArrowDown, Loading, ChatDotRound, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

defineProps({
  sessions: Array,
  selectedId: String,
  isLoading: Boolean
})

const emit = defineEmits(['select', 'delete'])

const expanded = ref(true)

async function handleDelete(sessionId) {
  try {
    await ElMessageBox.confirm('确定要删除这个会话吗？此操作不可恢复。', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    emit('delete', sessionId)
  } catch {
    // user cancelled
  }
}
</script>

<style scoped>
.session-section {
  margin-top: var(--space-2);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: color var(--transition-fast);
  user-select: none;
}

.section-header:hover {
  color: var(--text-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.expand-icon {
  transition: transform var(--transition-fast);
  font-size: 12px;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.session-list {
  padding: 0 var(--space-2);
}

.session-loading,
.session-empty {
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.session-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);
  margin-bottom: 2px;
}

.session-item:hover {
  background-color: var(--color-surface-raised);
}

.session-item.active {
  background-color: var(--color-accent-light);
  border-left: 3px solid var(--color-accent);
}

.session-icon {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 16px;
}

.session-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.session-item.active .session-text {
  color: var(--color-accent);
  font-weight: 500;
}

.delete-btn {
  flex-shrink: 0;
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: var(--color-destructive);
  background-color: var(--color-destructive-light);
}
</style>
