<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <img src="/its-logo.svg" alt="ITS Logo" class="login-logo" />
        <h1 class="login-title">{{ isRegister ? '创建账户' : '欢迎回来' }}</h1>
        <p class="login-subtitle">{{ isRegister ? '注册 ITS 智能客服系统' : '登录 ITS 智能客服系统' }}</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item v-if="isRegister" label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="isRegister ? '密码至少6位' : '请输入密码'"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="submit-btn"
            @click="handleSubmit"
          >
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span v-if="isRegister">
          已有账号？<a href="#" @click.prevent="toggleMode">去登录</a>
        </span>
        <span v-else>
          没有账号？<a href="#" @click.prevent="toggleMode">去注册</a>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  username: '',
  email: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

function toggleMode() {
  isRegister.value = !isRegister.value
  form.email = ''
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      if (isRegister.value) {
        await auth.register(form.username, form.email, form.password)
        ElMessage.success('注册成功，请登录')
        isRegister.value = false
        form.email = ''
        form.password = ''
      } else {
        await auth.login(form.username, form.password)
        router.push('/')
      }
    } catch (e) {
      ElMessage.error(e.message)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 50%, #F0FDF4 100%);
  padding: var(--space-4);
}

.login-card {
  width: 100%;
  max-width: 420px;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-10) var(--space-8);
  box-shadow: var(--shadow-lg);
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-logo {
  width: 56px;
  height: 56px;
  margin-bottom: var(--space-4);
}

.login-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.login-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: var(--text-base);
  font-weight: 600;
  border-radius: var(--radius-md);
}

.login-footer {
  text-align: center;
  margin-top: var(--space-6);
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.login-footer a {
  color: var(--color-accent);
  font-weight: 500;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  padding-bottom: var(--space-1);
}

:deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
}
</style>
