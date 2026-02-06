<template>
  <div class="submissions">
    <el-card>
      <template #header>
        <h2>提交记录</h2>
      </template>

      <el-table :data="submissions" style="width: 100%" @sort-change="handleSortChange">
        <el-table-column prop="submission_id" label="ID" width="80" sortable="custom" />
        <el-table-column prop="problem_id" label="题目ID" width="90" sortable="custom">
          <template #default="{ row }">
            <el-link @click="goToProblem(row.problem_id)" type="primary">
              #{{ row.problem_id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="problem_title" label="题目标题" min-width="180" sortable="custom">
          <template #default="{ row }">
            <el-link @click="goToProblem(row.problem_id)" v-if="row.problem" type="primary">
              {{ row.problem.title }}
            </el-link>
            <span v-else>未知题目</span>
          </template>
        </el-table-column>
        <el-table-column prop="contest_id" label="来源" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.contest_id" type="warning" size="small">
              比赛 #{{ row.contest_id }}
            </el-tag>
            <el-tag v-else type="info" size="small">题库</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="language" label="语言" width="100" sortable="custom" />
        <el-table-column prop="status" label="状态" width="150" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exec_time" label="用时" width="100" sortable="custom">
          <template #default="{ row }">
            {{ row.exec_time }}ms
          </template>
        </el-table-column>
        <el-table-column prop="exec_memory" label="内存" width="100" sortable="custom">
          <template #default="{ row }">
            {{ formatMemory(row.exec_memory) }}
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" sortable="custom">
          <template #default="{ row }">
            {{ formatTime(row.submitted_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="text" size="small" @click="viewCode(row)">查看代码</el-button>
            <el-button type="text" size="small" @click="viewDetail(row)">详细结果</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 代码查看对话框 -->
    <el-dialog v-model="codeVisible" title="提交代码" width="60%">
      <CodeViewer :code="currentCode" :language="currentCodeLang" />
    </el-dialog>

    <!-- 详细结果对话框 -->
    <el-dialog v-model="detailVisible" title="评测详情" width="70%">
      <div v-if="submissionDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="提交ID">{{ submissionDetail.submission_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(submissionDetail.status)">
              {{ getStatusText(submissionDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="语言">{{ submissionDetail.language }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ submissionDetail.total_score }}</el-descriptions-item>
          <el-descriptions-item label="最大用时">{{ submissionDetail.exec_time }}ms</el-descriptions-item>
          <el-descriptions-item label="最大内存">{{ formatMemory(submissionDetail.exec_memory) }}</el-descriptions-item>
        </el-descriptions>

        <h3 style="margin-top: 20px;">测试点详情</h3>
        <el-table :data="submissionDetail.judge_results" border style="margin-top: 10px;">
          <el-table-column label="测试点" width="80">
            <template #default="{ $index }">
              #{{ $index + 1 }}
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
          <el-table-column label="得分" width="80">
            <template #default="{ row }">
              {{ row.score }}
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="输入" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.input || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="期望输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.expected_output || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="isAdmin" label="实际输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.actual_output || '-' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <div v-if="row.error_message" class="error-message">
                {{ truncate(row.error_message, 100) }}
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import CodeViewer from '@/components/CodeViewer.vue'

const router = useRouter()

const submissions = ref([])
const codeVisible = ref(false)
const currentCode = ref('')
const currentCodeLang = ref('')
const detailVisible = ref(false)
const submissionDetail = ref(null)
const sortField = ref('')
const sortOrder = ref('')
const userRole = ref(localStorage.getItem('userRole') || 'user')

// 是否为管理员
const isAdmin = computed(() => userRole.value === 'admin')

onMounted(() => {
  loadSubmissions()
})

const handleSortChange = ({ prop, order }) => {
  if (order) {
    sortField.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortField.value = ''
    sortOrder.value = ''
  }
  loadSubmissions()
}

const loadSubmissions = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (!userId) {
      ElMessage.warning('请先登录')
      return
    }
    const params = { user_id: userId }
    if (sortField.value) {
      params.sort_by = sortField.value
      params.sort_order = sortOrder.value
    }
    const response = await api.get('/submissions', { params })
    submissions.value = response.data
  } catch (error) {
    ElMessage.error('加载提交记录失败')
  }
}

const viewCode = async (submission) => {
  try {
    const response = await api.get(`/submissions/${submission.submission_id}`)
    currentCode.value = response.data.code
    // prefer language from row if available, else from response
    currentCodeLang.value = submission.language || response.data.language || ''
    codeVisible.value = true
  } catch (error) {
    ElMessage.error('获取代码失败')
  }
}

const viewDetail = async (submission) => {
  try {
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/submissions/${submission.submission_id}/detail`, {
      params: { user_id: userId }
    })
    submissionDetail.value = response.data
    detailVisible.value = true
  } catch (error) {
    ElMessage.error('获取详细结果失败')
  }
}

const truncate = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const getStatusType = (status) => {
  const types = {
    accepted: 'success',
    wrong_answer: 'danger',
    time_limit_exceeded: 'warning',
    runtime_error: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    accepted: '通过',
    wrong_answer: '答案错误',
    time_limit_exceeded: '超时',
    runtime_error: '运行错误',
    compile_error: '编译错误',
    memory_limit_exceeded: '内存超限',
    judging: '评测中',
    system_error: '系统错误'
  }
  return texts[status] || status
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
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

const goToProblem = (problemId) => {
  router.push(`/problems/${problemId}`)
}
</script>

<style scoped>
.submissions {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.code-block {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
}

.error-message {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #f56c6c;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
