<template>
  <div class="messages-page">
    <el-card>
      <template #header>
        <div class="header">
          <h2>消息管理</h2>
          <el-button type="primary" @click="openNewMessageDialog">
            发送新私信
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 私信标签页 -->
        <el-tab-pane label="私信" name="private">
          <el-empty v-if="messages.length === 0" description="暂无私信" />

          <div v-else class="messages-list">
            <el-card 
              v-for="msg in messages" 
              :key="msg.message_id" 
              class="message-card"
              :class="{ 'sent-message': isSent(msg) }"
            >
              <template #header>
                <div class="message-header">
                  <div class="message-info">
                    <el-avatar 
                      :size="40" 
                      :src="getUserAvatar(msg)" 
                      class="user-avatar"
                      @click="goToUserProfile(msg)"
                      style="cursor: pointer;"
                    >
                      <el-icon><User /></el-icon>
                    </el-avatar>
                    <div class="message-info-text">
                      <div>
                        <el-tag v-if="isSent(msg)" type="success" size="small">发送</el-tag>
                        <el-tag v-else type="info" size="small">接收</el-tag>
                        <span class="message-title">{{ msg.title || '无标题' }}</span>
                      </div>
                      <div class="message-meta">
                        <span>{{ isSent(msg) ? '发送给' : '来自' }}: 
                          <el-link 
                            type="primary" 
                            :underline="false"
                            @click="goToUserProfile(msg)"
                          >
                            {{ getOtherUsers(msg) }}
                          </el-link>
                        </span>
                        <span>{{ formatDate(msg.created_at) }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="message-actions">
                    <el-button 
                      v-if="isSent(msg)"
                      type="primary" 
                      size="small" 
                      link
                      @click="handleEditMessage(msg)"
                    >
                      编辑
                    </el-button>
                    <el-button 
                      type="danger" 
                      size="small" 
                      link
                      @click="handleDeleteMessage(msg.message_id, 'private')"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </template>
              <div class="message-content">
                {{ msg.content }}
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 我的帖子标签页 -->
        <el-tab-pane label="我的帖子" name="topics">
          <el-empty v-if="myTopics.length === 0" description="暂无发表的帖子" />

          <div v-else class="messages-list">
            <el-card 
              v-for="topic in myTopics" 
              :key="topic.message_id" 
              class="message-card topic-card"
            >
              <template #header>
                <div class="message-header">
                  <div class="message-info">
                    <el-avatar 
                      :size="40" 
                      :src="getTopicAvatar(topic)" 
                      class="user-avatar"
                      @click="goToTopicUserProfile(topic)"
                      style="cursor: pointer;"
                    >
                      <el-icon><User /></el-icon>
                    </el-avatar>
                    <div class="message-info-text">
                      <div>
                        <el-tag type="warning" size="small">帖子</el-tag>
                        <span class="message-title">{{ topic.title || '无标题' }}</span>
                      </div>
                      <div class="message-meta">
                        <span>
                          作者: 
                          <el-link 
                            type="primary" 
                            :underline="false"
                            @click="goToTopicUserProfile(topic)"
                          >
                            {{ topic.creator?.username || '未知' }}
                          </el-link>
                        </span>
                        <span v-if="topic.problem">
                          题目: 
                          <el-link 
                            type="primary" 
                            :underline="false"
                            @click="goToProblemDiscussion(topic)"
                          >
                            {{ topic.problem.title }}
                          </el-link>
                        </span>
                        <span>{{ formatDate(topic.created_at) }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="message-actions">
                    <el-button 
                      type="primary" 
                      size="small" 
                      link
                      @click="handleEditMessage(topic)"
                    >
                      编辑
                    </el-button>
                    <el-button 
                      type="danger" 
                      size="small" 
                      link
                      @click="handleDeleteMessage(topic.message_id, 'topic')"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </template>
              <div class="message-content">
                {{ topic.content }}
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 发送新私信对话框 -->
    <el-dialog v-model="showNewMessageDialog" title="发送新私信" width="600px">
      <el-form :model="messageForm">
        <el-form-item label="接收者">
          <el-select 
            v-model="messageForm.recipient_ids" 
            multiple 
            filterable 
            remote
            reserve-keyword
            :remote-method="searchUsers"
            :loading="searchLoading"
            placeholder="输入用户名搜索"
            style="width: 100%"
          >
            <el-option
              v-for="user in searchUserList"
              :key="user.user_id"
              :label="`${user.username} (${user.school || '未设置学校'})`"
              :value="user.user_id"
            >
              <span style="float: left">{{ user.username }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                Rating: {{ user.rating }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="messageForm.title" placeholder="请输入标题（可选）" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="messageForm.content"
            type="textarea"
            :rows="8"
            placeholder="请输入私信内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewMessageDialog = false">取消</el-button>
        <el-button type="primary" @click="sendMessage">发送</el-button>
      </template>
    </el-dialog>

    <!-- 编辑消息对话框 -->
    <el-dialog v-model="showEditMessageDialog" title="编辑消息" width="600px">
      <el-form :model="editMessageForm">
        <el-form-item label="标题">
          <el-input
            v-model="editMessageForm.title"
            placeholder="请输入标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="editMessageForm.content"
            type="textarea"
            :rows="8"
            placeholder="请输入内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditMessageDialog = false">取消</el-button>
        <el-button type="primary" @click="updateMessage">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import api from '../api'
import { buildAvatarUrl, updateAvatarTimestampsForUsers } from '../utils/avatar'

const router = useRouter()
const route = useRoute()

const messages = ref([])
const myTopics = ref([])
const allUsers = ref([])
const searchUserList = ref([])
const searchLoading = ref(false)
const showNewMessageDialog = ref(false)
const showEditMessageDialog = ref(false)
const activeTab = ref('private')
const messageForm = ref({
  recipient_ids: [],
  title: '',
  content: ''
})
const editMessageForm = ref({
  message_id: null,
  title: '',
  content: ''
})

const currentUserId = computed(() => {
  const userId = localStorage.getItem('userId')
  return userId ? parseInt(userId) : null
})

onMounted(async () => {
  await loadMessages()
  await loadUsers()
  
  // 检查路由参数，如果有 recipientId，自动打开发送私信对话框
  if (route.query.recipientId) {
    const recipientId = parseInt(route.query.recipientId)
    if (recipientId && recipientId !== currentUserId.value) {
      // 等待用户列表加载完成后，打开对话框并预填收件人
      openNewMessageDialogWithRecipient(recipientId)
    }
    // 清除路由参数，避免重复触发
    router.replace({ name: 'Messages', query: {} })
  }
})

const handleTabChange = (tab) => {
  if (tab === 'topics') {
    loadMyTopics()
  } else if (tab === 'private') {
    loadMessages()
  }
}

// 刷新数据的函数（可以手动调用）
const refreshData = async () => {
  if (activeTab.value === 'private') {
    await loadMessages()
  } else if (activeTab.value === 'topics') {
    await loadMyTopics()
  }
  await loadUsers()

  // 更新 avatar 时间戳，迫使图片重新加载
  messages.value.forEach(m => {
    if (m.creator) updateAvatarTimestampsForUsers([m.creator])
    if (m.recipients) updateAvatarTimestampsForUsers(m.recipients)
  })
  myTopics.value.forEach(t => {
    if (t.creator) updateAvatarTimestampsForUsers([t.creator])
  })
  updateAvatarTimestampsForUsers(allUsers.value)
}

// 监听窗口获得焦点事件，自动刷新数据
if (typeof window !== 'undefined') {
  window.addEventListener('focus', () => { refreshData() })
}

const loadMessages = async () => {
  if (!currentUserId.value) {
    ElMessage.error('请先登录')
    return
  }

  try {
    const response = await api.get(`/messages/private?user_id=${currentUserId.value}`)
    messages.value = response.data
  } catch (error) {
    ElMessage.error('加载私信失败')
  }
}

const loadMyTopics = async () => {
  if (!currentUserId.value) {
    ElMessage.error('请先登录')
    return
  }

  try {
    const response = await api.get(`/messages/my-topics?user_id=${currentUserId.value}`)
    myTopics.value = response.data
  } catch (error) {
    ElMessage.error('加载帖子失败')
  }
}

const loadUsers = async () => {
  if (!currentUserId.value) {
    return
  }
  
  try {
    // 只加载好友列表（可以发送私信的用户）
    const response = await api.get(`/messages/available-recipients?user_id=${currentUserId.value}`)
    allUsers.value = response.data
    // 初始化搜索列表（显示所有好友）
    searchUserList.value = allUsers.value
  } catch (error) {
    console.error('加载好友列表失败:', error)
    ElMessage.error('加载好友列表失败')
  }
}

const searchUsers = async (query) => {
  if (!currentUserId.value) {
    return
  }
  
  searchLoading.value = true
  try {
    // 使用后端搜索接口
    const response = await api.get(`/messages/available-recipients?user_id=${currentUserId.value}&search=${encodeURIComponent(query || '')}`)
    searchUserList.value = response.data
  } catch (error) {
    console.error('搜索好友失败:', error)
  } finally {
    searchLoading.value = false
  }
}

const openNewMessageDialog = () => {
  // 初始化搜索列表（显示所有好友）
  searchUserList.value = allUsers.value
  // 重置表单
  messageForm.value = {
    recipient_ids: [],
    title: '',
    content: ''
  }
  showNewMessageDialog.value = true
}

// 新增：打开发送私信对话框并预填收件人
const openNewMessageDialogWithRecipient = (recipientId) => {
  // 初始化搜索列表（显示所有好友）
  searchUserList.value = allUsers.value
  // 预填收件人
  messageForm.value = {
    recipient_ids: [recipientId],
    title: '',
    content: ''
  }
  showNewMessageDialog.value = true
  ElMessage.success('请填写私信内容')
}

const getUserAvatar = (msg) => {
  const user = isSent(msg) ? msg.recipients?.[0] : msg.creator
  if (!user?.avatar) return ''
  return buildAvatarUrl(user.avatar, user.user_id)
}

const getTopicAvatar = (topic) => {
  const user = topic.creator
  if (!user?.avatar) return ''
  return buildAvatarUrl(user.avatar, user.user_id)
}

const goToUserProfile = (msg) => {
  const userId = isSent(msg) ? msg.recipients?.[0]?.user_id : msg.creator?.user_id
  if (userId) {
    router.push({ name: 'UserDetail', params: { id: userId } })
  }
}

const goToTopicUserProfile = (topic) => {
  if (topic.creator?.user_id) {
    router.push({ name: 'UserDetail', params: { id: topic.creator.user_id } })
  }
}

const goToProblemDiscussion = (topic) => {
  if (topic.problem?.problem_id) {
    // 跳转到题目详情页的讨论标签，并传递消息ID用于定位
    router.push({ 
      name: 'ProblemDetail', 
      params: { id: topic.problem.problem_id },
      query: { tab: 'discuss', messageId: topic.message_id }
    })
  }
}

const isSent = (msg) => {
  return msg.creator?.user_id === currentUserId.value
}

const getOtherUsers = (msg) => {
  if (isSent(msg)) {
    return msg.recipients?.map(r => r.username).join(', ') || '未知'
  } else {
    return msg.creator?.username || '未知'
  }
}

const sendMessage = async () => {
  if (!messageForm.value.content.trim()) {
    ElMessage.warning('请输入私信内容')
    return
  }

  if (messageForm.value.recipient_ids.length === 0) {
    ElMessage.warning('请选择至少一个接收者')
    return
  }

  try {
    await api.post(`/messages?creator_id=${currentUserId.value}`, {
      title: messageForm.value.title,
      content: messageForm.value.content,
      message_type: 'private',
      recipient_ids: messageForm.value.recipient_ids
    })
    ElMessage.success('发送成功')
    showNewMessageDialog.value = false
    messageForm.value = { recipient_ids: [], title: '', content: '' }
    loadMessages()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送失败')
  }
}

const handleEditMessage = (msg) => {
  editMessageForm.value = {
    message_id: msg.message_id,
    title: msg.title || '',
    content: msg.content || ''
  }
  showEditMessageDialog.value = true
}

const updateMessage = async () => {
  if (!editMessageForm.value.content.trim()) {
    ElMessage.warning('请输入内容')
    return
  }

  try {
    await api.put(`/messages/${editMessageForm.value.message_id}?user_id=${currentUserId.value}`, {
      title: editMessageForm.value.title,
      content: editMessageForm.value.content
    })
    ElMessage.success('更新成功')
    showEditMessageDialog.value = false
    editMessageForm.value = { message_id: null, title: '', content: '' }
    loadMessages()
    loadMyTopics()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  }
}

const handleDeleteMessage = async (messageId, type) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除这${type === 'private' ? '条私信' : '个帖子'}吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await api.delete(`/messages/${messageId}?user_id=${currentUserId.value}`)
    ElMessage.success('删除成功')
    
    if (type === 'private') {
      loadMessages()
    } else {
      loadMyTopics()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.messages-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  margin: 0;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-card {
  margin-bottom: 10px;
}

.sent-message {
  background: #f0f9ff;
}

.topic-card {
  background: #fffbf0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.message-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  cursor: pointer;
  transition: transform 0.2s;
}

.user-avatar:hover {
  transform: scale(1.1);
}

.message-info-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.message-title {
  font-weight: bold;
  font-size: 16px;
  margin-left: 5px;
}

.message-meta {
  display: flex;
  gap: 15px;
  font-size: 14px;
  color: #909399;
}

.message-actions {
  display: flex;
  gap: 10px;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
  padding: 10px 0;
}
</style>
