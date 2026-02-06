<template>
  <div class="home">
    <!-- Hero 横幅：仿 VSCode 官网风格 -->
    <section class="hero-section rounded soft-shadow fade-in-up">
      <div class="hero-inner">
        <div class="hero-left">
          <h1 class="hero-title">CodeFuse — 为程序员打造的练习与竞赛平台</h1>
          <p class="hero-subtitle">在真实竞赛环境中训练，在开放社区中成长。快速提交，实时评测，智能推荐题目。</p>

          <div class="hero-ctas">
            <el-button size="large" type="primary" @click="goToProblems">开始刷题</el-button>
            <el-button size="large" plain @click="goToContests">参与比赛</el-button>
          </div>

          <div class="hero-features">
            <div class="hf-item">
              <el-icon :size="20" color="#409eff"><Check /></el-icon>
              <span>智能评测与详细报告</span>
            </div>
            <div class="hf-item">
              <el-icon :size="20" color="#67c23a"><ChatDotRound /></el-icon>
              <span>活跃讨论与私信</span>
            </div>
            <div class="hf-item">
              <el-icon :size="20" color="#e6a23c"><Trophy /></el-icon>
              <span>比赛模拟与排名</span>
            </div>
          </div>
        </div>

        <div class="hero-right">
          <!-- 简单的展示面板或截图占位 -->
          <div class="screen-mock rounded soft-shadow">
            <div class="screen-header">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <div class="screen-body">
              <!-- 用现有组件或静态示例填充 -->
              <pre class="code-sample">
                long long binpow(long long a, long long b, long long p) {
                  if (b == 0) return 1;
                  long long res = binpow(a, b / 2, p);
                  if (b % 2)
                    return res * res % p * a % p;
                  else
                    return res * res % p;
                }
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 快速入口 -->
    <div class="quick-actions">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="action-card" @click="goToProblems">
            <el-icon :size="50" color="#409eff"><Document /></el-icon>
            <h3>题库</h3>
            <p>{{ stats.problems }} 道题目</p>
            <el-button type="primary" link>立即开始 →</el-button>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="action-card" @click="goToContests">
            <el-icon :size="50" color="#67c23a"><Trophy /></el-icon>
            <h3>比赛</h3>
            <p>参与编程竞赛</p>
            <el-button type="success" link>查看比赛 →</el-button>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="action-card" @click="goToSubmissions">
            <el-icon :size="50" color="#e6a23c"><Histogram /></el-icon>
            <h3>提交记录</h3>
            <p>{{ stats.submissions }} 次提交</p>
            <el-button type="warning" link>查看记录 →</el-button>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="action-card" @click="goToProfile">
            <el-icon :size="50" color="#f56c6c"><User /></el-icon>
            <h3>个人中心</h3>
            <p>管理个人信息</p>
            <el-button type="danger" link>进入中心 →</el-button>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 特性介绍 -->
    <el-card class="features-card">
      <template #header>
        <h2><el-icon><Star /></el-icon> 平台特色</h2>
      </template>
      <el-row :gutter="30">
        <el-col :span="8" v-for="(feature, index) in platformFeatures" :key="index">
          <div class="feature-item">
            <div class="feature-icon">
              <el-icon :size="40" :color="feature.color">
                <component :is="feature.icon" />
              </el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="stats-card">
      <template #header>
        <h2>平台统计</h2>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-statistic title="题目总数" :value="stats.problems" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="用户总数" :value="stats.users" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="提交总数" :value="stats.submissions" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Edit,
  ChatDotRound,
  Share,
  Trophy,
  Check,
  Document,
  Histogram,
  User,
  Star,
  TrendCharts,
  Connection,
  Management
} from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()

// 统计数据
const stats = ref({
  problems: 0,
  users: 0,
  submissions: 0
})

// 轮播图内容
const carouselItems = [
  {
    icon: Edit,
    iconColor: '#409eff',
    title: '多态学习模式',
    description: '支持团队协作和独立练习',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    features: [
      '团队协作：与队友共同解决问题',
      '独立尝试：专注个人成长',
      '灵活切换：适应不同学习场景'
    ]
  },
  {
    icon: ChatDotRound,
    iconColor: '#67c23a',
    title: '即时反馈系统',
    description: '快速获得帮助和指导',
    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    features: [
      '实时讨论区：随时提问交流',
      '快速响应：社区成员互助',
      '经验分享：学习他人解法'
    ]
  },
  {
    icon: Share,
    iconColor: '#e6a23c',
    title: '开放社区平台',
    description: '贡献内容，分享知识',
    background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    features: [
      '贡献题目：分享你的创意',
      '发布讨论：交流编程心得',
      '互相帮助：建立学习网络'
    ]
  },
  {
    icon: Trophy,
    iconColor: '#f56c6c',
    title: '竞赛模拟训练',
    description: '提升实战能力',
    background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    features: [
      '模拟比赛：真实竞赛环境',
      '难度分级：循序渐进提升',
      '排名系统：激发学习动力'
    ]
  }
]

