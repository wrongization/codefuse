<template>
  <div class="test-case-manager">
    <div class="header">
      <h2>测试用例管理 - {{ problem?.title }}</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加测试用例
      </el-button>
    </div>

  <!-- 测试用例列表 -->
  <el-table :data="displayTestCases" style="width: 100%" border :row-class-name="tcRowClass">
      <el-table-column label="移动" width="60">
        <template #default="{ $index }">
          <div class="drag-cell" draggable="true" @dragstart="onDragStart($event, $index)" @dragover.prevent="onDragOver($event, $index)" @dragleave="onDragLeave($event, $index)" @drop="onDrop($event, $index)">
            <i class="drag-handle">☰</i>
          </div>
        </template>
      </el-table-column>
  <el-table-column prop="order" label="顺序" min-width="60" sortable />
      <el-table-column label="类型" min-width="120">
        <template #default="{ row }">
          <el-switch v-model="row.is_sample" :active-value="1" :inactive-value="0" />
        </template>
      </el-table-column>
      <el-table-column label="输入数据" min-width="200">
        <template #default="{ row }">
          <div class="code-preview">{{ truncate(row.input_data, 50) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="输出数据" min-width="200">
        <template #default="{ row }">
          <div class="code-preview">{{ truncate(row.output_data, 50) }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="分数" width="80" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="editTestCase(row)">
            编辑
          </el-button>
          <el-button type="danger" size="small" @click="deleteTestCase(row.test_case_id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑测试用例' : '添加测试用例'"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="顺序" prop="order">
          <el-input-number v-model="form.order" :min="0" />
        </el-form-item>
        
        <el-form-item label="类型" prop="is_sample">
          <el-radio-group v-model="form.is_sample">
            <el-radio :label="1">样例（对用户可见）</el-radio>
            <el-radio :label="0">隐藏（仅评测时使用）</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="分数" prop="score">
          <el-input-number v-model="form.score" :min="0" :max="100" />
        </el-form-item>
        
        <el-form-item label="输入数据" prop="input_data">
          <el-input
            v-model="form.input_data"
            type="textarea"
            :rows="8"
            placeholder="请输入测试输入数据"
            style="font-family: 'Courier New', monospace;"
          />
        </el-form-item>
        
        <el-form-item label="输出数据" prop="output_data">
          <el-input
            v-model="form.output_data"
            type="textarea"
            :rows="8"
            placeholder="请输入期望的输出数据"
            style="font-family: 'Courier New', monospace;"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="batchDialogVisible" title="批量导入测试用例" width="800px">
      <el-alert
        title="格式说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        每个测试用例占两行：第一行是输入，第二行是输出。使用 "---" 分隔不同的测试用例。
      </el-alert>
      <el-input
        v-model="batchContent"
        type="textarea"
        :rows="20"
        placeholder="示例：&#10;输入1&#10;输出1&#10;---&#10;输入2&#10;输出2"
        style="font-family: 'Courier New', monospace;"
      />
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="batchImport">导入</el-button>
      </template>
    </el-dialog>

    <div class="footer-actions">
      <el-button @click="showBatchDialog">批量导入</el-button>
      <el-button @click="$router.back()">返回</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/api'

const route = useRoute()
const problemId = parseInt(route.params.id)

const problem = ref(null)
const testCases = ref([])
const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const batchContent = ref('')
const editingId = ref(null)
const formRef = ref(null)

const form = ref({
  order: 0,
  is_sample: 0,
  score: 10,
  input_data: '',
  output_data: ''
})

// drag helpers: use a display array with placeholder for smooth insertion indicator
const dragOverIndex = ref(null)
const dragOverPosition = ref(null)
const currentDragIndex = ref(null) // real index in testCases

const displayTestCases = computed(() => {
  const arr = testCases.value.slice()
  if (dragOverIndex.value === null || dragOverPosition.value === null) return arr
  const displayInsert = dragOverIndex.value + (dragOverPosition.value === 'after' ? 1 : 0)
  const placeholder = { __placeholder: true }
  const newArr = arr.slice(0)
  newArr.splice(displayInsert, 0, placeholder)
  return newArr
})

const displayIndexToReal = (displayIndex) => {
  const display = displayTestCases.value
  if (!display || displayIndex < 0 || displayIndex >= display.length) return null
  if (display[displayIndex].__placeholder) return null
  let count = 0
  for (let i = 0; i <= displayIndex; i++) if (!display[i].__placeholder) count++
  return count - 1
}

const displayInsertToRealInsert = (displayInsert) => {
  const display = displayTestCases.value
  let count = 0
  for (let i = 0; i < displayInsert && i < display.length; i++) if (!display[i].__placeholder) count++
  return count
}

const onDragStart = (event, displayIndex) => {
  const real = displayIndexToReal(displayIndex)
  if (real === null) return
  currentDragIndex.value = real
  try { event.dataTransfer.effectAllowed = 'move' } catch (e) {}
}
const onDragOver = (event, displayIndex) => {
  let rowEl = null
  try { rowEl = event.currentTarget && event.currentTarget.closest ? event.currentTarget.closest('tr') : null } catch (e) { rowEl = null }
  const rect = rowEl ? rowEl.getBoundingClientRect() : null
  const clientY = event.clientY || 0
  if (rect) {
    const middle = rect.top + rect.height / 2
    dragOverPosition.value = clientY < middle ? 'before' : 'after'
    dragOverIndex.value = displayIndex
  } else {
    dragOverIndex.value = displayIndex
    dragOverPosition.value = 'after'
  }
}
const onDragLeave = (event, index) => {
  dragOverIndex.value = null
  dragOverPosition.value = null
}
const onDrop = (event, displayIndex) => {
  if (currentDragIndex.value === null || currentDragIndex.value === undefined) return
  const displayInsert = dragOverIndex.value !== null && dragOverPosition.value !== null ?
    (dragOverIndex.value + (dragOverPosition.value === 'after' ? 1 : 0)) : (displayIndex + 1)
  const insertIndex = Math.max(0, Math.min(displayInsertToRealInsert(displayInsert), testCases.value.length))
  const from = currentDragIndex.value
  const item = testCases.value.splice(from, 1)[0]
  let finalInsert = insertIndex
  if (from < insertIndex) finalInsert = insertIndex - 1
  finalInsert = Math.max(0, Math.min(finalInsert, testCases.value.length))
  testCases.value.splice(finalInsert, 0, item)
  testCases.value.forEach((tc, idx) => tc.order = idx)
  currentDragIndex.value = null
  dragOverIndex.value = null
  dragOverPosition.value = null
}

const tcRowClass = (row, rowIndex) => {
  const classes = []
  if (!row.__placeholder) {
    const real = testCases.value.indexOf(row)
    if (real === currentDragIndex.value) classes.push('dragging-row')
  }
  if (dragOverIndex.value !== null && dragOverPosition.value !== null && rowIndex === dragOverIndex.value) {
    classes.push(dragOverPosition.value === 'before' ? 'drag-over-before' : 'drag-over-after')
  }
  return classes.join(' ')
}

const rules = {
  input_data: [{ required: true, message: '请输入测试输入数据', trigger: 'blur' }],
  output_data: [{ required: true, message: '请输入期望输出数据', trigger: 'blur' }],
  score: [{ required: true, message: '请输入分数', trigger: 'blur' }]
}

// 加载题目信息
const loadProblem = async () => {
  try {
    const response = await api.get(`/problems/${problemId}`)
    problem.value = response.data
  } catch (error) {
    ElMessage.error('加载题目信息失败')
  }
}

// 加载测试用例
const loadTestCases = async () => {
  try {
    const response = await api.get(`/test-cases/problem/${problemId}`, {
      params: { include_hidden: true }
    })
    testCases.value = response.data
  } catch (error) {
    ElMessage.error('加载测试用例失败')
  }
}

// 显示添加对话框
const showAddDialog = () => {
  editingId.value = null
  form.value = {
    order: testCases.value.length,
    is_sample: 0,
    score: 10,
    input_data: '',
    output_data: ''
  }
  dialogVisible.value = true
}

// 编辑测试用例
const editTestCase = (testCase) => {
  editingId.value = testCase.test_case_id
  form.value = {
    order: testCase.order,
    is_sample: testCase.is_sample,
    score: testCase.score,
    input_data: testCase.input_data,
    output_data: testCase.output_data
  }
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  try {
    await formRef.value.validate()
    
    const data = {
      ...form.value,
      problem_id: problemId
    }
    // 计算操作后总分，要求严格等于100
    const currentTotal = testCases.value.reduce((s, t) => s + (Number(t.score) || 0), 0)
    let newTotal = currentTotal
    if (editingId.value) {
      // 编辑：减去旧项得分，加上新分
      const idx = testCases.value.findIndex(t => t.test_case_id === editingId.value)
      const oldScore = idx >= 0 ? Number(testCases.value[idx].score || 0) : 0
      newTotal = currentTotal - oldScore + Number(data.score || 0)
    } else {
      // 新增：加上新分
      newTotal = currentTotal + Number(data.score || 0)
    }

    if (newTotal !== 100) {
      ElMessage.error('操作后测试点总分必须等于100分（当前将为：' + newTotal + '）')
      return
    }

    if (editingId.value) {
      // 编辑
      await api.put(`/test-cases/${editingId.value}`, data)
      ElMessage.success('更新成功')
    } else {
      // 添加
      await api.post('/test-cases/', data)
      ElMessage.success('添加成功')
    }
    
    dialogVisible.value = false
    loadTestCases()
  } catch (error) {
    if (error.name !== 'ValidationError') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 删除测试用例
const deleteTestCase = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个测试用例吗？', '警告', {
      type: 'warning'
    })
    // 删除前计算删除后总分，要求严格等于100
    const idx = testCases.value.findIndex(t => t.test_case_id === id)
    const removedScore = idx >= 0 ? Number(testCases.value[idx].score || 0) : 0
    const currentTotal = testCases.value.reduce((s, t) => s + (Number(t.score) || 0), 0)
    const newTotal = currentTotal - removedScore
    if (newTotal !== 100) {
      ElMessage.error('删除会导致题目总分不等于100（删除后：' + newTotal + '），请先调整其他测试点分数后再删除')
      return
    }

    await api.delete(`/test-cases/${id}`)
    ElMessage.success('删除成功')
    loadTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 显示批量导入对话框
const showBatchDialog = () => {
  batchContent.value = ''
  batchDialogVisible.value = true
}

// 批量导入
const batchImport = async () => {
  try {
    const sections = batchContent.value.split('---').filter(s => s.trim())
    const testCasesToCreate = []
    
    for (let i = 0; i < sections.length; i++) {
      const lines = sections[i].trim().split('\n')
      if (lines.length < 2) {
        ElMessage.error(`第 ${i + 1} 个测试用例格式错误`)
        return
      }
      
      testCasesToCreate.push({
        problem_id: problemId,
        input_data: lines[0],
        output_data: lines[1],
        score: 10,
        is_sample: 0,
        order: testCases.value.length + i
      })
    }
    
    await api.post('/test-cases/batch', testCasesToCreate)
    ElMessage.success(`成功导入 ${testCasesToCreate.length} 个测试用例`)
    batchDialogVisible.value = false
    loadTestCases()
  } catch (error) {
    ElMessage.error('批量导入失败')
  }
}

// 截断文本
const truncate = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

onMounted(() => {
  loadProblem()
  loadTestCases()
})
</script>

<style scoped>
.test-case-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.code-preview {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.footer-actions {
  margin-top: 20px;
  text-align: right;
}
.drag-handle {
  cursor: grab;
  display: inline-block;
  padding: 4px 6px;
  border-radius: 4px;
  color: #606266;
}
.drag-handle:active { cursor: grabbing }

.drag-cell {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 0;
}

tr.dragging-row td {
  opacity: 0.6;
  transform: scale(0.995);
  transition: opacity 120ms ease, transform 120ms ease;
}

tr.drag-over-before {
  position: relative;
}
tr.drag-over-after {
  position: relative;
}

tr.drag-over-before td::before,
tr.drag-over-after td::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, rgba(64,158,255,0.2), rgba(64,158,255,0.8));
  box-shadow: 0 2px 6px rgba(64,158,255,0.15);
  animation: slide-highlight 900ms linear infinite;
  pointer-events: none;
}
tr.drag-over-before td::before { top: 0; }
tr.drag-over-after td::after { bottom: 0; }

@keyframes slide-highlight { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }

.drag-over-before td { border-top: 3px solid #409eff; background: rgba(64,158,255,0.03); }
.drag-over-after td { border-bottom: 3px solid #409eff; background: rgba(64,158,255,0.03); }

/* 占位行样式 */
.drag-placeholder {
  height: 48px;
  background: rgba(64,158,255,0.06);
  border: 1px dashed rgba(64,158,255,0.25);
  border-radius: 4px;
  transition: height 180ms ease, opacity 180ms ease, transform 180ms ease;
  opacity: 0.95;
}
.drag-placeholder::before { content: ''; display: block; height: 100%; }
</style>
