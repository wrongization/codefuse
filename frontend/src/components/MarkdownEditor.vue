<template>
  <div class="markdown-editor">
    <el-tabs v-model="activeTab" size="small" class="markdown-editor__tabs">
      <el-tab-pane name="edit" label="编辑">
        <el-input
          v-model="localValue"
          type="textarea"
          :rows="rows"
          :placeholder="placeholder"
          class="markdown-editor__textarea"
        />
        <div class="markdown-editor__hint">支持 Markdown 语法</div>
      </el-tab-pane>
      <el-tab-pane name="preview" label="预览">
        <div
          v-if="localValue"
          class="markdown-body markdown-editor__preview"
          v-html="renderedContent"
        />
        <div v-else class="markdown-editor__empty">暂无内容</div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: Number, default: 6 },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref('edit')
const localValue = ref(props.modelValue || '')

watch(
  () => props.modelValue,
  (val) => {
    if (val !== localValue.value) {
      localValue.value = val || ''
    }
  }
)

watch(localValue, (val) => {
  emit('update:modelValue', val)
})

const renderedContent = computed(() => renderMarkdown(localValue.value))
const rows = computed(() => props.rows)
const placeholder = computed(() => props.placeholder || '支持 Markdown 格式')
</script>

<style scoped>
.markdown-editor {
  width: 100%;
}

.markdown-editor__tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.markdown-editor__textarea :deep(.el-textarea__inner) {
  font-family: 'Fira Code', 'Courier New', monospace;
}

.markdown-editor__hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.markdown-editor__preview {
  min-height: 160px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 8px;
  background: var(--el-fill-color-light, #fafafa);
}

.markdown-editor__empty {
  min-height: 160px;
  padding: 16px;
  color: #999;
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafbfc;
}
</style>
