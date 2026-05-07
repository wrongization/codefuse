<template>
  <div class="problem-detail">
    <el-card v-if="problem">
      <template #header>
        <div class="header">
          <div class="title-section">
            <h2>{{ problem.title }}</h2>
            <el-tag :type="getDifficultyType(problem.difficulty)">
              {{ getDifficultyText(problem.difficulty) }}
            </el-tag>
          </div>
          <div v-if="isAdmin" class="actions">
            <el-button type="primary" size="small" @click="goToAdminTestCases">
              快捷测试点管理
            </el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="题目描述" name="description">
          <div class="section">
            <h3>题目描述</h3>
            <div class="markdown-body" v-html="renderedDescription"></div>
          </div>
          <div class="section">
            <h3>输入格式</h3>
            <div class="markdown-body" v-html="renderedInputFormat"></div>
          </div>
          <div class="section">
            <h3>输出格式</h3>
            <div class="markdown-body" v-html="renderedOutputFormat"></div>
          </div>
          <div class="section">
            <h3>样例</h3>
            <el-row :gutter="20">
              <el-col :span="12">
                <h4>输入</h4>
                <pre>{{ problem.sample_input }}</pre>
              </el-col>
              <el-col :span="12">
                <h4>输出</h4>
                <pre>{{ problem.sample_output }}</pre>
              </el-col>
            </el-row>
          </div>
          <div class="section">
            <p>时间限制: {{ problem.time_limit }}ms</p>
            <p>内存限制: {{ problem.memory_limit / 1024}}MB / {{ problem.memory_limit }}KB</p>
          </div>
        </el-tab-pane>

        <el-tab-pane label="提交代码" name="submit">
          <el-form>
            <!-- 语言选择已合并在代码编辑工具栏 -->
            <el-form-item label="提交方式">
              <el-radio-group v-model="submitMethod">
                <el-radio label="code">直接输入</el-radio>
                <el-radio label="file">本地文件</el-radio>
              </el-radio-group>
            </el-form-item>
            <template v-if="submitMethod === 'code'">
              <div class="code-editor-actions">
                <div class="toolbar-row">
                  <el-select v-model="submitForm.language" size="small" style="width:140px">
                    <el-option label="C" value="c" />
                    <el-option label="C++" value="cpp" />
                    <el-option label="Python" value="python" />
                    <el-option label="Java" value="java" />
                  </el-select>
                </div>
                <div class="toolbar-row">
                  <el-button size="small" @click="previewingCode = !previewingCode">{{ previewingCode ? '关闭预览' : '预览高亮' }}</el-button>
                  <el-button size="small" @click="copySubmitCode">复制</el-button>
                  <el-button size="small" @click="clearSubmitCode">清空</el-button>
                  <el-button size="small" @click="toggleWordWrap">{{ wordWrap ? '换行: 开' : '换行: 关' }}</el-button>
                </div>
                <div class="toolbar-row info-row">编辑区为纯文本；预览会展示语法高亮。可切换换行、复制或清空。</div>
              </div>

              <!-- 将代码输入区放在选项下面（label-position="top" 使其占满宽度） -->
              <el-form-item label="代码" label-position="top">
                <div v-if="!previewingCode" class="code-editor-wrapper">
                  <div class="gutter" ref="gutterRef">
                    <div v-for="ln in lineNumbers" :key="ln" class="gutter-line">{{ ln }}</div>
                  </div>
                  <textarea ref="textareaRef" v-model="submitForm.code" class="code-textarea" rows="18" :placeholder="'请输入你的代码'" :style="{ whiteSpace: wordWrap ? 'pre-wrap' : 'pre' }"></textarea>
                </div>
                <div v-else>
                  <CodeViewer :code="submitForm.code" :language="submitForm.language" :showMeta="false" />
                </div>
              </el-form-item>
              <el-form-item label="同步到好友（可多选）">
                <el-select v-model="selectedSync" multiple placeholder="选择要同步提交的好友">
                  <el-option v-for="f in friendsList" :key="f.user_id" :label="f.username" :value="f.user_id" />
                </el-select>
                <div class="help-text" style="margin-top:6px; color:#888; font-size:12px">被选中的好友将收到与您完全相同的提交（前提：他们是您的好友且已报名比赛）</div>
              </el-form-item>
            </template>
            <el-form-item v-else label="选择文件">
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                accept=".c,.cpp,.py,.java"
              >
                <el-button type="primary">选择代码文件</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 .c, .cpp, .py, .java 文件
                  </div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSubmit" :loading="submitting" :disabled="submitting">
                {{ submitting ? '提交中...' : '提交' }}
              </el-button>
              <el-button @click="resetForm" :disabled="submitting">重置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="提交记录" name="submissions">
          <div class="submissions-section">
            <el-alert 
              v-if="contestId" 
              :title="`当前显示比赛 #${contestId} 中该题目的提交记录`" 
              type="info" 
              :closable="false"
              style="margin-bottom: 20px"
            />
            <el-alert 
              v-else 
              title="当前显示题库中该题目的提交记录" 
              type="info" 
              :closable="false"
              style="margin-bottom: 20px"
            />
            
            <el-table :data="problemSubmissions" style="width: 100%" v-loading="submissionsLoading">
              <el-table-column prop="submission_id" label="ID" width="80" />
              <el-table-column label="语言" width="100">
                <template #default="{ row }">
                  {{ row.language }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="150">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="用时" width="100">
                <template #default="{ row }">
                  {{ row.exec_time }}ms
                </template>
              </el-table-column>
              <el-table-column label="内存" width="100">
                <template #default="{ row }">
                  {{ formatMemory(row.exec_memory) }}
                </template>
              </el-table-column>
              <el-table-column label="提交时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.submitted_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button type="text" size="small" @click="viewSubmissionCode(row)">查看代码</el-button>
                  <el-button type="text" size="small" @click="viewSubmissionDetail(row)">详细结果</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="problemSubmissions.length === 0 && !submissionsLoading" description="暂无提交记录" />
          </div>
        </el-tab-pane>

        <!-- 讨论标签页：非比赛题目或比赛已结束时显示 -->
        <el-tab-pane v-if="!contestId || contestStatus === 'finished'" label="讨论" name="discuss">
          <div class="discuss-section">
            <el-alert
              v-if="contestId && contestStatus === 'finished'"
              title="练习模式：比赛已结束，讨论区开放"
              type="info"
              :closable="false"
              style="margin-bottom: 20px"
            />
            <el-button type="primary" @click="showNewDiscussDialog = true" style="margin-bottom: 20px">
              发表新讨论
            </el-button>
            
            <el-empty v-if="discussions.length === 0" description="暂无讨论" />
            
            <div v-else class="discussions-list">
              <el-card 
                v-for="msg in discussions" 
                :key="msg.message_id" 
                :id="`discussion-${msg.message_id}`"
                class="discussion-card"
              >
                <template #header>
                  <div class="discussion-header">
                    <div class="discussion-user-info">
                      <el-avatar 
                        :size="50" 
                        :src="getDiscussionAvatar(msg)" 
                        class="discussion-avatar"
                        @click="goToUserProfile(msg.creator?.user_id)"
                        style="cursor: pointer;"
                      >
                        <el-icon><User /></el-icon>
                      </el-avatar>
                      <div>
                        <h4>{{ msg.title || '无标题' }}</h4>
                        <div class="discussion-meta">
                          <el-link 
                            type="primary" 
                            :underline="false"
                            @click="goToUserProfile(msg.creator?.user_id)"
                          >
                            {{ msg.creator?.username }}
                          </el-link>
                          <span>{{ formatDate(msg.created_at) }}</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="msg.creator?.user_id === currentUserId" style="display: flex; gap: 10px;">
                      <el-button
                        type="primary"
                        size="small"
                        link
                        @click="handleEditDiscussion(msg)"
                      >
                        编辑
                      </el-button>
                      <el-button
                        type="danger"
                        size="small"
                        link
                        @click="handleDeleteDiscussion(msg.message_id)"
                      >
                        删除
                      </el-button>
                    </div>
                  </div>
                </template>
                <div
                  class="discussion-content markdown-body"
                  v-html="renderDiscussionContent(msg.content)"
                ></div>
              </el-card>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>



    <!-- 发表新讨论对话框 -->
    <el-dialog v-model="showNewDiscussDialog" title="发表新讨论" width="600px">
      <el-form :model="discussForm">
        <el-form-item label="标题">
          <el-input v-model="discussForm.title" placeholder="请输入讨论标题（可选）" />
        </el-form-item>
        <el-form-item label="内容">
          <MarkdownEditor
            v-model="discussForm.content"
            :rows="10"
            placeholder="请输入讨论内容（支持 Markdown 格式）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewDiscussDialog = false">取消</el-button>
        <el-button type="primary" @click="submitDiscussion">发表</el-button>
      </template>
    </el-dialog>

    

    <!-- 编辑讨论对话框 -->
    <el-dialog v-model="showEditDiscussDialog" title="编辑讨论" width="600px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input
            v-model="editDiscussForm.title"
            placeholder="请输入标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="内容">
          <MarkdownEditor
            v-model="editDiscussForm.content"
            :rows="10"
            placeholder="请输入讨论内容（支持 Markdown 格式）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDiscussDialog = false">取消</el-button>
        <el-button type="primary" @click="updateDiscussion">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看代码对话框 -->
    <el-dialog v-model="codeDialogVisible" title="提交代码" width="70%">
      <CodeViewer :code="currentSubmissionCode" :language="currentSubmissionCodeLang" />
    </el-dialog>

    <!-- 查看详细结果对话框 -->
    <el-dialog v-model="detailDialogVisible" title="评测详情" width="80%">
      <div v-if="currentSubmissionDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="提交ID">{{ currentSubmissionDetail.submission_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentSubmissionDetail.status)">
              {{ getStatusText(currentSubmissionDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="语言">{{ currentSubmissionDetail.language }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ currentSubmissionDetail.total_score }}</el-descriptions-item>
          <el-descriptions-item label="最大用时">{{ currentSubmissionDetail.exec_time }}ms</el-descriptions-item>
          <el-descriptions-item label="最大内存">{{ formatMemory(currentSubmissionDetail.exec_memory) }}</el-descriptions-item>
        </el-descriptions>

        <h3 style="margin-top: 20px;">测试点详情</h3>
        <el-table :data="currentSubmissionDetail.judge_results" border style="margin-top: 10px;">
          <el-table-column label="测试点" width="100">
            <template #default="{ row }">
              #{{ row.test_case_index + 1 }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="150">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="用时" width="100">
            <template #default="{ row }">
              {{ row.time_used || 0 }}ms
            </template>
          </el-table-column>
          <el-table-column label="内存" width="100">
            <template #default="{ row }">
              {{ formatMemory(row.memory_used) }}
            </template>
          </el-table-column>
          <el-table-column prop="score" label="得分" width="100" />
          <el-table-column v-if="isAdmin" label="输入" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 120px; overflow-y: auto; margin: 0;">{{ row.input || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="期望输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 120px; overflow-y: auto; margin: 0;">{{ row.expected_output || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="实际输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 120px; overflow-y: auto; margin: 0;">{{ row.actual_output || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <span style="color: #f56c6c;">{{ row.error_message || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import api from '../api'
import CodeViewer from '@/components/CodeViewer.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import { buildAvatarUrl, updateAvatarTimestampsForUsers } from '../utils/avatar'
import { renderMarkdown } from '../utils/markdown'

const route = useRoute()
const router = useRouter()
const problem = ref(null)
const renderedDescription = computed(() => renderMarkdown(problem.value?.description || ''))
const renderedInputFormat = computed(() => renderMarkdown(problem.value?.input_format || ''))
const renderedOutputFormat = computed(() => renderMarkdown(problem.value?.output_format || ''))
const renderDiscussionContent = (text) => renderMarkdown(text || '')
// initialize activeTab from route.query.tab so refresh/back preserves sub-tab
const activeTab = ref(String(route.query.tab || 'description'))
const submitMethod = ref('code')
const uploadRef = ref(null)
const selectedFile = ref(null)
const discussions = ref([])
const problemSubmissions = ref([])
const submissionsLoading = ref(false)
const submitting = ref(false)  // 提交中的加载状态
const showNewDiscussDialog = ref(false)
const showEditDiscussDialog = ref(false)
const codeDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentSubmissionCode = ref('')
const currentSubmissionCodeLang = ref('')
const currentSubmissionDetail = ref(null)
const previewingCode = ref(false)
const wordWrap = ref(true)
const gutterRef = ref(null)
const textareaRef = ref(null)
const discussForm = ref({
  title: '',
  content: ''
})
const editDiscussForm = ref({
  message_id: null,
  title: '',
  content: ''
})

// 获取 URL 中的 contest_id（如果是从比赛页面进入）
const contestId = computed(() => {
  const id = route.query.contest_id
  return id ? parseInt(id) : null
})

// 比赛状态（用于判断是否显示讨论区）
const contestStatus = ref(null)

const currentUser = computed(() => {
  const role = localStorage.getItem('role')
  const userId = localStorage.getItem('userId')
  return { role, userId: userId ? parseInt(userId) : null }
})

const currentUserId = computed(() => currentUser.value.userId)

// adminFlag: fallback server-side check in case localStorage role is not set correctly
import { ref as vueRef } from 'vue'
const adminFlag = vueRef(false)

const isAdmin = computed(() => adminFlag.value || currentUser.value.role === 'admin')
const isCreator = computed(() => problem.value && problem.value.creator_id === currentUser.value.userId)

const submitForm = ref({
  language: 'python',
  code: ''
})

// 好友列表与被选中的同步对象
const friendsList = ref([])
const selectedSync = ref([])

const lineNumbers = computed(() => {
  const code = submitForm.value.code || ''
  const lines = code.split('\n').length
  return Array.from({ length: Math.max(1, lines) }, (_, i) => i + 1)
})

const copySubmitCode = async () => {
  try {
    await navigator.clipboard.writeText(submitForm.value.code || '')
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

const clearSubmitCode = () => {
  submitForm.value.code = ''
}

const toggleWordWrap = () => {
  wordWrap.value = !wordWrap.value
}

const syncScroll = () => {
  if (gutterRef.value && textareaRef.value) {
    gutterRef.value.scrollTop = textareaRef.value.scrollTop
  }
}

// 管理测试点：跳转到 Admin 页面并打开题目对应的测试点管理面板
const goToAdminTestCases = () => {
  router.push({ name: 'Admin', query: { tab: 'problems', manage_problem_id: route.params.id } })
}

onMounted(async () => {
  try {
    // 如果是比赛题目，先检查访问权限
    if (contestId.value) {
      await checkContestAccess()
    }
    
    const response = await api.get(`/problems/${route.params.id}`)
    problem.value = response.data
    // 尝试从后端获取当前用户信息以确认管理员身份（兼容 localStorage 未设置 role 的情况）
    try {
      const me = await api.get('/users/me')
      if (me && me.data && me.data.role === 'admin') {
        adminFlag.value = true
      }
    } catch (e) {
      // ignore – 后端可能返回 401 或未登录
    }
    
    // 非比赛题目或比赛已结束的题目才加载讨论
    if (!contestId.value || contestStatus.value === 'finished') {
      await loadDiscussions()
    }
    // 加载好友列表（用于协作提交多选）
    loadFriends()
    
    // 检查URL中的 message_id 或 messageId 参数，若存在则切换到讨论并定位到对应帖子
    const messageIdFromQuery = route.query.message_id || route.query.messageId || route.query.messageId
    if (messageIdFromQuery) {
      activeTab.value = 'discuss'
      // 确保讨论已经加载，然后滚动到指定消息
      if (!discussions.value || discussions.value.length === 0) {
        await loadDiscussions()
      }
      // 等待 DOM 更新后滚动到指定消息
      await nextTick()
      setTimeout(() => {
        scrollToMessage(messageIdFromQuery)
      }, 150)
    }
    // 如果初始 activeTab 不是 description（比如 submissions），在首次加载时触发对应数据拉取
    if (activeTab.value === 'discuss') {
      // 已确保讨论加载
    } else if (activeTab.value === 'submissions') {
      if (problemSubmissions.value.length === 0) {
        await loadProblemSubmissions()
      }
    }
  } catch (error) {
    ElMessage.error('加载题目失败')
    router.push('/problems')
  }
})

// 将 activeTab 同步到 route.query.tab
watch(activeTab, (newTab) => {
  if (!newTab) return
  const q = { ...route.query, tab: String(newTab) }
  router.replace({ query: q }).catch(() => {})
})

// 如果路由 query 的 tab 发生变化（例如浏览器后退/前进），同步到 activeTab
watch(() => route.query.tab, (newTab) => {
  if (newTab && String(newTab) !== activeTab.value) {
    activeTab.value = String(newTab)
  }
})

const loadFriends = async () => {
  try {
    const res = await api.get('/friendships/')
    // /friendships/ 返回已接受的好友关系，friend 字段包含对方信息
    friendsList.value = res.data.map(f => ({
      user_id: f.friend?.user_id,
      username: f.friend?.username
    })).filter(x => x.user_id)
  } catch (e) {
    console.warn('加载好友列表失败', e)
    friendsList.value = []
  }
}

onMounted(() => {
  // attach scroll sync
  if (textareaRef.value) {
    textareaRef.value.addEventListener('scroll', syncScroll)
  }
})

onUnmounted(() => {
  if (textareaRef.value) {
    textareaRef.value.removeEventListener('scroll', syncScroll)
  }
  // 清理轮询/定时器
  stopAutoRefreshSubmissions()
  pollingHandle.value = null
})

// 刷新讨论数据的函数
const refreshDiscussions = async () => {
  if (problem.value && (!contestId.value || contestStatus.value === 'finished')) {
    await loadDiscussions()
  }

  // 更新讨论者头像时间戳
  discussions.value.forEach(d => {
    if (d.creator) updateAvatarTimestampsForUsers([d.creator])
  })
}

// 监听窗口获得焦点事件，自动刷新讨论
if (typeof window !== 'undefined') {
  window.addEventListener('focus', () => { refreshDiscussions() })
}

// 检查比赛访问权限
const checkContestAccess = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) {
      ElMessage.error('请先登录')
      router.push(`/contests/${contestId.value}`)
      return
    }
    
    const params = { user_id: userId }
    const response = await api.get(`/contests/${contestId.value}`, { params })
    
    // 保存比赛状态
    contestStatus.value = response.data.status
    
    if (!response.data.can_view_problems) {
      ElMessage.warning('您暂时无法访问比赛题目，请确保已报名且在比赛时间内')
      router.push(`/contests/${contestId.value}`)
    }
  } catch (error) {
    ElMessage.error('检查访问权限失败')
    router.push('/contests')
  }
}

// 监听activeTab变化
watch(activeTab, (newTab) => {
  if (newTab === 'discuss') {
    loadDiscussions()
  } else if (newTab === 'submissions' && problemSubmissions.value.length === 0) {
    loadProblemSubmissions()
  }
})
// 当用户切换到 submissions tab 时启动自动刷新（如果存在 judging）
watch(activeTab, (newTab) => {
  if (newTab === 'submissions') {
    // 先加载一次
    loadProblemSubmissions().then(() => {
      const judging = problemSubmissions.value.some(s => s && s.status === 'judging')
      if (judging) startAutoRefreshSubmissions()
    })
  } else {
    stopAutoRefreshSubmissions()
  }
})

// 监听 route.query 中的 message_id 或 messageId 参数，支持路由跳转后自动定位到对应讨论
watch(() => route.query.message_id || route.query.messageId, async (newVal) => {
  if (newVal) {
    activeTab.value = 'discuss'
    if (!discussions.value || discussions.value.length === 0) {
      await loadDiscussions()
    }
    await nextTick()
    setTimeout(() => {
      scrollToMessage(newVal)
    }, 150)
  }
})

const loadDiscussions = async () => {
  try {
    // guard: ensure problem id is available before requesting topic messages
    const pid = route.params.id
    if (!pid) {
      // avoid spurious requests when route params aren't ready (e.g., on focus/blur events)
      console.warn('loadDiscussions: route.params.id is undefined, skipping messages load')
      return
    }
    const response = await api.get(`/messages/topic/${pid}`)
    discussions.value = response.data
  } catch (error) {
    console.error('加载讨论失败:', error)
  }
}

// 加载题目提交记录
const loadProblemSubmissions = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.warning('请先登录')
    return
  }

  try {
    submissionsLoading.value = true
    const params = {
      user_id: userId,
      problem_id: route.params.id,
      limit: 100
    }
    
    // 根据是否在比赛中区分提交记录
    if (contestId.value) {
      // 比赛中的题目，只显示该比赛的提交
      params.contest_id = contestId.value
    } else {
      // 题库中的题目，只显示题库的提交（contest_id = -1）
      params.contest_id = -1
    }
    
    const response = await api.get('/submissions', { params })
    problemSubmissions.value = response.data
  } catch (error) {
    ElMessage.error('加载提交记录失败')
  } finally {
    submissionsLoading.value = false
  }
}

