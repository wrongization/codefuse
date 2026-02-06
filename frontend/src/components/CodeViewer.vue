<template>
  <div class="codeviewer">
    <div class="meta" v-if="showMeta">
      <span class="lang">{{ displayLang }}</span>
      <el-button size="small" @click="copy" :disabled="!code">复制</el-button>
    </div>
    <pre class="hl-pre"><code ref="codeEl" class="hljs"></code></pre>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  code: { type: String, default: '' },
  language: { type: String, default: '' },
  showMeta: { type: Boolean, default: true }
})

const codeEl = ref(null)
const displayLang = computed(() => props.language || '')

let hljs = null
const loadHLJS = async () => {
  if (hljs) return hljs
  // try dynamic import first (works if highlight.js installed)
  try {
    const mod = await import('highlight.js')
    try { await import('highlight.js/styles/github.css') } catch (e) { /* ignore style load errors */ }
    hljs = mod.default || mod
    return hljs
  } catch (e) {
    // fallback to CDN
    if (!window.hljs) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.css'
      document.head.appendChild(link)
      await new Promise((resolve, reject) => {
        const s = document.createElement('script')
        s.src = 'https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/common.min.js'
        s.onload = resolve
        s.onerror = reject
        document.head.appendChild(s)
      })
    }
    hljs = window.hljs
    return hljs
  }
}

const highlight = async () => {
  if (!codeEl.value) return
  const text = props.code || ''
  codeEl.value.textContent = text
  try {
    const h = await loadHLJS()
    if (!h) return
    if (props.language && h.getLanguage && h.getLanguage(props.language)) {
      const result = h.highlight(text, { language: props.language, ignoreIllegals: true })
      codeEl.value.innerHTML = result.value
    } else if (h.highlightAuto) {
      const result = h.highlightAuto(text)
      codeEl.value.innerHTML = result.value
    } else {
      codeEl.value.textContent = text
    }
  } catch (e) {
    codeEl.value.textContent = text
  }
}

onMounted(highlight)
watch(() => props.code, highlight)
watch(() => props.language, highlight)

const copy = async () => {
  try {
    await navigator.clipboard.writeText(props.code || '')
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.codeviewer {
  border: 1px solid var(--el-border-color, #e6e6e6);
  border-radius: 6px;
  background: var(--el-background-color, #fff);
  overflow: hidden;
}
.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  background: linear-gradient(90deg, rgba(0,0,0,0.02), rgba(0,0,0,0.01));
}
.meta .lang {
  font-size: 12px;
  color: #606266;
}
.hl-pre {
  margin: 0;
  padding: 12px;
  max-height: 600px;
  overflow: auto;
  background: transparent;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.45;
}
</style>