// 平台特色
const platformFeatures = [
  {
    icon: TrendCharts,
    color: '#409eff',
    title: '智能评测系统',
    description: '支持多种编程语言，实时评测代码，详细的运行结果分析'
  },
  {
    icon: Connection,
    color: '#67c23a',
    title: '协作式学习',
    description: '支持多人提交，团队协作解题，培养团队合作能力'
  },
  {
    icon: Management,
    color: '#e6a23c',
    title: '完善的管理',
    description: '题目管理、用户管理、比赛管理，系统活动全记录'
  },
  {
    icon: Star,
    color: '#f56c6c',
    title: '个性化推荐',
    description: '根据做题记录智能推荐，帮助你突破学习瓶颈'
  },
  {
    icon: ChatDotRound,
    color: '#909399',
    title: '讨论社区',
    description: '题目讨论、私信交流，构建活跃的学习社区'
  },
  {
    icon: Document,
    color: '#5cb87a',
    title: '丰富题库',
    description: '覆盖算法、数据结构等多个领域，难度分级明确'
  }
]

// 加载统计数据
onMounted(async () => {
  try {
    const [problems, users, submissions] = await Promise.all([
      api.get('/problems'),
      api.get('/users'),
      api.get('/submissions')
    ])
    stats.value = {
      problems: problems.data.length,
      users: users.data.length,
      submissions: submissions.data.length
    }
  } catch (error) {
    console.error('获取统计信息失败', error)
  }
})

// 导航函数
const goToProblems = () => {
  router.push('/problems')
}

const goToContests = () => {
  router.push('/contests')
}

const goToSubmissions = () => {
  router.push('/submissions')
}

const goToProfile = () => {
  const userId = localStorage.getItem('userId')
  if (!userId) {
    ElMessage.warning('请先登录')
    return
  }
  router.push('/profile')
}
</script>

<style scoped>
.home {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* Hero 横幅样式 */
.hero-section {
  padding: 48px 32px;
  background: linear-gradient(180deg, rgba(64,158,255,0.06), rgba(255,255,255,0.6));
  margin-bottom: 32px;
}
.hero-inner {
  display: flex;
  gap: 32px;
  align-items: center;
}
.hero-left { flex: 1; }
.hero-right { width: 520px; }
.hero-title {
  font-size: 36px;
  line-height: 1.15;
  margin: 0 0 12px;
  color: #0b1727;
}
.hero-subtitle {
  font-size: 18px;
  color: #475569;
  margin-bottom: 20px;
}
.hero-ctas { display: flex; gap: 12px; margin-bottom: 20px }
.hero-features { display: flex; gap: 18px; flex-wrap: wrap }
.hf-item { display:flex; gap:8px; align-items:center; color:#475569 }

.screen-mock { background: linear-gradient(180deg,#0f1724,#061224); color: #e6eef8; padding: 18px; }
.screen-header { height: 14px; display:flex; gap:8px; align-items:center; margin-bottom:12px }
.screen-header .dot { width:10px; height:10px; border-radius:50%; display:inline-block }
.screen-header .red { background:#ff5f56 }
.screen-header .yellow { background:#ffbd2e }
.screen-header .green { background:#27c93f }
.screen-body { background: rgba(255,255,255,0.03); padding: 12px; border-radius: 6px; min-height: 220px }
.code-sample { color: #cfe8ff; font-size: 13px; margin:0; overflow:auto }

/* 轮播图样式 */
.hero-carousel {
  margin-bottom: 40px;
  border-radius: 10px;
  overflow: hidden;
}

.carousel-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: white;
  border-radius: 10px;
}

.carousel-icon {
  margin-bottom: 20px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.carousel-content h2 {
  font-size: 32px;
  margin-bottom: 15px;
  font-weight: bold;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.carousel-content p {
  font-size: 18px;
  margin-bottom: 25px;
  opacity: 0.95;
}

.feature-list {
  list-style: none;
  padding: 0;
  text-align: left;
  max-width: 400px;
}

.feature-list li {
  padding: 8px 0;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.feature-list li .el-icon {
  font-size: 20px;
  flex-shrink: 0;
}

/* 快速入口卡片 */
.quick-actions {
  margin-bottom: 40px;
}

.action-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.action-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.action-card .el-icon {
  margin-bottom: 15px;
}

.action-card h3 {
  font-size: 20px;
  margin: 15px 0 10px;
  color: #303133;
}

.action-card p {
  color: #909399;
  font-size: 14px;
  margin-bottom: 15px;
}

.action-card .el-button {
  font-size: 14px;
  font-weight: bold;
}

/* 特性介绍卡片 */
.features-card {
  margin-bottom: 40px;
}

.features-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
}

.features-card h2 {
  margin: 0;
  font-size: 24px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.feature-item {
  text-align: center;
  padding: 20px;
  transition: all 0.3s ease;
}

.feature-item:hover {
  transform: scale(1.05);
}

.feature-icon {
  margin-bottom: 20px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-item h3 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 10px;
}

.feature-item p {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

/* 统计卡片 */
.stats-card {
  text-align: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.stats-card :deep(.el-card__header) {
  border-bottom: none;
  padding-bottom: 0;
}

.stats-card h2 {
  color: #303133;
  margin: 0;
}

:deep(.el-statistic) {
  padding: 20px;
}

:deep(.el-statistic__head) {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
}

:deep(.el-statistic__content) {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .hero-carousel {
    height: 300px !important;
  }
  
  .carousel-content h2 {
    font-size: 24px;
  }
  
  .carousel-content p {
    font-size: 14px;
  }
  
  .feature-list li {
    font-size: 14px;
  }
  
  .action-card {
    margin-bottom: 15px;
  }
}
</style>