// 自动刷新控制：当有处于 judging 的提交时，定期刷新提交列表
const submissionsRefreshTimer = { id: null }

const startAutoRefreshSubmissions = (intervalMs = 2000) => {
  if (submissionsRefreshTimer.id) return
  submissionsRefreshTimer.id = setInterval(async () => {
    try {
      await loadProblemSubmissions()
      const stillJudging = problemSubmissions.value.some(s => s && s.status === 'judging')
      if (!stillJudging) {
        clearInterval(submissionsRefreshTimer.id)
        submissionsRefreshTimer.id = null
      }
    } catch (e) {
      console.warn('auto refresh submissions error', e)
    }
  }, intervalMs)
}

const stopAutoRefreshSubmissions = () => {
  if (submissionsRefreshTimer.id) {
    clearInterval(submissionsRefreshTimer.id)
    submissionsRefreshTimer.id = null
  }
}

// 查看提交代码
const viewSubmissionCode = async (submission) => {
  try {
    const response = await api.get(`/submissions/${submission.submission_id}`)
    currentSubmissionCode.value = response.data.code
    currentSubmissionCodeLang.value = submission.language || response.data.language || ''
    codeDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取代码失败')
  }
}

// 查看提交详细结果
const viewSubmissionDetail = async (submission) => {
  try {
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/submissions/${submission.submission_id}/detail`, {
      params: { user_id: userId }
    })
    currentSubmissionDetail.value = response.data
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详细结果失败')
  }
}

// (removed separate test-case I/O dialog; admins see I/O inline in the table)

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleFileRemove = () => {
  selectedFile.value = null
}

const resetForm = () => {
  submitForm.value.code = ''
  selectedFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const handleSubmit = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.error('请先登录')
    return
  }

  submitting.value = true  // 开始提交，显示加载状态
  
  try {
    if (submitMethod.value === 'code') {
      // 直接输入代码提交
      if (!submitForm.value.code.trim()) {
        ElMessage.warning('请输入代码')
        submitting.value = false
        return
      }

      const data = {
        problem_id: parseInt(route.params.id),
        code: submitForm.value.code,
        language: submitForm.value.language,
        contest_id: contestId.value || null  // 如果是比赛题目，添加 contest_id
        ,
        sync_with: selectedSync.value
      }
      
      await api.post(`/submissions?user_id=${userId}`, data)
      ElMessage.success('提交成功，正在评测中...')
      
      // 切换到提交记录标签页并刷新
      activeTab.value = 'submissions'
      problemSubmissions.value = []  // 清空以触发重新加载
      await loadProblemSubmissions()
      // 启动轮询，监测刚提交的评测状态并在完成后刷新列表
      startPollingRecentJudging()
    } else {
      // 文件上传提交
      if (!selectedFile.value) {
        ElMessage.warning('请选择代码文件')
        submitting.value = false
        return
      }

      const formData = new FormData()
      formData.append('file', selectedFile.value)
      formData.append('problem_id', route.params.id)
      formData.append('language', submitForm.value.language)
      formData.append('user_id', userId)
      
      // 如果是比赛题目，添加 contest_id
      if (contestId.value) {
        formData.append('contest_id', contestId.value)
      }
      // 添加 sync_with 字段（JSON 字符串）
      if (selectedSync.value && selectedSync.value.length > 0) {
        formData.append('sync_with', JSON.stringify(selectedSync.value))
      }

      await api.post('/submissions/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      ElMessage.success('提交成功，正在评测中...')
      
      // 切换到提交记录标签页并刷新
      activeTab.value = 'submissions'
      problemSubmissions.value = []  // 清空以触发重新加载
      await loadProblemSubmissions()
      // 启动轮询，监测刚提交的评测状态并在完成后刷新列表
      startPollingRecentJudging()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false  // 提交结束，隐藏加载状态
  }
}

// ------------------ 提交轮询辅助 ------------------
const pollingHandle = ref(null)

const pollSubmissionStatuses = async (ids, intervalMs = 2000, timeoutMs = 120000) => {
  const start = Date.now()
  const sleep = (ms) => new Promise(r => setTimeout(r, ms))
  try {
    while (Date.now() - start < timeoutMs) {
      const results = await Promise.all(ids.map(id => api.get(`/submissions/${id}`).then(r => r.data).catch(() => null)))
      // 更新本地列表中对应的提交
      let anyUpdated = false
      results.forEach(res => {
        if (!res) return
        const idx = problemSubmissions.value.findIndex(s => s.submission_id === res.submission_id)
        if (idx !== -1) {
          // 合并字段
          problemSubmissions.value[idx] = { ...problemSubmissions.value[idx], ...res }
          anyUpdated = true
        }
      })
      const stillJudging = results.filter(r => r && r.status === 'judging').length
      if (stillJudging === 0) return true
      await sleep(intervalMs)
    }
  } catch (e) {
    console.warn('pollSubmissionStatuses error', e)
  }
  return false
}

const startPollingRecentJudging = async () => {
  // 取出当前列表里最近的若干条处于 judging 状态的提交 id
  const ids = problemSubmissions.value
    .filter(s => s && String(s.user_id) === String(localStorage.getItem('userId')) && s.status === 'judging')
    .slice(0, 10)
    .map(s => s.submission_id)

  if (!ids || ids.length === 0) return

  // 防止重复启动
  if (pollingHandle.value) return
  pollingHandle.value = true
  const finished = await pollSubmissionStatuses(ids, 2000, 120000)
  pollingHandle.value = null
  if (finished) {
    // 最后确保完整刷新一次提交列表
    await loadProblemSubmissions()
  }
}

// 在组件卸载时停止任何轮询（通过置空标识）
onUnmounted(() => {
  pollingHandle.value = null
})

const submitDiscussion = async () => {
  if (!discussForm.value.content.trim()) {
    ElMessage.warning('请输入讨论内容')
    return
  }

  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.error('请先登录')
    return
  }

  try {
    await api.post(`/messages?creator_id=${userId}`, {
      title: discussForm.value.title,
      content: discussForm.value.content,
      message_type: 'topic',
      problem_id: parseInt(route.params.id)
    })
    ElMessage.success('发表成功')
    showNewDiscussDialog.value = false
    discussForm.value = { title: '', content: '' }
    loadDiscussions()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发表失败')
  }
}

const handleEditDiscussion = (msg) => {
  editDiscussForm.value = {
    message_id: msg.message_id,
    title: msg.title || '',
    content: msg.content || ''
  }
  showEditDiscussDialog.value = true
}

const updateDiscussion = async () => {
  if (!editDiscussForm.value.content.trim()) {
    ElMessage.warning('请输入讨论内容')
    return
  }

  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.error('请先登录')
    return
  }

  try {
    await api.put(`/messages/${editDiscussForm.value.message_id}?user_id=${userId}`, {
      title: editDiscussForm.value.title,
      content: editDiscussForm.value.content
    })
    ElMessage.success('更新成功')
    showEditDiscussDialog.value = false
    editDiscussForm.value = { message_id: null, title: '', content: '' }
    loadDiscussions()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  }
}

const handleDeleteDiscussion = async (messageId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个讨论吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const userId = localStorage.getItem('userId')
    await api.delete(`/messages/${messageId}?user_id=${userId}`)
    ElMessage.success('删除成功')
    loadDiscussions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const getDiscussionAvatar = (msg) => {
  if (!msg.creator?.avatar) return ''
  return buildAvatarUrl(msg.creator.avatar, msg.creator.user_id)
}

const goToUserProfile = (userId) => {
  if (userId) {
    router.push({ name: 'UserDetail', params: { id: userId } })
  }
}

const scrollToMessage = (messageId) => {
  const element = document.getElementById(`discussion-${messageId}`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    // 添加高亮效果
    element.style.transition = 'background-color 0.5s'
    element.style.backgroundColor = '#fff7e6'
    setTimeout(() => {
      element.style.backgroundColor = ''
    }, 2000)
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const formatTime = (timeStr) => {
  if (!timeStr) return '--'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

const formatMemory = (bytes) => {
  if (!bytes || bytes === 0) return '0KB'
  const kb = bytes / 1024
  if (kb < 1024) {
    return `${Math.round(kb)}KB`
  } else {
    const mb = kb / 1024
    return `${mb.toFixed(2)}MB`
  }
}

const getDifficultyType = (difficulty) => {
  const types = {
    easy: 'success',
    medium: 'warning',
    hard: 'danger'
  }
  return types[difficulty] || 'info'
}

// 状态类型映射
const getStatusType = (status) => {
  const statusMap = {
    'accepted': 'success',
    'Accepted': 'success',
    'wrong_answer': 'danger',
    'Wrong Answer': 'danger',
    'time_limit_exceeded': 'warning',
    'Time Limit Exceeded': 'warning',
    'memory_limit_exceeded': 'warning',
    'Memory Limit Exceeded': 'warning',
    'runtime_error': 'danger',
    'Runtime Error': 'danger',
    'compile_error': 'info',
    'Compile Error': 'info',
    'judging': 'info',
    'Judging': 'info',
    'system_error': 'danger',
    'System Error': 'danger'
  }
  return statusMap[status] || 'info'
}

// 状态文本映射
const getStatusText = (status) => {
  const statusMap = {
    'accepted': '通过',
    'Accepted': '通过',
    'wrong_answer': '答案错误',
    'Wrong Answer': '答案错误',
    'time_limit_exceeded': '超时',
    'Time Limit Exceeded': '超时',
    'memory_limit_exceeded': '内存超限',
    'Memory Limit Exceeded': '内存超限',
    'runtime_error': '运行错误',
    'Runtime Error': '运行错误',
    'compile_error': '编译错误',
    'Compile Error': '编译错误',
    'judging': '评测中',
    'Judging': '评测中',
    'system_error': '系统错误',
    'System Error': '系统错误'
  }
  return statusMap[status] || status
}

const getDifficultyText = (difficulty) => {
  const texts = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return texts[difficulty] || difficulty
}

const manageTestCases = () => {
  // legacy: 跳转到 Admin 的测试点管理
  router.push(`/problems/${route.params.id}/test-cases`)
}

// Quick manager is provided by Admin's test-case manager; we redirect to Admin with manage_problem_id when admin wants to manage test cases from problem detail.
</script>

<style scoped>
.problem-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-section h2 {
  margin: 0;
}

.actions {
  display: flex;
  gap: 10px;
}

.section {
  margin-bottom: 30px;
}

.section h3 {
  color: #409eff;
  margin-bottom: 10px;
}

.section pre {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
}

.discuss-section {
  padding: 20px;
}

.discussions-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.discussion-card {
  margin-bottom: 10px;
}

.discussion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.discussion-user-info {
  display: flex;
  gap: 15px;
  align-items: center;
}

.discussion-avatar {
  cursor: pointer;
  transition: transform 0.2s;
}

.discussion-avatar:hover {
  transform: scale(1.1);
}

.discussion-header h4 {
  margin: 0;
  font-size: 16px;
}

.discussion-meta {
  display: flex;
  gap: 15px;
  font-size: 14px;
  color: #909399;
}

.discussion-content {
  line-height: 1.6;
  white-space: normal;
  word-break: break-word;
}

.code-block {
  background-color: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', Consolas, monospace;
  line-height: 1.5;
  white-space: pre;
  margin: 0;
}

/* 代码编辑器样式（简易替代） */
.code-editor-wrapper {
  display: flex;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
.code-editor-wrapper .gutter {
  background: #fafafa;
  padding: 8px 10px;
  text-align: right;
  user-select: none;
  flex: 0 0 56px; /* fixed gutter width but allow layout shrink */
  border-right: 1px solid #eef0f2;
  box-sizing: border-box;
  overflow: hidden;
}
.gutter-line { font-size: 12px; color: #90a0ad; padding: 2px 6px; line-height: 1.45; }
.code-textarea {
  flex: 1 1 auto;
  min-width: 0; /* allow flexbox to shrink without forcing overflow */
  border: none;
  padding: 10px 12px;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.45;
  resize: vertical;
  min-height: 280px;
  outline: none;
  background: #fff;
  color: #2c3e50;
}
.code-textarea::-webkit-scrollbar { height: 10px; width: 10px }
.code-textarea:focus { box-shadow: inset 0 0 0 2px rgba(64,158,255,0.06); }

.code-editor-actions { margin-bottom: 8px; }

/* Responsive tweaks: stack editor vertically on small screens and prevent horizontal overflow on very wide screens */
@media (max-width: 900px) {
  .code-editor-wrapper {
    flex-direction: column;
  }
  .code-editor-wrapper .gutter {
    width: 100%;
    flex: 0 0 auto;
    text-align: left;
    border-right: none;
    border-bottom: 1px solid #eef0f2;
  }
  .gutter-line { display: inline-block; margin-right: 8px; }
  .code-textarea { min-height: 180px; }
}

/* toolbar: stack each control on its own line */
.code-editor-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.code-editor-actions .toolbar-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.code-editor-actions .info-row {
  color: #909399;
  font-size: 12px;
}

/* on very wide screens keep the editor filling the container (no artificial centering) */
.code-editor-wrapper { max-width: 100%; }

/* Make preview full width inside form item */
:deep(.el-dialog__body .code-viewer), .code-viewer {
  width: 100%;
}
.code-textarea:focus { box-shadow: inset 0 0 0 2px rgba(64,158,255,0.06); }
</style>
