<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <h2>个人信息</h2>
        </div>
      </template>

      <div class="profile-content">
        <!-- 头像区域 -->
        <div class="avatar-section">
          <el-avatar :size="120" :src="avatarUrl" class="avatar">
            <template #default>
              <el-icon :size="60"><User /></el-icon>
            </template>
          </el-avatar>
          <el-upload
            class="avatar-uploader"
            :action="uploadUrl"
            :headers="uploadHeaders"
            :show-file-list="false"
            :on-success="handleAvatarSuccess"
            :before-upload="beforeAvatarUpload"
          >
            <el-button type="primary" size="small" class="upload-btn">
              <el-icon><Upload /></el-icon>
              更换头像
            </el-button>
          </el-upload>
        </div>

        <!-- 信息表单 -->
        <el-form
          ref="profileFormRef"
          :model="userInfo"
          :rules="rules"
          label-width="100px"
          class="profile-form"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="userInfo.username"
              :disabled="!isEditing"
              placeholder="请输入用户名"
            />
          </el-form-item>

          <el-form-item label="用户ID">
            <el-input v-model="userInfo.user_id" :disabled="true" />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="userInfo.email"
              :disabled="!isEditing"
              placeholder="请输入邮箱"
            />
          </el-form-item>

          <el-form-item label="学校" prop="school">
            <el-input
              v-model="userInfo.school"
              :disabled="!isEditing"
              placeholder="请输入学校"
            />
          </el-form-item>

          <el-form-item label="评分">
            <el-input-number
              v-model="userInfo.rating"
              :disabled="true"
              :controls="false"
            />
            <span class="rating-tip">评分由系统根据提交记录自动计算</span>
          </el-form-item>

          <el-form-item label="角色">
            <el-tag :type="userInfo.role === 'admin' ? 'danger' : 'primary'">
              {{ userInfo.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </el-form-item>

          <el-form-item label="注册时间">
            <span>{{ formatDate(userInfo.created_at) }}</span>
          </el-form-item>

          <el-divider />

          <!-- 修改密码区域 -->
          <div v-if="isEditing">
            <h3>修改密码</h3>
            <el-form-item label="当前密码" prop="currentPassword">
              <el-input
                v-model="passwordForm.currentPassword"
                type="password"
                placeholder="请输入当前密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                placeholder="请输入新密码（留空则不修改）"
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
          </div>

          <el-form-item class="form-actions">
            <el-button v-if="!isEditing" type="primary" @click="startEdit">
              <el-icon><Edit /></el-icon>
              编辑信息
            </el-button>
            <template v-else>
              <el-button type="primary" @click="saveProfile" :loading="saving">
                <el-icon><Check /></el-icon>
                保存修改
              </el-button>
              <el-button @click="cancelEdit">
                <el-icon><Close /></el-icon>
                取消
              </el-button>
            </template>
          </el-form-item>
        </el-form>

        <!-- 统计信息 -->
        <el-divider />
        <div class="stats-section">
          <h3>统计信息</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="提交总数" :value="stats.totalSubmissions">
                <template #prefix>
                  <el-icon><DocumentCopy /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="通过题目" :value="stats.solvedProblems">
                <template #prefix>
                  <el-icon><Select /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="参与比赛" :value="stats.contestCount">
                <template #prefix>
                  <el-icon><Trophy /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Upload, Edit, Check, Close, DocumentCopy, Select, Trophy } from '@element-plus/icons-vue'
import api from '../api'
import { updateAvatarTimestamp } from '../utils/avatar'

const profileFormRef = ref(null)
const isEditing = ref(false)
const saving = ref(false)

const userInfo = reactive({
  user_id: null,
  username: '',
  email: '',
  school: '',
  rating: 0,
  role: 'user',
  created_at: '',
  avatar: ''
})

const originalUserInfo = reactive({})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const stats = reactive({
  totalSubmissions: 0,
  solvedProblems: 0,
  contestCount: 0
})

const uploadUrl = ref(`${api.defaults.baseURL}/users/avatar`)
const uploadHeaders = ref({
  'Authorization': `Bearer ${localStorage.getItem('token')}`
})

const avatarUrl = computed(() => {
  if (!userInfo.avatar) return ''
  if (userInfo.avatar.startsWith('http')) return userInfo.avatar
  return `${api.defaults.baseURL}${userInfo.avatar}`
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  school: [
    { max: 100, message: '学校名称不能超过 100 个字符', trigger: 'blur' }
  ],
  newPassword: [
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    {
      validator: (rule, value, callback) => {
        if (passwordForm.newPassword && value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 加载用户信息
const loadUserInfo = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) {
      ElMessage.error('请先登录')
      return
    }

    const response = await api.get(`/users/${userId}`)
    Object.assign(userInfo, response.data)
    Object.assign(originalUserInfo, response.data)
  } catch (error) {
    console.error('加载用户信息失败:', error)
    ElMessage.error('加载用户信息失败')
  }
}

// 加载统计信息（使用后端提供的汇总接口）
const loadStats = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) return

    const res = await api.get(`/users/${userId}/stats`)
    stats.totalSubmissions = res.data.totalSubmissions || 0
    stats.solvedProblems = res.data.solvedProblems || 0
    stats.contestCount = res.data.contestCount || 0
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 开始编辑
const startEdit = () => {
  isEditing.value = true
  Object.assign(originalUserInfo, userInfo)
}

// 取消编辑
const cancelEdit = () => {
  isEditing.value = false
  Object.assign(userInfo, originalUserInfo)
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  profileFormRef.value?.clearValidate()
}

// 保存修改
const saveProfile = async () => {
  try {
    // 验证表单
    await profileFormRef.value?.validate()

    saving.value = true

    // 准备更新数据
    const updateData = {
      username: userInfo.username,
      email: userInfo.email,
      school: userInfo.school
    }

    // 如果要修改密码
    if (passwordForm.newPassword) {
      if (!passwordForm.currentPassword) {
        ElMessage.error('请输入当前密码')
        saving.value = false
        return
      }
      updateData.current_password = passwordForm.currentPassword
      updateData.password = passwordForm.newPassword
    }

    // 发送更新请求
    await api.put(`/users/${userInfo.user_id}`, updateData)

    ElMessage.success('保存成功')
    isEditing.value = false
    
    // 如果修改了用户名，更新localStorage
    if (userInfo.username !== originalUserInfo.username) {
      localStorage.setItem('username', userInfo.username)
    }

    // 清空密码表单
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''

    // 重新加载用户信息
    await loadUserInfo()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// 处理头像上传成功
const handleAvatarSuccess = async (response) => {
  userInfo.avatar = response.avatar_url
  ElMessage.success('头像上传成功')
  // 更新头像时间戳以强制刷新
  updateAvatarTimestamp(userInfo.user_id)
  // 重新加载用户信息以确保数据同步
  await loadUserInfo()
}

// 上传前检查
const beforeAvatarUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadUserInfo()
  loadStats()
})
</script>

<style scoped>
.profile-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.profile-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
}

.profile-content {
  padding: 20px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 40px;
}

.avatar {
  margin-bottom: 15px;
  border: 3px solid #f0f0f0;
}

.upload-btn {
  margin-top: 10px;
}

.profile-form {
  max-width: 600px;
  margin: 0 auto;
}

.rating-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.form-actions {
  margin-top: 30px;
  text-align: center;
}

.form-actions .el-button {
  min-width: 120px;
}

.stats-section {
  margin-top: 20px;
}

.stats-section h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #303133;
}

:deep(.el-statistic) {
  text-align: center;
}

:deep(.el-statistic__head) {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

:deep(.el-statistic__content) {
  font-size: 28px;
  color: #409eff;
  font-weight: bold;
}
</style>
