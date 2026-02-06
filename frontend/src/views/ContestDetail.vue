<template>
  <div class="contest-detail">
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <h2>{{ contest.title }}</h2>
              <el-tag v-if="contest.status === 'finished'" type="info" size="large">
                <el-icon><Clock /></el-icon>
                练习模式
              </el-tag>
              <el-tag v-if="isPassed" type="success" size="large">
                <el-icon><CircleCheck /></el-icon>
                已通过
              </el-tag>
            </div>
            <div>{{ contest.description }}</div>
          </div>
          <div v-if="contest.status !== 'finished'">
            <el-button v-if="!isRegistered" type="primary" @click="register">报名</el-button>
            <el-button v-else type="warning" @click="unregister">取消报名</el-button>
          </div>
          <div v-else>
            <el-tag type="info">比赛已结束，任何人可自由练习</el-tag>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" style="margin-top: 20px">
        <!-- 题目列表标签页 -->
        <el-tab-pane label="题目列表" name="problems">
          <el-row :gutter="20">
            <el-col :span="16">
              <!-- 无权限查看题目时的提示 -->
              <el-alert
                v-if="!canViewProblems"
                :title="getAccessMessage()"
                type="warning"
                :closable="false"
                style="margin-bottom: 20px"
              />
              
              <!-- 有权限时显示题目列表 -->
              <el-table v-if="canViewProblems" :data="contest.problems" style="width:100%">
                <el-table-column prop="problem_id" label="ID" width="80"/>
                <el-table-column prop="title" label="标题">
                  <template #default="{ row }">
                    <el-link @click="goToProblem(row.problem_id)" type="primary">
                      {{ row.title }}
                    </el-link>
                  </template>
                </el-table-column>
                <el-table-column prop="difficulty" label="难度" width="120"/>
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag v-if="problemPassStatus[row.problem_id]" type="success" size="small">
                      <el-icon><CircleCheck /></el-icon>
                      通过
                    </el-tag>
                    <span v-else style="color: #909399;">--</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{ row }">
                    <el-button size="small" @click="goToProblem(row.problem_id)">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-col>

            <el-col :span="8">
              <el-card>
                <h3>参赛用户 ({{ contest.participants.length }})</h3>
                <el-list>
                  <el-list-item v-for="p in contest.participants" :key="p.user_id">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                      <div>{{ p.username }} <small>({{ p.rating }})</small></div>
                    </div>
                  </el-list-item>
                </el-list>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 提交记录标签页 -->
        <el-tab-pane label="提交记录" name="submissions">
          <el-table :data="contestSubmissions" style="width: 100%" v-loading="submissionsLoading">
            <el-table-column prop="submission_id" label="ID" width="80" />
            <el-table-column prop="problem_id" label="题目ID" width="90">
              <template #default="{ row }">
                <el-link @click="goToProblem(row.problem_id)" type="primary">
                  #{{ row.problem_id }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="题目标题" min-width="180">
              <template #default="{ row }">
                <el-link @click="goToProblem(row.problem_id)" v-if="row.problem" type="primary">
                  {{ row.problem.title }}
                </el-link>
                <span v-else>未知题目</span>
              </template>
            </el-table-column>
            <el-table-column prop="language" label="语言" width="100" />
            <el-table-column prop="status" label="状态" width="150">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="exec_time" label="用时" width="100">
              <template #default="{ row }">
                {{ row.exec_time }}ms
              </template>
            </el-table-column>
            <el-table-column prop="exec_memory" label="内存" width="100">
              <template #default="{ row }">
                {{ formatMemory(row.exec_memory) }}
              </template>
            </el-table-column>
            <el-table-column prop="submitted_at" label="提交时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.submitted_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="contestSubmissions.length === 0 && !submissionsLoading" description="暂无提交记录" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Clock } from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()
const contestId = Number(route.params.id)

const contest = ref({ 
  title: '', 
  description: '', 
  start_time: null, 
  end_time: null, 
  problems: [], 
  participants: [],
  can_view_problems: false,
  is_registered: false,
  status: ''
})
const loading = ref(false)
const isRegistered = ref(false)
const canViewProblems = ref(false)
const problemPassStatus = ref({})
const activeTab = ref('problems')
const contestSubmissions = ref([])
const submissionsLoading = ref(false)

// 计算是否通过比赛（所有题目都通过）
const isPassed = computed(() => {
  if (contest.value.problems.length === 0) return false
  return contest.value.problems.every(p => problemPassStatus.value[p.problem_id])
})

// 获取访问提示信息
const getAccessMessage = () => {
  if (contest.value.status === 'upcoming') {
    return '比赛尚未开始，开始后可查看题目'
  }
  if (contest.value.status === 'finished') {
    return '比赛已结束，进入练习模式，所有用户可自由查看和提交'
  }
  if (!isRegistered.value) {
    return '请先报名参加比赛才能查看题目'
  }
  return '题目仅在比赛时间内对报名用户开放'
}

const loadContest = async () => {
  try {
    loading.value = true
    const userId = localStorage.getItem('userId')
    const params = userId ? { user_id: userId } : {}
    
    const res = await api.get(`/contests/${contestId}`, { params })
    contest.value = res.data

    // 从后端获取权限信息
    isRegistered.value = contest.value.is_registered || false
    canViewProblems.value = contest.value.can_view_problems || false
    
    // 只有能查看题目时才加载通过状态
    if (canViewProblems.value && contest.value.problems.length > 0) {
      await loadProblemPassStatus()
    }
  } catch (err) {
    ElMessage.error('加载比赛失败')
  } finally {
    loading.value = false
  }
}

const loadProblemPassStatus = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) return
  
  try {
    // 对每个题目检查是否有通过的提交
    for (const problem of contest.value.problems) {
      const response = await api.get(`/submissions?user_id=${userId}&problem_id=${problem.problem_id}&contest_id=${contestId}&status=Accepted&limit=1`)
      problemPassStatus.value[problem.problem_id] = response.data.length > 0
    }
  } catch (err) {
    console.error('加载题目通过状态失败', err)
  }
}

const register = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) { ElMessage.warning('请先登录'); return }
    await api.post(`/contests/${contestId}/register?user_id=${userId}`)
    ElMessage.success('报名成功')
    loadContest()
  } catch (err) { ElMessage.error(err.response?.data?.detail || '报名失败') }
}

const unregister = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) { ElMessage.warning('请先登录'); return }
    await api.delete(`/contests/${contestId}/register/${userId}`)
    ElMessage.success('取消报名成功')
    loadContest()
  } catch (err) { ElMessage.error(err.response?.data?.detail || '取消报名失败') }
}

const goToProblem = (id) => {
  // 携带 contest_id 参数以便题目页面知道这是比赛中的题目
  router.push(`/problems/${id}?contest_id=${contestId}`)
}

// 加载比赛提交记录
const loadContestSubmissions = async () => {
  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.warning('请先登录')
    return
  }

  try {
    submissionsLoading.value = true
    const response = await api.get('/submissions', {
      params: {
        user_id: userId,
        contest_id: contestId,
        limit: 100
      }
    })
    contestSubmissions.value = response.data
  } catch (error) {
    ElMessage.error('加载提交记录失败')
  } finally {
    submissionsLoading.value = false
  }
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

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return '--'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

// 格式化内存
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

// 监听标签页切换
watch(activeTab, (newTab) => {
  if (newTab === 'submissions' && contestSubmissions.value.length === 0) {
    loadContestSubmissions()
  }
})

onMounted(() => { 
  loadContest()
})
</script>

<style scoped>
.contest-detail { padding: 20px }
</style>
