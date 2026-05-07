<template>
  <div class="user-detail-page">
    <el-card>
      <template #header>
        <div class="header">
          <el-button @click="goBack" type="text">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h2>用户信息</h2>
        </div>
      </template>

      <div class="user-content">
        <!-- 头像和基本信息 -->
        <div class="user-header">
          <el-avatar :size="120" :src="avatarUrl" class="avatar">
            <template #default>
              <el-icon :size="60"><User /></el-icon>
            </template>
          </el-avatar>
          <div class="user-basic-info">
            <h2>{{ userInfo.username }}</h2>
            <el-tag :type="roleType">{{ roleText }}</el-tag>
            <div class="rating">
              <el-icon><TrophyBase /></el-icon>
              Rating: {{ userInfo.rating }}
            </div>
          </div>
        </div>

        <!-- 详细信息 -->
        <el-descriptions :column="2" border class="user-descriptions">
          <el-descriptions-item label="用户名">
            {{ userInfo.username }}
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            {{ userInfo.email }}
          </el-descriptions-item>
          <el-descriptions-item label="学校">
            {{ userInfo.school || '未设置' }}
          </el-descriptions-item>
          <el-descriptions-item label="Rating">
            {{ userInfo.rating }}
          </el-descriptions-item>
          <el-descriptions-item label="注册时间">
            {{ formatDate(userInfo.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag :type="roleType">{{ roleText }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 统计信息 -->
        <el-row :gutter="20" class="stats-row">
          <el-col :span="8">
            <el-card class="stat-card">
              <el-statistic title="提交数" :value="stats.submissionCount">
                <template #prefix>
                  <el-icon><Document /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="stat-card">
              <el-statistic title="通过题目" :value="stats.solvedCount">
                <template #prefix>
                  <el-icon><CircleCheck /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="stat-card">
              <el-statistic title="参赛次数" :value="stats.contestCount">
                <template #prefix>
                  <el-icon><Trophy /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
        </el-row>

        <!-- 操作按钮 (不是查看自己时显示) -->
        <div v-if="!isViewingSelf" class="action-buttons">
          <el-button 
            v-if="friendshipStatus === 'none'" 
            type="primary" 
            @click="sendFriendRequest"
            :loading="actionLoading"
          >
            <el-icon><UserFilled /></el-icon>
            添加好友
          </el-button>
          <el-button 
            v-if="friendshipStatus === 'pending_sent'" 
            type="info" 
            disabled
          >
            <el-icon><Clock /></el-icon>
            已发送请求
          </el-button>
          <el-button 
            v-if="friendshipStatus === 'pending_received'" 
            type="success" 
            @click="acceptFriendRequest"
            :loading="actionLoading"
          >
            <el-icon><Check /></el-icon>
            接受好友请求
          </el-button>
          <el-button 
            v-if="friendshipStatus === 'accepted'" 
            type="primary" 
            @click="sendPrivateMessage"
          >
            <el-icon><ChatDotRound /></el-icon>
            发送私信
          </el-button>
          <el-button 
            v-if="friendshipStatus === 'accepted'" 
            type="danger" 
            plain
            @click="deleteFriend"
            :loading="actionLoading"
          >
            <el-icon><Delete /></el-icon>
            删除好友
          </el-button>
          <el-button 
            v-if="friendshipStatus === 'blocked_by_me'" 
            type="warning" 
            @click="unblockUser"
            :loading="actionLoading"
          >
            <el-icon><Unlock /></el-icon>
            取消屏蔽
          </el-button>
          <el-button 
            v-else-if="friendshipStatus !== 'none' && friendshipStatus !== 'blocked_by_them'" 
            type="warning" 
            plain
            @click="blockUser"
            :loading="actionLoading"
          >
            <el-icon><Lock /></el-icon>
            屏蔽用户
          </el-button>
          <el-tag v-if="friendshipStatus === 'blocked_by_them'" type="danger">
            对方已屏蔽你
          </el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  User, ArrowLeft, TrophyBase, Document, CircleCheck, Trophy,
  UserFilled, Clock, Check, ChatDotRound, Delete, Lock, Unlock
} from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()

const userInfo = ref({
  username: '',
  email: '',
  school: '',
  rating: 0,
  created_at: '',
  role: 'user',
  avatar: ''
})

const stats = ref({
  submissionCount: 0,
  solvedCount: 0,
  contestCount: 0
})

const friendshipStatus = ref('none') // none, pending_sent, pending_received, accepted, blocked_by_me, blocked_by_them
const friendshipId = ref(null)
const actionLoading = ref(false)
const currentUserId = ref(null)

const isViewingSelf = computed(() => {
  return currentUserId.value && currentUserId.value === parseInt(route.params.id)
})

const avatarUrl = computed(() => {
  if (!userInfo.value.avatar) return ''
  if (userInfo.value.avatar.startsWith('http')) return userInfo.value.avatar
  return `${api.defaults.baseURL}${userInfo.value.avatar}`
})

const roleType = computed(() => {
  return userInfo.value.role === 'admin' ? 'danger' : 'primary'
})

const roleText = computed(() => {
  return userInfo.value.role === 'admin' ? '管理员' : '普通用户'
})

const loadUserInfo = async () => {
  try {
    const userId = route.params.id
    if (!userId) {
      ElMessage.error('用户ID无效')
      goBack()
      return
    }

    const response = await api.get(`/users/${userId}`)
    userInfo.value = response.data
  } catch (error) {
    console.error('加载用户信息失败:', error)
    ElMessage.error('加载用户信息失败')
  }
}

const loadStats = async () => {
  try {
    const userId = route.params.id
    if (!userId) return

    // 加载提交统计
    const submissionsRes = await api.get('/submissions', {
      params: { user_id: userId }
    })
    stats.value.submissionCount = submissionsRes.data.length

    // 统计通过的题目数
    const solvedProblems = new Set()
    submissionsRes.data.forEach(sub => {
      if (sub.status === 'accepted') {
        solvedProblems.add(sub.problem_id)
      }
    })
    stats.value.solvedCount = solvedProblems.size

    // 加载参赛统计
    const contestsRes = await api.get(`/contests/user/${userId}`)
    stats.value.contestCount = contestsRes.data.length
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const loadFriendshipStatus = async () => {
  try {
    const userId = route.params.id
    if (!userId || !currentUserId.value || isViewingSelf.value) return

    // 顺序请求避免并发认证问题
    // 注意：必须使用尾部斜杠，避免307重定向导致Authorization header丢失
    const friendsRes = await api.get('/friendships/')
    const requestsRes = await api.get('/friendships/requests')
    const sentRes = await api.get('/friendships/sent')
    const blockedRes = await api.get('/friendships/blocked')

    const targetUserId = parseInt(userId)

    // 检查是否是好友
    const friend = friendsRes.data.find(f => f.friend.user_id === targetUserId)
    if (friend) {
      friendshipStatus.value = 'accepted'
      friendshipId.value = friend.friendship_id
      return
    }

    // 检查是否收到对方的请求
    const request = requestsRes.data.find(r => r.user.user_id === targetUserId)
    if (request) {
      friendshipStatus.value = 'pending_received'
      friendshipId.value = request.friendship_id
      return
    }

    // 检查是否已发送请求
    const sent = sentRes.data.find(s => s.friend.user_id === targetUserId)
    if (sent) {
      friendshipStatus.value = 'pending_sent'
      friendshipId.value = sent.friendship_id
      return
    }

    // 检查是否屏蔽了对方
    const blocked = blockedRes.data.find(b => b.friend.user_id === targetUserId)
    if (blocked) {
      friendshipStatus.value = 'blocked_by_me'
      friendshipId.value = blocked.friendship_id
      return
    }

    // 检查对方是否屏蔽了自己（尝试发送请求时会返回错误）
    friendshipStatus.value = 'none'
    friendshipId.value = null
  } catch (error) {
    console.error('加载好友关系失败:', error)
  }
}

const sendFriendRequest = async () => {
  try {
    actionLoading.value = true
    await api.post('/friendships/', {
      friend_id: parseInt(route.params.id)
    })
    ElMessage.success('好友请求已发送')
    await loadFriendshipStatus()
  } catch (error) {
    console.error('发送好友请求失败:', error)
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('发送好友请求失败')
    }
  } finally {
    actionLoading.value = false
  }
}

const acceptFriendRequest = async () => {
  try {
    actionLoading.value = true
    await api.put(`/friendships/${friendshipId.value}/accept`)
    ElMessage.success('已接受好友请求')
    await loadFriendshipStatus()
  } catch (error) {
    console.error('接受好友请求失败:', error)
    ElMessage.error('接受好友请求失败')
  } finally {
    actionLoading.value = false
  }
}

const deleteFriend = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该好友吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    actionLoading.value = true
    await api.delete(`/friendships/${friendshipId.value}`)
    ElMessage.success('已删除好友')
    await loadFriendshipStatus()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除好友失败:', error)
      ElMessage.error('删除好友失败')
    }
  } finally {
    actionLoading.value = false
  }
}

const blockUser = async () => {
  try {
    await ElMessageBox.confirm('确定要屏蔽该用户吗？屏蔽后对方将无法向你发送消息和好友请求。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    actionLoading.value = true
    
    // 使用新的直接屏蔽API
    const userId = parseInt(route.params.id)
    const response = await api.post(`/friendships/block/${userId}`)
    
    // 更新friendshipId
    if (response.data.friendship_id) {
      friendshipId.value = response.data.friendship_id
    }
    
    ElMessage.success('已屏蔽该用户')
    await loadFriendshipStatus()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('屏蔽用户失败:', error)
      if (error.response?.data?.detail) {
        ElMessage.error(error.response.data.detail)
      } else {
        ElMessage.error('屏蔽用户失败')
      }
    }
  } finally {
    actionLoading.value = false
  }
}

const unblockUser = async () => {
  try {
    actionLoading.value = true
    const response = await api.put(`/friendships/${friendshipId.value}/unblock`)
    
    // 显示后端返回的消息
    if (response.data?.message) {
      ElMessage.success(response.data.message)
    } else {
      ElMessage.success('已取消屏蔽')
    }
    
    await loadFriendshipStatus()
  } catch (error) {
    console.error('取消屏蔽失败:', error)
    ElMessage.error('取消屏蔽失败')
  } finally {
    actionLoading.value = false
  }
}

const sendPrivateMessage = () => {
  // 跳转到消息页面，并通过 query 参数传递收件人 ID
  router.push({
    name: 'Messages',
    query: { recipientId: route.params.id }
  })
}

const goBack = () => {
  router.back()
}

// 监听路由参数变化，实时更新用户信息
watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    loadUserInfo()
    loadStats()
    loadFriendshipStatus()
  }
})

