<template>
  <div class="admin-container">
    <el-card class="admin-card">
      <template #header>
        <div class="card-header">
          <div class="title">
            <el-icon><Monitor /></el-icon>
            <span>IP白名单管理</span>
          </div>
          <div class="header-buttons">
            <div class="whitelist-control">
              <span class="whitelist-label">白名单控制：</span>
              <el-switch
                v-model="whitelistEnabled"
                active-text="已启用"
                inactive-text="已禁用"
                @change="handleWhitelistChange"
              />
            </div>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>添加IP
            </el-button>
            <el-button @click="showChangePassword">
              <el-icon><Lock /></el-icon>修改密码
            </el-button>
            <el-button type="danger" @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="ips" style="width: 100%">
        <el-table-column prop="ip" label="IP地址"></el-table-column>
        <el-table-column prop="description" label="描述"></el-table-column>
        <el-table-column prop="created_at" label="创建时间">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button type="danger" size="small" @click="handleDelete(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="添加IP" width="30%">
      <el-form :model="newIp">
        <el-form-item label="IP地址">
          <el-input v-model="newIp.ip" placeholder="请输入IP地址"></el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newIp.description" placeholder="请输入描述"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAdd">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <el-card class="admin-card settings-card">
      <template #header>
        <div class="card-header">
          <span>默认阈值设置</span>
        </div>
      </template>
      <div class="settings-form">
        <el-form :model="thresholdSettings" label-width="150px">
          <el-form-item label="白色孤立点大小">
            <el-input-number 
              v-model="thresholdSettings.white_threshold" 
              :min="0"
            />
          </el-form-item>
          <el-form-item label="黑色孤立点大小">
            <el-input-number 
              v-model="thresholdSettings.black_threshold" 
              :min="0"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="updateThresholdSettings">
              保存设置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="30%"
      :close-on-click-modal="false"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            placeholder="请输入旧密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleChangePassword" :loading="passwordLoading">
            确认修改
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Monitor, Plus, Lock, SwitchButton } from '@element-plus/icons-vue'
import { API_URLS } from '@/config/api'
import axios from 'axios'

