<template>
  <div class="sidebar" :class="{ collapsed: !expanded }">
    <!-- Logo & Toggle -->
    <div class="sidebar-header">
      <div class="logo-area">
        <img src="/its-logo.svg" alt="ITS" class="logo-img" />
        <Transition name="fade">
          <span v-if="expanded" class="logo-text">ITS Agent</span>
        </Transition>
      </div>
      <button class="toggle-btn" @click="$emit('toggle')" :title="expanded ? '收起' : '展开'">
        <el-icon><Fold v-if="expanded" /><Expand v-else /></el-icon>
      </button>
    </div>

    <!-- New Session -->
    <Transition name="fade">
      <div v-if="expanded" class="new-session-wrapper">
        <button class="new-session-btn" @click="$emit('newSession')">
          <el-icon><Plus /></el-icon>
          <span>新建会话</span>
          <span class="shortcut"><kbd>Ctrl</kbd>+<kbd>K</kbd></span>
        </button>
      </div>
    </Transition>

    <!-- Navigation -->
    <Transition name="fade">
      <div v-if="expanded" class="nav-section">
        <div
          v-for="item in navItems"
          :key="item.key"
          :class="['nav-item', { active: selectedNav === item.key }]"
          @click="$emit('selectNav', item.key)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </Transition>

    <!-- Sessions -->
    <Transition name="fade">
      <div v-if="expanded" class="sessions-wrapper">
        <SessionList
          :sessions="sessions"
          :selected-id="selectedSessionId"
          :is-loading="isLoadingSessions"
          @select="(id) => $emit('selectSession', id)"
          @delete="(id) => $emit('deleteSession', id)"
        />
      </div>
    </Transition>

    <!-- Collapsed nav icons -->
    <div v-if="!expanded" class="collapsed-nav">
      <div
        v-for="item in navItems"
        :key="item.key"
        :class="['collapsed-nav-item', { active: selectedNav === item.key }]"
        @click="$emit('selectNav', item.key)"
        :title="item.label"
      >
        <el-icon><component :is="item.icon" /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Fold, Expand, Plus, Document, Location, Search } from '@element-plus/icons-vue'
import SessionList from './SessionList.vue'

defineProps({
  expanded: Boolean,
  selectedNav: String,
  selectedSessionId: String,
  sessions: Array,
  isLoadingSessions: Boolean
})

defineEmits(['toggle', 'newSession', 'selectNav', 'selectSession', 'deleteSession'])

const navItems = [
  { key: 'knowledge', label: '知识库查询', icon: Document },
  { key: 'service', label: '服务站查询', icon: Location },
  { key: 'network', label: '联网搜索', icon: Search }
]
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-expanded);
  height: 100%;
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-border);
  transition: width var(--transition-normal);
  overflow: hidden;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  min-height: 64px;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  overflow: hidden;
}

.logo-img {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.logo-text {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

.toggle-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  background-color: var(--color-surface-raised);
  color: var(--text-primary);
}

.new-session-wrapper {
  padding: var(--space-3) var(--space-4);
}

.new-session-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-accent);
  color: var(--color-on-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: 600;
  font-family: var(--font-sans);
  transition: background-color var(--transition-fast);
}

.new-session-btn:hover {
  background-color: var(--color-accent-hover);
}

.shortcut {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0.8;
}

.shortcut kbd {
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.nav-section {
  padding: var(--space-2) var(--space-3);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  margin-bottom: 2px;
}

.nav-item:hover {
  background-color: var(--color-surface-raised);
  color: var(--text-primary);
}

.nav-item.active {
  background-color: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 600;
}

.sessions-wrapper {
  flex: 1;
  overflow-y: auto;
  border-top: 1px solid var(--color-border);
}

.collapsed-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
}

.collapsed-nav-item {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.collapsed-nav-item:hover {
  background-color: var(--color-surface-raised);
  color: var(--text-primary);
}

.collapsed-nav-item.active {
  color: var(--color-accent);
  background-color: var(--color-accent-light);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
