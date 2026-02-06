<template>
  <div class="friends-page">
    <el-card>
      <template #header>
        <div class="header">
          <h2>好友管理</h2>
          <el-button type="primary" @click="showAddFriendDialog = true">
            <el-icon><UserFilled /></el-icon>
            添加好友
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 我的好友标签页 -->
        <el-tab-pane label="我的好友" name="friends">
          <div v-if="friendsLoading" class="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-empty v-else-if="friends.length === 0" description="还没有好友" />
          <div v-else class="friends-list">
            <el-card v-for="item in friends" :key="item.friendship_id" class="friend-card">
              <div class="friend-info">
                <el-avatar 
                  :size="60" 
                  :src="getFriendAvatar(item.friend)" 
                  @click="goToUserProfile(item.friend.user_id)"
                  style="cursor: pointer;"
                >
                  <el-icon><User /></el-icon>
                </el-avatar>
                <div class="friend-details">
                  <h3>
                    <el-link 
                      type="primary" 
                      :underline="false"
                      @click="goToUserProfile(item.friend.user_id)"
                    >
                      {{ item.friend.username }}
                    </el-link>
                  </h3>
                  <p class="friend-meta">
                    <el-icon><Clock /></el-icon>
                    成为好友于 {{ formatDate(item.created_at) }}
                  </p>
                </div>
              </div>
              <div class="friend-actions">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="sendMessage(item.friend)"
                >
                  发送私信
                </el-button>
                <el-popconfirm
                  title="确定要删除这个好友吗？"
                  confirm-button-text="确定"
                  cancel-button-text="取消"
                  @confirm="deleteFriend(item.friendship_id)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" link>
                      删除好友
                    </el-button>
                  </template>
                </el-popconfirm>
                <el-popconfirm
                  title="确定要屏蔽这个用户吗？屏蔽后对方将无法向你发送消息"
                  confirm-button-text="确定"
                  cancel-button-text="取消"
                  @confirm="blockUser(item.friendship_id)"
                >
                  <template #reference>
                    <el-button type="warning" size="small" link>
                      屏蔽
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 好友请求标签页 -->
        <el-tab-pane name="requests">
          <template #label>
            <el-badge :value="pendingRequests.length" :hidden="pendingRequests.length === 0">
              好友请求
            </el-badge>
          </template>
          
          <div v-if="requestsLoading" class="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-empty v-else-if="pendingRequests.length === 0" description="暂无好友请求" />
          <div v-else class="requests-list">
            <el-card v-for="item in pendingRequests" :key="item.friendship_id" class="request-card">
              <div class="request-info">
                <el-avatar 
                  :size="60" 
                  :src="getUserAvatar(item.user)"
                  @click="goToUserProfile(item.user.user_id)"
                  style="cursor: pointer;"
                >
                  <el-icon><User /></el-icon>
                </el-avatar>
                <div class="request-details">
                  <h3>
                    <el-link 
                      type="primary" 
                      :underline="false"
                      @click="goToUserProfile(item.user.user_id)"
                    >
                      {{ item.user.username }}
                    </el-link>
                  </h3>
                  <p class="request-meta">
                    <el-icon><Clock /></el-icon>
                    {{ formatDate(item.created_at) }} 请求添加你为好友
                  </p>
                </div>
              </div>
              <div class="request-actions">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="acceptRequest(item.friendship_id)"
                >
                  接受
                </el-button>
                <el-button 
                  type="danger" 
                  size="small"
                  @click="rejectRequest(item.friendship_id)"
                >
                  拒绝
                </el-button>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 已发送标签页 -->
        <el-tab-pane label="已发送" name="sent">
          <div v-if="sentLoading" class="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-empty v-else-if="sentRequests.length === 0" description="暂无已发送的好友请求" />
          <div v-else class="sent-list">
            <el-card v-for="item in sentRequests" :key="item.friendship_id" class="sent-card">
              <div class="sent-info">
                <el-avatar 
                  :size="60" 
                  :src="getFriendAvatar(item.friend)"
                  @click="goToUserProfile(item.friend.user_id)"
                  style="cursor: pointer;"
                >
                  <el-icon><User /></el-icon>
                </el-avatar>
                <div class="sent-details">
                  <h3>
                    <el-link 
                      type="primary" 
                      :underline="false"
                      @click="goToUserProfile(item.friend.user_id)"
                    >
                      {{ item.friend.username }}
                    </el-link>
                  </h3>
                  <p class="sent-meta">
                    <el-icon><Clock /></el-icon>
                    {{ formatDate(item.created_at) }} 已发送请求，等待对方处理
                  </p>
                </div>
              </div>
              <div class="sent-actions">
                <el-popconfirm
                  title="确定要撤回好友请求吗？"
                  confirm-button-text="确定"
                  cancel-button-text="取消"
                  @confirm="deleteFriend(item.friendship_id)"
                >
                  <template #reference>
                    <el-button type="danger" size="small">
                      撤回请求
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 黑名单标签页 -->
        <el-tab-pane label="黑名单" name="blocked">
          <div v-if="blockedLoading" class="loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载中...
          </div>
          <el-empty v-else-if="blockedUsers.length === 0" description="黑名单为空" />
          <div v-else class="blocked-list">
            <el-card v-for="item in blockedUsers" :key="item.friendship_id" class="blocked-card">
              <div class="blocked-info">
                <el-avatar 
                  :size="60" 
                  :src="getFriendAvatar(item.friend)"
                >
                  <el-icon><User /></el-icon>
                </el-avatar>
                <div class="blocked-details">
                  <h3>{{ item.friend.username }}</h3>
                  <p class="blocked-meta">
                    <el-icon><Clock /></el-icon>
                    {{ formatDate(item.updated_at) }} 已屏蔽
                  </p>
                </div>
              </div>
              <div class="blocked-actions">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="unblockUser(item.friendship_id)"
                >
                  解除屏蔽
                </el-button>
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 添加好友对话框 -->
    <el-dialog v-model="showAddFriendDialog" title="添加好友" width="500px">
      <el-form :model="addFriendForm">
          <el-form-item label="搜索用户">
            <div style="display:flex; gap:8px; align-items:center;">
              <el-input
                ref="addFriendInputRef"
                v-model="addFriendQuery"
                placeholder="用户名/用户ID"
                clearable
                @keyup.enter="doSearch"
                style="flex: 1"
              />
              <el-button type="primary" @click="doSearch" :loading="searchLoading">搜索</el-button>
            </div>

            <el-select
              v-model="addFriendForm.friend_id"
              filterable
              placeholder="从搜索结果中选择要添加的用户"
              :disabled="searchUserList.length === 0"
              style="width: 100%; margin-top: 8px"
              @change="onAddFriendSelectChange"
            >
              <el-option
                v-for="user in searchUserList"
                :key="user.user_id"
                :label="`${user.username} (${user.school || '未设置学校'})`"
                :value="user.user_id"
              >
                <div style="display: flex; align-items: center; gap: 10px;">
                  <el-avatar :size="30" :src="getUserAvatar(user)">
                    <el-icon><User /></el-icon>
                  </el-avatar>
                  <span v-html="highlight(user.username, addFriendQuery)"></span>
                  <span style="color: #909399; font-size: 12px;">{{ user.school || '未设置学校' }}</span>
                </div>
              </el-option>
            </el-select>
            <div v-if="searchMessage" class="search-hint">{{ searchMessage }}</div>
          </el-form-item>
        </el-form>
      <template #footer>
        <el-button @click="showAddFriendDialog = false">取消</el-button>
        <el-button type="primary" @click="sendFriendRequest" :loading="adding">发送请求</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, UserFilled, Clock, Loading } from '@element-plus/icons-vue'
