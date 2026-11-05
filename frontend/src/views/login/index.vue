<template>
  <div class="login-container">
    <div class="login-card">
      <div class="header-section">
        <div class="logo-circle">
          <el-icon :size="32" color="#3b82f6"><Compass /></el-icon>
        </div>
        <h2 class="title">企业内部知识问答平台</h2>
        <p class="subtitle">私有化 RAG 驱动 · 文档智能检索与可溯源解答</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入登录密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="handleLogin"
        >
          {{ loading ? '正在验证安全凭据...' : '登 录 系 统' }}
        </el-button>
      </el-form>

      <!-- 快速演示账号填充 -->
      <div class="demo-box">
        <span class="demo-label">快速体验预填：</span>
        <el-button size="small" round @click="fillAccount('admin', 'admin123')">
          管理员 (admin)
        </el-button>
        <el-button size="small" round @click="fillAccount('staff', 'staff123')">
          普通员工 (staff)
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import { User, Lock, Compass } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入登录密码', trigger: 'blur' }]
}

const fillAccount = (u, p) => {
  loginForm.username = u
  loginForm.password = p
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(loginForm)
      ElMessage.success(`欢迎回来，${userStore.username} (${userStore.roleName})`)
      router.push('/chat')
    } catch (err) {
      // 错误已由 request 拦截器统一提示
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(30, 41, 59) 90%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.header-section {
  text-align: center;
  margin-bottom: 30px;
}

.logo-circle {
  width: 60px;
  height: 60px;
  background: #eff6ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
}

.login-form {
  margin-bottom: 20px;
}

.submit-btn {
  width: 100%;
  font-weight: 600;
  letter-spacing: 1px;
  margin-top: 10px;
  background-color: #2563eb;
  border-color: #2563eb;
}

.submit-btn:hover {
  background-color: #1d4ed8;
  border-color: #1d4ed8;
}

.demo-box {
  border-top: 1px dashed #e2e8f0;
  padding-top: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.demo-label {
  font-size: 12px;
  color: #64748b;
}
</style>