onMounted(async () => {
  // 先加载用户信息和统计（这些不需要登录）
  await Promise.all([
    loadUserInfo(),
    loadStats()
  ])
  
  // 检查是否已登录
  const token = localStorage.getItem('token')
  if (!token) {
    // 未登录，不显示社交功能
    return
  }
  
  // 获取当前登录用户ID（用于判断是否查看自己）
  try {
    const currentUserRes = await api.get('/users/me')
    currentUserId.value = currentUserRes.data.user_id
    
    // 只有在查看别人时才加载好友关系
    if (!isViewingSelf.value) {
      await loadFriendshipStatus()
    }
  } catch (error) {
    // 如果获取当前用户失败，不加载好友关系
    console.error('获取当前用户失败:', error)
  }
})
</script>

<style scoped>
.user-detail-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header h2 {
  margin: 0;
  flex: 1;
}

.user-content {
  padding: 20px 0;
}

.user-header {
  display: flex;
  align-items: center;
  gap: 30px;
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.avatar {
  border: 3px solid #409eff;
}

.user-basic-info {
  flex: 1;
}

.user-basic-info h2 {
  margin: 0 0 10px 0;
  font-size: 28px;
}

.user-basic-info .el-tag {
  margin-bottom: 10px;
}

.rating {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
}

.user-descriptions {
  margin-bottom: 30px;
}

.stats-row {
  margin-top: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card :deep(.el-statistic__head) {
  font-size: 16px;
  color: #606266;
}

.stat-card :deep(.el-statistic__content) {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.action-buttons {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.action-buttons .el-button {
  min-width: 120px;
}
</style>