import api from '../api'
import { buildAvatarUrl, updateAvatarTimestampsForUsers } from '../utils/avatar'

const router = useRouter()
const route = useRoute()

// initialize activeTab from route.query.tab so refresh/back preserves sub-tab
const activeTab = ref(String(route.query.tab || 'friends'))
const friends = ref([])
const pendingRequests = ref([])
const sentRequests = ref([])
const blockedUsers = ref([])
const allUsers = ref([])
const searchUserList = ref([])

const friendsLoading = ref(false)
const requestsLoading = ref(false)
const sentLoading = ref(false)
const blockedLoading = ref(false)
const searchLoading = ref(false)
const adding = ref(false)

const showAddFriendDialog = ref(false)
const addFriendForm = ref({
  friend_id: null
})

// 搜索输入（仅在点击搜索或按回车时触发真正的请求）
const addFriendQuery = ref('')
const addFriendInputRef = ref(null)
// 在搜索区域显示的友好提示（例如 ID 未找到 / 无匹配）
const searchMessage = ref('')
// 记录上一次选择，用于实现重复选择取消（toggle）行为
const prevSelected = ref(null)

const currentUserId = localStorage.getItem('userId')

// 清理对话框时的状态
watch(showAddFriendDialog, (val) => {
  if (val) {
    // 打开对话框时自动聚焦输入
    nextTick(() => { addFriendInputRef.value && addFriendInputRef.value.focus && addFriendInputRef.value.focus() })
    // reset message/results
    searchMessage.value = ''
    searchUserList.value = []
  } else {
    // 关闭时清理状态
    addFriendQuery.value = ''
    searchUserList.value = []
    addFriendForm.value.friend_id = null
    prevSelected.value = null
    searchMessage.value = ''
  }
})

onMounted(() => {
  loadFriends()
})

