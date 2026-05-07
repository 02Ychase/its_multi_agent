<template>
  <div class="user-avatar-wrapper" ref="wrapperRef">
    <div class="avatar-trigger" @click="showDropdown = !showDropdown">
      <el-avatar :size="32" class="avatar">
        {{ username?.charAt(0)?.toUpperCase() || 'U' }}
      </el-avatar>
    </div>

    <Transition name="dropdown">
      <div v-if="showDropdown" class="dropdown-menu">
        <div class="dropdown-user">
          <el-avatar :size="40" class="dropdown-avatar">
            {{ username?.charAt(0)?.toUpperCase() || 'U' }}
          </el-avatar>
          <div class="dropdown-info">
            <span class="dropdown-name">{{ username }}</span>
            <span class="dropdown-role">在线</span>
          </div>
        </div>
        <el-divider style="margin: 8px 0;" />
        <div class="dropdown-item" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { SwitchButton } from '@element-plus/icons-vue'

defineProps({
  username: String
})

const emit = defineEmits(['logout'])

const showDropdown = ref(false)
const wrapperRef = ref(null)

function handleClickOutside(e) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

function handleLogout() {
  showDropdown.value = false
  emit('logout')
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.user-avatar-wrapper {
  position: relative;
}

.avatar-trigger {
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.avatar-trigger:hover {
  opacity: 0.8;
}

.avatar {
  background-color: var(--color-accent);
  color: var(--color-on-primary);
  font-weight: 600;
  font-size: var(--text-sm);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  width: 220px;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  z-index: 100;
  box-shadow: var(--shadow-lg);
}

.dropdown-user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
}

.dropdown-avatar {
  background-color: var(--color-accent);
  color: var(--color-on-primary);
  font-weight: 600;
}

.dropdown-info {
  display: flex;
  flex-direction: column;
}

.dropdown-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.dropdown-role {
  font-size: var(--text-xs);
  color: var(--color-success);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.dropdown-item:hover {
  background-color: var(--color-destructive-light);
  color: var(--color-destructive);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all var(--transition-fast);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
