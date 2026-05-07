<template>
  <div class="problems">
    <el-card>
      <template #header>
        <div class="header">
          <h2>题库</h2>
        </div>
      </template>

      <!-- 搜索和筛选器 -->
      <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center; flex-wrap: wrap;">
        <el-input
          v-model="searchText"
          placeholder="搜索题目标题"
          style="width: 250px"
          clearable
          @keyup.enter="loadProblems"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="difficultyFilter"
          placeholder="难度"
          style="width: 120px"
          clearable
          @change="loadProblems"
        >
          <el-option label="简单" value="easy" />
          <el-option label="中等" value="medium" />
          <el-option label="困难" value="hard" />
        </el-select>

        <el-select 
          v-model="tagsFilterArray" 
          placeholder="选择标签（可多选）" 
          style="width: auto; min-width: 250px; max-width: 500px;" 
          multiple
          @change="loadProblems"
        >
          <el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" />
        </el-select>

        <el-button type="primary" @click="loadProblems">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 题目列表 -->
      <el-table :data="problems" style="width: 100%" @sort-change="handleSortChange">
        <el-table-column prop="problem_id" label="ID" width="80" sortable="custom" />
        <el-table-column label="状态" width="80" align="center" sortable="custom" sort-by="is_solved">
          <template #default="{ row }">
            <el-icon v-if="row.is_solved" color="#67C23A" :size="20">
              <Check />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" sortable="custom">
          <template #default="{ row }">
            <el-link @click="goToDetail(row.problem_id)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag 
              :type="getDifficultyType(row.difficulty)" 
              style="cursor: pointer"
              @click="filterByDifficulty(row.difficulty)"
            >
              {{ getDifficultyText(row.difficulty) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="200">
          <template #default="{ row }">
            <span v-if="row.tags">
              <el-tag 
                v-for="rawTag in row.tags.split(',')" 
                :key="rawTag" 
                size="small" 
                :type="tagsFilterArray.includes(rawTag.trim()) ? 'primary' : 'info'"
                style="margin-right: 5px; cursor: pointer"
                @click.stop="filterByTag(rawTag.trim())"
              >
                {{ rawTag.trim() }}
              </el-tag>
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Search } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const problems = ref([])
const searchText = ref('')
const difficultyFilter = ref('')  // 新增难度筛选
const tagsFilterArray = ref([])  // 改为数组，支持多选
const sortField = ref('')
const sortOrder = ref('')
const allTags = ref([])

onMounted(() => {
  loadProblems()
  loadTags()
})

const loadProblems = async () => {
  try {
    const params = {}
    if (searchText.value) {
      params.search = searchText.value
    }
    // 添加难度筛选
    if (difficultyFilter.value) {
      params.difficulty = difficultyFilter.value
    }
    // 将标签数组转换为逗号分隔的字符串
    if (tagsFilterArray.value.length > 0) {
      params.tags = tagsFilterArray.value.join(',')
    }
    if (sortField.value) {
      params.sort_by = sortField.value
      params.sort_order = sortOrder.value
    }
    // 添加user_id以获取通过状态
    const userId = localStorage.getItem('userId')
    if (userId) {
      params.user_id = userId
    }
    const response = await api.get('/problems', { params })
    problems.value = response.data
  } catch (error) {
    ElMessage.error('加载题目失败')
  }
}

const resetFilters = () => {
  searchText.value = ''
  difficultyFilter.value = ''  // 清空难度筛选
  tagsFilterArray.value = []  // 清空标签数组
  sortField.value = ''
  sortOrder.value = ''
  loadProblems()
}

const handleSortChange = ({ prop, order }) => {
  if (order) {
    sortField.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortField.value = ''
    sortOrder.value = ''
  }
  loadProblems()
}

const loadTags = async () => {
  try {
    const response = await api.get('/problems')
    const tagsSet = new Set()
    response.data.forEach(problem => {
      if (problem.tags) {
        problem.tags.split(',').forEach(tag => {
          const trimmedTag = tag.trim()
          if (trimmedTag) {
            tagsSet.add(trimmedTag)
          }
        })
      }
    })
    allTags.value = Array.from(tagsSet).sort()
  } catch (error) {
    console.error('加载标签失败', error)
  }
}

const goToDetail = (id) => {
  router.push(`/problems/${id}`)
}

const getDifficultyType = (difficulty) => {
  const types = {
    easy: 'success',
    medium: 'warning',
    hard: 'danger'
  }
  return types[difficulty] || 'info'
}

const getDifficultyText = (difficulty) => {
  const texts = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return texts[difficulty] || difficulty
}

// 点击难度标签进行筛选
const filterByDifficulty = (difficulty) => {
  difficultyFilter.value = difficulty
  loadProblems()
  ElMessage.success(`已筛选难度：${getDifficultyText(difficulty)}`)
}

// 点击标签进行筛选
const filterByTag = (tag) => {
  // 如果标签已存在，不重复添加
  if (!tagsFilterArray.value.includes(tag)) {
    tagsFilterArray.value.push(tag)
    loadProblems()
    ElMessage.success(`已添加标签筛选：${tag}`)
  } else {
    ElMessage.info(`标签 ${tag} 已在筛选条件中`)
  }
}
</script>

<style scoped>
.problems {
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

.filter-form {
  margin-bottom: 20px;
}
</style>