// Ensure correct data loads for the initial activeTab (e.g., when loaded from route.query.tab)
onMounted(() => {
  if (activeTab.value) {
    handleTabChange(activeTab.value)
  }
})

const refreshData = async () => {
  // Do not preload full user list on refresh to avoid exposing users.
  friends.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
  pendingRequests.value.forEach(item => { if (item?.user) updateAvatarTimestampsForUsers([item.user]) })
  sentRequests.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
  blockedUsers.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
}

if (typeof window !== 'undefined') {
  window.addEventListener('focus', () => { refreshData() })
}

const handleTabChange = (tab) => {
  if (tab === 'requests') {
    loadPendingRequests()
  } else if (tab === 'sent') {
    loadSentRequests()
  } else if (tab === 'blocked') {
    loadBlockedUsers()
  } else if (tab === 'friends') {
    loadFriends()
  }
}

// Watch for programmatic changes to activeTab and load corresponding data
watch(activeTab, (tab) => {
  if (tab) handleTabChange(tab)
})

// when activeTab changes, sync to URL query param (replace to avoid stacking history)
watch(activeTab, (newTab) => {
  if (!newTab) return
  const q = { ...route.query, tab: String(newTab) }
  router.replace({ query: q }).catch(() => {})
})

// if route.query.tab changes (browser back/forward), sync it to activeTab
watch(() => route.query.tab, (newTab) => {
  if (newTab && String(newTab) !== activeTab.value) {
    activeTab.value = String(newTab)
  }
})

const loadFriends = async () => {
  friendsLoading.value = true
  try {
    const response = await api.get('/friendships/')
    friends.value = response.data
    // 更新头像时间戳
    friends.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
  } catch (error) {
    ElMessage.error('加载好友列表失败')
  } finally {
    friendsLoading.value = false
  }
}

const loadPendingRequests = async () => {
  requestsLoading.value = true
  try {
    const response = await api.get('/friendships/requests')
    pendingRequests.value = response.data
    pendingRequests.value.forEach(item => { if (item?.user) updateAvatarTimestampsForUsers([item.user]) })
  } catch (error) {
    ElMessage.error('加载好友请求失败')
  } finally {
    requestsLoading.value = false
  }
}

const loadSentRequests = async () => {
  sentLoading.value = true
  try {
    const response = await api.get('/friendships/sent')
    sentRequests.value = response.data
    sentRequests.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
  } catch (error) {
    ElMessage.error('加载已发送请求失败')
  } finally {
    sentLoading.value = false
  }
}

const loadBlockedUsers = async () => {
  blockedLoading.value = true
  try {
    const response = await api.get('/friendships/blocked')
    blockedUsers.value = response.data
    blockedUsers.value.forEach(item => { if (item?.friend) updateAvatarTimestampsForUsers([item.friend]) })
  } catch (error) {
    ElMessage.error('加载黑名单失败')
  } finally {
    blockedLoading.value = false
  }
}

// NOTE: we intentionally do not preload the full user list to avoid exposing all users.
// Searching for users is done via server-side search in `searchUsers`.

const searchUsers = async (query) => {
  // If query is empty, don't return any user suggestions to avoid listing users.
  if (!query || !query.trim()) {
    searchUserList.value = []
    searchMessage.value = ''
    return
  }

  searchLoading.value = true
  // clear previous message
  searchMessage.value = ''
  try {
    // If the query is an integer, try fetching by user id first (exact match)
    const idMatch = String(query).trim().match(/^\d+$/)
    if (idMatch) {
      try {
        const resp = await api.get(`/users/${idMatch[0]}`)
        // backend may return a single user object
        if (resp && resp.data) {
          searchUserList.value = [resp.data]
          searchMessage.value = ''
          return
        }
      } catch (e) {
        // 如果按 ID 未找到，设置下方友好提示并不再回退到模糊搜索
        searchMessage.value = `未找到用户 ID: ${idMatch[0]}`
        searchUserList.value = []
        return
      }
    }
    // 禁止通过邮箱搜索
    if (String(query).includes('@')) {
      searchMessage.value = '不支持通过邮箱搜索，请使用用户名或用户ID'
      searchUserList.value = []
      return
    }

    // Otherwise, perform server-side search by username (and optional school)
    const res = await api.get('/users', { params: { search: query, limit: 20 } })
    // Filter out current user just in case
    const filtered = (res.data || []).filter(u => String(u.user_id) !== String(currentUserId))
    searchUserList.value = filtered
    if (!filtered || filtered.length === 0) {
      searchMessage.value = '未找到匹配的用户'
    } else {
      searchMessage.value = ''
    }
  } catch (error) {
    console.error('searchUsers error', error)
    searchUserList.value = []
  } finally {
    searchLoading.value = false
  }
}