export default {
  components: {
    Monitor,
    Plus,
    Lock,
    SwitchButton
  },
  data() {
    const validateConfirmPassword = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请再次输入密码'))
      } else if (value !== this.passwordForm.newPassword) {
        callback(new Error('两次输入密码不一致!'))
      } else {
        callback()
      }
    }

    return {
      ips: [],
      dialogVisible: false,
      newIp: {
        ip: '',
        description: ''
      },
      whitelistEnabled: true,
      thresholdSettings: {
        white_threshold: 0,
        black_threshold: 0
      },
      passwordDialogVisible: false,
      passwordLoading: false,
      passwordForm: {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      passwordRules: {
        oldPassword: [
          { required: true, message: '请输入旧密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
        ],
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请再次输入新密码', trigger: 'blur' },
          { validator: validateConfirmPassword, trigger: 'blur' }
        ]
      }
    }
  },
  created() {
    this.fetchIps()
    this.fetchWhitelistStatus()
    this.fetchThresholdSettings()
  },
  methods: {
    formatDate(dateString) {
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    async fetchWhitelistStatus() {
      try {
        const { data } = await axios.get(API_URLS.WHITELIST_STATUS, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (data.status === 'success') {
          this.whitelistEnabled = data.enabled
        }
      } catch (error) {
        console.error('获取白名单状态错误:', error)
        this.$message.error('获取白名单状态失败')
      }
    },
    async handleWhitelistChange(value) {
      try {
        const { data } = await axios.post(API_URLS.WHITELIST_STATUS, 
          { enabled: value },
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        )
        
        if (data.status === 'success') {
          this.$message.success(value ? '白名单已启用' : '白名单已禁用')
        } else {
          this.whitelistEnabled = !value  // 恢复之前的状态
          this.$message.error(data.message || '设置失败')
        }
      } catch (error) {
        console.error('更新白名单状态错误:', error)
        this.whitelistEnabled = !value  // 恢复之前的状态
        this.$message.error('设置失败')
      }
    },
    async fetchIps() {
      try {
        const { data } = await axios.get(API_URLS.IPS, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (data.status === 'success') {
          this.ips = data.ips
        }
      } catch (error) {
        console.error('获取IP列表错误:', error)
        this.$message.error('获取IP列表失败')
      }
    },
    showAddDialog() {
      this.dialogVisible = true
      this.newIp = { ip: '', description: '' }
    },
    async handleAdd() {
      try {
        const { data } = await axios.post(API_URLS.IPS, 
          this.newIp,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        )
        
        if (data.status === 'success') {
          this.$message.success('IP添加成功')
          this.dialogVisible = false
          this.fetchIps()
        } else {
          this.$message.error(data.message || 'IP添加失败')
        }
      } catch (error) {
        console.error('添加IP错误:', error)
        this.$message.error('IP添加失败')
      }
    },
    async handleDelete(row) {
      try {
        const { data } = await axios.delete(`${API_URLS.IPS}/${row.id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (data.status === 'success') {
          this.$message.success('IP删除成功')
          this.fetchIps()
        } else {
          this.$message.error(data.message || 'IP删除失败')
        }
      } catch (error) {
        console.error('删除IP错误:', error)
        this.$message.error('IP删除失败')
      }
    },
    handleLogout() {
      localStorage.removeItem('token')
      this.$router.push('/admin/login')
    },
    async fetchThresholdSettings() {
      try {
        const { data } = await axios.get(API_URLS.SETTINGS_THRESHOLD, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (data.status === 'success') {
          this.thresholdSettings = {
            white_threshold: data.white_threshold,
            black_threshold: data.black_threshold
          }
        }
      } catch (error) {
        console.error('获取阈值设置失败:', error)
        this.$message.error('获取阈值设置失败')
      }
    },
    async updateThresholdSettings() {
      try {
        const { data } = await axios.post(API_URLS.SETTINGS_THRESHOLD, 
          this.thresholdSettings,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        )
        
        if (data.status === 'success') {
          this.$message.success('设置更新成功')
        } else {
          this.$message.error(data.message || '设置更新失败')
        }
      } catch (error) {
        console.error('更新阈值设置失败:', error)
        this.$message.error('设置更新失败')
      }
    },
    showChangePassword() {
      this.passwordDialogVisible = true
      this.passwordForm = {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
    },
    async handleChangePassword() {
      if (!this.$refs.passwordFormRef) return
      
      try {
        await this.$refs.passwordFormRef.validate()
        this.passwordLoading = true
        
        const { data } = await axios.post(API_URLS.CHANGE_PASSWORD, 
          {
            oldPassword: this.passwordForm.oldPassword,
            newPassword: this.passwordForm.newPassword
          },
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        )
        
        if (data.status === 'success') {
          this.$message.success('密码修改成功')
          this.passwordDialogVisible = false
        } else {
          this.$message.error(data.message || '密码修改失败')
        }
      } catch (error) {
        console.error('修改密码错误:', error)
        this.$message.error(error.response?.data?.message || '密码修改失败')
      } finally {
        this.passwordLoading = false
      }
    }
  }
}
</script>

<style scoped>
.admin-container {
  padding: 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f6f8ff 0%, #f1f5ff 100%);
}

.admin-card {
  margin: 0 auto;
  max-width: 1200px;
  border-radius: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.whitelist-control {
  display: flex;
  align-items: center;
  margin-right: 20px;
}

.whitelist-label {
  margin-right: 10px;
  font-weight: 500;
  color: #606266;
}

.settings-card {
  margin-top: 20px;
}

.settings-form {
  max-width: 500px;
  margin: 0 auto;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
}
</style> 