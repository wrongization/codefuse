<template>
  <div class="contests">
    <el-card>
      <template #header>
        <div class="header-content">
          <h2>比赛列表</h2>
        </div>
      </template>

      <!-- 筛选和搜索 -->
      <div class="filters">
        <el-input
          v-model="searchText"
          placeholder="搜索比赛标题"
          style="width: 300px"
          @keyup.enter="loadContests"
          clearable
          @clear="loadContests"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-button type="primary" @click="loadContests">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        
        <el-button @click="searchText = ''; sortField = ''; sortOrder = ''; loadContests()">重置</el-button>
      </div>

      <!-- 比赛列表 -->
      <el-table :data="contests" style="width: 100%; margin-top: 20px" v-loading="loading" @sort-change="handleSortChange">
        <el-table-column prop="contest_id" label="ID" width="80" sortable="custom" />
        <el-table-column prop="title" label="比赛标题" min-width="200" sortable="custom">
          <template #default="{ row }">
            <el-link @click="goToContest(row.contest_id)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'upcoming'" type="info">未开始</el-tag>
            <el-tag v-else-if="row.status === 'ongoing'" type="success">进行中</el-tag>
            <el-tag v-else type="warning">练习模式</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatTime(row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="problem_count" label="题目数" width="100" sortable="custom" />
        <el-table-column prop="participant_count" label="参赛人数" width="100" sortable="custom" />
        <el-table-column prop="is_registered" label="报名状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.is_registered" type="success">已报名</el-tag>
            <el-tag v-else type="info">未报名</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_passed" label="通过情况" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.is_passed" type="success">
              <el-icon><CircleCheck /></el-icon>
              已通过
            </el-tag>
            <el-tag v-else-if="row.problem_count > 0" type="info">未通过</el-tag>
            <span v-else style="color: #909399;">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewContest(row.contest_id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, CircleCheck } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const contests = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)

const searchText = ref('')
const sortField = ref('')
const sortOrder = ref('')

onMounted(() => {
  loadContests()
})

const handleSortChange = ({ prop, order }) => {
  if (order) {
    sortField.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortField.value = ''
    sortOrder.value = ''
  }
  loadContests()
}

const loadContests = async () => {
  try {
    loading.value = true
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (sortField.value) {
      params.sort_by = sortField.value
      params.sort_order = sortOrder.value
    }
    
    // 添加用户ID以获取通过情况和报名状态
    const userId = localStorage.getItem('userId')
    if (userId) params.user_id = userId
    
    const response = await api.get('/contests/', { params })
    contests.value = response.data
    // 如果后端没有按照我们请求的字段排序，前端再做一次本地排序以保证列排序行为一致
    if (sortField.value) {
      const dir = sortOrder.value === 'asc' ? 1 : -1
      contests.value.sort((a, b) => {
        const av = a[sortField.value] ?? ''
        const bv = b[sortField.value] ?? ''
        if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * dir
        if (av > bv) return 1 * dir
        if (av < bv) return -1 * dir
        return 0
      })
    }
  } catch (error) {
    ElMessage.error('加载比赛列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEditing.value = false
  contestForm.value = {
    contest_id: null,
    title: '',
    description: '',
    start_time: null,
    end_time: null
  }
  dialogVisible.value = true
}

const editContest = (contest) => {
  isEditing.value = true
  contestForm.value = {
    contest_id: contest.contest_id,
    title: contest.title,
    description: contest.description,
    start_time: new Date(contest.start_time),
    end_time: new Date(contest.end_time)
  }
  dialogVisible.value = true
}

const saveContest = async () => {
  try {
    const creatorId = localStorage.getItem('userId')
    if (!creatorId) {
      ElMessage.warning('请先登录')
      return
    }

    // 验证时间
    if (!contestForm.value.start_time || !contestForm.value.end_time) {
      ElMessage.warning('请填写开始时间和结束时间')
      return
    }

    const startTime = new Date(contestForm.value.start_time)
    const endTime = new Date(contestForm.value.end_time)
    
    if (startTime >= endTime) {
      ElMessage.warning('开始时间必须早于结束时间')
      return
    }

    const data = {
      title: contestForm.value.title,
      description: contestForm.value.description,
      start_time: contestForm.value.start_time,
      end_time: contestForm.value.end_time
    }

    if (isEditing.value) {
      await api.put(`/contests/${contestForm.value.contest_id}`, data)
      ElMessage.success('比赛更新成功')
    } else {
      await api.post(`/contests/?creator_id=${creatorId}`, data)
      ElMessage.success('比赛创建成功')
    }

    dialogVisible.value = false
    loadContests()
  } catch (error) {
    ElMessage.error(isEditing.value ? '更新比赛失败' : '创建比赛失败')
  }
}

const deleteContest = async (contestId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个比赛吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.delete(`/contests/${contestId}`)
    ElMessage.success('删除成功')
    loadContests()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewContest = (contestId) => {
  router.push(`/contests/${contestId}`)
}

const goToContest = (contestId) => {
  router.push(`/contests/${contestId}`)
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped>
.contests {
  padding: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
}

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
