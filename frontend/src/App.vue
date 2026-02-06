<template>
  <div id="app">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="logo">
          <h1>CodeFuse</h1>
        </div>
        <el-menu
          :default-active="activeMenu"
          mode="horizontal"
          @select="handleMenuSelect"
          class="nav-menu"
        >
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/problems">题库</el-menu-item>
          <el-menu-item index="/contests">比赛</el-menu-item>
          <el-menu-item index="/submissions">提交记录</el-menu-item>
          <el-menu-item index="/messages" v-if="isLoggedIn">
            <el-icon><ChatDotRound /></el-icon>
            <span>消息</span>
          </el-menu-item>
          <el-menu-item index="/friends" v-if="isLoggedIn">
            <el-icon><UserFilled /></el-icon>
            <span>好友</span>
          </el-menu-item>
          <el-menu-item index="/admin" v-if="isAdmin">
            <el-icon><Setting /></el-icon>
            <span>管理</span>
          </el-menu-item>
        </el-menu>
        <div class="user-info">
          <template v-if="isLoggedIn">
            <el-dropdown @command="handleUserCommand">
              <span class="user-dropdown">
                {{ username }}
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon>
                    个人信息
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button @click="showLogin">登录</el-button>
            <el-button type="primary" @click="showRegister">注册</el-button>
          </template>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main>
        <router-view></router-view>
      </el-main>
    </el-container>

    <!-- 登录对话框 -->
    <el-dialog v-model="loginVisible" title="登录" width="480px">
      <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" label-width="140px">
        <el-form-item label="用户名/邮箱" prop="username">
          <el-input v-model="loginForm.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            maxlength="50"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="loginVisible = false">取消</el-button>
        <el-button type="primary" @click="handleLogin">登录</el-button>
      </template>
    </el-dialog>

    <!-- 注册对话框 -->
    <el-dialog v-model="registerVisible" title="注册" width="480px">
      <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-width="140px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" maxlength="50" show-word-limit @blur="() => registerFormRef.value && registerFormRef.value.validateField('username')" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" type="email" @blur="() => registerFormRef.value && registerFormRef.value.validateField('email')" />
        </el-form-item>
        <el-form-item label="学校" prop="school">
          <el-input v-model="registerForm.school" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="registerForm.password" 
            type="password" 
            maxlength="50"
            show-word-limit
            show-password
          />
          <div style="color: #909399; font-size: 12px; margin-top: 4px;">
            密码长度为 6-50 个字符
          </div>
        </el-form-item>
        <el-form-item label="管理员码" prop="admin_code">
          <el-input 
            v-model="registerForm.admin_code" 
            type="password" 
            placeholder="普通用户无需填写"
            show-password
          />
          <div style="color: #909399; font-size: 12px; margin-top: 4px;">
            仅注册管理员时需要填写（可选）
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, User, SwitchButton, ArrowDown, ChatDotRound, UserFilled } from '@element-plus/icons-vue'
import api from './api'

const router = useRouter()
const route = useRoute()

const loginVisible = ref(false)
const registerVisible = ref(false)
const isLoggedIn = ref(false)
const username = ref('')
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = ref({
  username: '',
  password: ''
})

const registerForm = ref({
  username: '',
  email: '',
  school: '',
  password: '',
  admin_code: ''
})

// 登录表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名/邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 注册表单验证规则
const checkUsernameExists = async (username) => {
  if (!username) return false
  try {
    const res = await api.get('/users', { params: { search: username, limit: 5 } })
    return (res.data || []).some(u => u.username === username)
  } catch (e) {
    // 网络或后端错误时不阻止注册，后端会最终校验
    return false
  }
}

const checkEmailExists = async (email) => {
  if (!email) return false
  try {
    const res = await api.get('/users', { params: { search: email, limit: 5 } })
    return (res.data || []).some(u => u.email === email)
  } catch (e) {
    return false
  }
}

const validateUsername = async (rule, value, callback) => {
  if (!value) return callback(new Error('请输入用户名'))
  if (value.length < 2 || value.length > 50) return callback(new Error('用户名长度为 2-50 个字符'))
  const exists = await checkUsernameExists(value)
  if (exists) return callback(new Error('用户名已存在'))
  callback()
}

const validateEmail = async (rule, value, callback) => {
  if (!value) return callback(new Error('请输入邮箱'))
  // 简单邮箱格式验证由 element rule 的 type=email 处理，但我们也保留一层检查
  const exists = await checkEmailExists(value)
  if (exists) return callback(new Error('邮箱已被注册'))
  callback()
}

const registerRules = {
  username: [
    { validator: validateUsername, trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] },
    { validator: validateEmail, trigger: 'blur' }
  ],
  school: [
    { max: 100, message: '学校名称不能超过 100 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为 6-50 个字符', trigger: 'blur' }
  ]
}

const activeMenu = computed(() => route.path)

// 判断是否为管理员
const isAdmin = computed(() => {
  return isLoggedIn.value && localStorage.getItem('userRole') === 'admin'
})

onMounted(() => {
  // 检查登录状态
  const token = localStorage.getItem('token')
  const storedUsername = localStorage.getItem('username')
  if (token && storedUsername) {
    isLoggedIn.value = true
    username.value = storedUsername
  }
})

const handleMenuSelect = (index) => {
  router.push(index)
}

const handleUserCommand = (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    logout()
  }
}

const showLogin = () => {
  loginVisible.value = true
}

const showRegister = () => {
  registerVisible.value = true
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await api.post('/users/login', loginForm.value)
        // 保存用户信息
        localStorage.setItem('token', response.data.access_token)
        localStorage.setItem('username', response.data.username)
        localStorage.setItem('userId', response.data.user_id)
        localStorage.setItem('userRole', response.data.role)
        isLoggedIn.value = true
        username.value = response.data.username
        loginVisible.value = false
        // 根据角色显示不同的欢迎消息
        const roleText = response.data.role === 'admin' ? '管理员' : '用户'
        ElMessage.success(`欢迎${roleText}：${response.data.username}`)
        // 重置表单
        loginFormRef.value.resetFields()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '登录失败')
      }
    }
  })
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        await api.post('/users/register', registerForm.value)
        ElMessage.success('注册成功，请登录')
        registerVisible.value = false
        // 重置表单
        registerFormRef.value.resetFields()
        showLogin()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '注册失败')
      }
    }
  })
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('userId')
  localStorage.removeItem('userRole')
  isLoggedIn.value = false
  username.value = ''
  router.push('/')
  ElMessage.success('已退出登录')
}
</script>

<style scoped>
#app {
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #dcdfe6;
  padding: 0 20px;
}

.logo h1 {
  margin: 0;
  color: #409eff;
  font-size: 24px;
  margin-right: 40px;
}

.nav-menu {
  flex: 1;
  border-bottom: none;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0 12px;
  color: #606266;
  font-size: 14px;
}

.user-dropdown:hover {
  color: #409eff;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
