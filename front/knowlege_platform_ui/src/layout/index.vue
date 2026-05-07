<template>
  <div class="app-wrapper">
    <div class="sidebar">
      <div class="logo-area">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="logo-text">ITS Knowledge</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="el-menu-vertical"
      >
        <el-menu-item index="/knowledge">
          <el-icon><Files /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
      </el-menu>
    </div>
    <div class="main-container">
      <router-view v-slot="{ Component }">
        <transition name="fade-transform" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: var(--color-background);
  color: var(--text-primary);
}

.sidebar {
  width: 260px;
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .logo-area {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border-bottom: 1px solid var(--color-border);
    padding: 0 20px;

    .logo-icon {
      width: 28px;
      height: 28px;
      color: var(--color-accent);
    }

    .logo-text {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: 0.5px;
    }
  }

  .el-menu-vertical {
    border-right: none;
    padding: 8px;

    :deep(.el-menu-item) {
      border-radius: 8px;
      margin-bottom: 4px;
      height: 44px;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-secondary);

      &:hover {
        background-color: var(--color-surface-raised);
        color: var(--text-primary);
      }

      &.is-active {
        background-color: var(--color-accent-light);
        color: var(--color-accent);
        font-weight: 600;
      }
    }
  }
}

.main-container {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: var(--color-background);
}

.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.2s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-12px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
