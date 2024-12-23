<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <el-icon class="login-icon"><Monitor /></el-icon>
        <h2>管理员登录</h2>
      </div>
      <el-form 
        ref="loginForm"
        :model="loginForm"
        :rules="rules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button 
            type="primary" 
            class="login-button" 
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import { Monitor, User, Lock } from '@element-plus/icons-vue'
import { API_URLS } from '@/config/api'
import axios from 'axios'

export default {
  setup() {
    return {
      Monitor,
      User,
      Lock
    }
  },
  data() {
    return {
      loading: false,
      loginForm: {
        username: '',
        password: ''
      },
      rules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    async handleLogin() {
      try {
        await this.$refs.loginForm.validate()
        this.loading = true
        
        const { data } = await axios.post(API_URLS.LOGIN, this.loginForm)
        
        if (data.status === 'success') {
          localStorage.setItem('token', data.token)
          this.$router.push('/admin')
          this.$message.success('登录成功')
        } else {
          this.$message.error(data.message || '登录失败')
        }
      } catch (error) {
        console.error('登录错误:', error)
        this.$message.error(error.response?.data?.message || '登录失败，请检查输入')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #f6f8ff 0%, #f1f5ff 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 16px;
}

.login-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 24px;
  font-weight: 600;
}

.login-form {
  margin-top: 30px;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  padding: 12px;
}

.login-button {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  font-size: 16px;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-input__prefix) {
  font-size: 18px;
}
</style>