// 点击搜索或按回车时调用：使用与原来相同的 searchUsers 逻辑
const doSearch = async () => {
  const q = String(addFriendQuery.value || '').trim()
  // 禁止邮箱搜索
  if (q.includes('@')) {
    searchMessage.value = '不支持通过邮箱搜索，请使用用户名或用户ID'
    searchUserList.value = []
    return
  }
  await searchUsers(q)
}

// 选择切换：如果用户重复选择同一项则取消选择（toggle 行为）
const onAddFriendSelectChange = (val) => {
  if (prevSelected.value && String(prevSelected.value) === String(val)) {
    // toggle off
    addFriendForm.value.friend_id = null
    prevSelected.value = null
  } else {
    prevSelected.value = val
  }
}

// 高亮匹配函数：对匹配片段包裹 <span class="highlight">，并对输入进行简单转义以防 XSS
const escapeHtml = (str) => {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const highlight = (text, q) => {
  if (!q) return escapeHtml(text)
  try {
    const esc = String(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(esc, 'ig')
    return escapeHtml(text).replace(re, (m) => `<span class="highlight">${escapeHtml(m)}</span>`)
  } catch (e) {
    return escapeHtml(text)
  }
}

const sendFriendRequest = async () => {
  if (!addFriendForm.value.friend_id) {
    ElMessage.warning('请选择要添加的用户')
    return
  }

  adding.value = true
  try {
    await api.post('/friendships/', {
      friend_id: addFriendForm.value.friend_id
    })
    ElMessage.success('好友请求已发送')
    showAddFriendDialog.value = false
    addFriendForm.value.friend_id = null
    loadSentRequests()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送好友请求失败')
  } finally {
    adding.value = false
  }
}

const acceptRequest = async (friendshipId) => {
  try {
    await api.put(`/friendships/${friendshipId}/accept`)
    ElMessage.success('已接受好友请求')
    loadPendingRequests()
    loadFriends()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const rejectRequest = async (friendshipId) => {
  try {
    await api.put(`/friendships/${friendshipId}/reject`)
    ElMessage.success('已拒绝好友请求')
    loadPendingRequests()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const deleteFriend = async (friendshipId) => {
  try {
    await api.delete(`/friendships/${friendshipId}`)
    ElMessage.success('操作成功')
    loadFriends()
    loadSentRequests()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const blockUser = async (friendshipId) => {
  try {
    await api.put(`/friendships/${friendshipId}/block`)
    ElMessage.success('已屏蔽该用户')
    loadFriends()
    loadBlockedUsers()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const unblockUser = async (friendshipId) => {
  try {
    const response = await api.put(`/friendships/${friendshipId}/unblock`)
    
    // 显示后端返回的消息
    if (response.data?.message) {
      ElMessage.success(response.data.message)
    } else {
      ElMessage.success('已解除屏蔽')
    }
    
    // 重新加载黑名单
    loadBlockedUsers()
    
    // 如果恢复为好友关系，也重新加载好友列表
    if (response.data?.message?.includes('好友关系已恢复')) {
      loadFriends()
    }
  } catch (error) {
    console.error('取消屏蔽失败:', error)
    ElMessage.error('操作失败')
  }
}

const getUserAvatar = (user) => {
  if (!user?.avatar) return ''
  return buildAvatarUrl(user.avatar, user.user_id)
}

const getFriendAvatar = (friend) => {
  if (!friend?.avatar) return ''
  return buildAvatarUrl(friend.avatar, friend.user_id)
}

const goToUserProfile = (userId) => {
  if (userId) {
    router.push({ name: 'UserDetail', params: { id: userId } })
  }
}

const sendMessage = (friend) => {
  // 跳转到消息页面，并通过 query 参数传递收件人 ID
  router.push({ 
    name: 'Messages',
    query: { recipientId: friend.user_id }
  })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.friends-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  margin: 0;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #909399;
  font-size: 16px;
}

.loading .el-icon {
  font-size: 24px;
  margin-right: 8px;
}

.friends-list,
.requests-list,
.sent-list,
.blocked-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.friend-card,
.request-card,
.sent-card,
.blocked-card {
  transition: all 0.3s;
}

.friend-card:hover,
.request-card:hover,
.sent-card:hover,
.blocked-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.friend-info,
.request-info,
.sent-info,
.blocked-info {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.friend-details,
.request-details,
.sent-details,
.blocked-details {
  flex: 1;
}

.friend-details h3,
.request-details h3,
.sent-details h3,
.blocked-details h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
}

.friend-meta,
.request-meta,
.sent-meta,
.blocked-meta {
  margin: 0;
  color: #909399;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.friend-actions,
.request-actions,
.sent-actions,
.blocked-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

:deep(.el-badge__content) {
  background-color: #f56c6c;
}

.search-hint {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

.highlight {
  background-color: #fff2cc;
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
