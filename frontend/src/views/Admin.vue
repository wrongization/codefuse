<template>
  <div class="admin-container">
    <el-card class="header-card">
      <h2>管理中心</h2>
      <p>欢迎使用 CodeFuse 管理后台</p>
    </el-card>

    <el-tabs v-model="activeTab" type="border-card" class="admin-tabs">
      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <div class="tab-header">
          <h3>用户管理</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-input 
              v-model="userSearch" 
              placeholder="搜索用户名或邮箱" 
              style="width: 250px"
              @keyup.enter="loadUsers"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="loadUsers">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="userSearch = ''; userSortField = ''; userSortOrder = ''; loadUsers()">重置</el-button>
          </div>
        </div>

        <el-table :data="pagedUsers" style="width: 100%" v-loading="loadingUsers" @sort-change="handleUserSortChange">
          <el-table-column prop="user_id" label="ID" width="80" sortable="custom" />
          <el-table-column prop="username" label="用户名" min-width="120" sortable="custom">
            <template #default="{ row }">
              <el-link
                type="primary"
                :underline="false"
                @click="router.push({ name: 'UserDetail', params: { id: row.user_id } })"
              >
                {{ row.username }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="180" sortable="custom" />
          <el-table-column prop="school" label="学校" min-width="150" sortable="custom" />
          <el-table-column prop="rating" label="积分" width="100" sortable="custom" />
          <el-table-column prop="role" label="角色" width="100" sortable="custom">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'danger' : ''">
                {{ row.role === 'admin' ? '管理员' : '用户' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" width="180" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewUserDetail(row)">详细信息</el-button>
              <el-button size="small" type="danger" @click="deleteUser(row.user_id)" :disabled="row.role === 'admin'">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="userPage"
          :page-size="PAGE_SIZE"
          :total="totalUsers"
          layout="total, prev, pager, next"
          @current-change="onUserPageChange"
          style="margin-top: 20px; text-align: center"
        />
      </el-tab-pane>

      <!-- 提交记录管理 -->
      <!-- 私信管理 -->
      <el-tab-pane label="私信管理" name="messages">
        <div class="tab-header">
          <h3>私信管理</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-input
              v-model="messageSearch"
              placeholder="搜索标题或内容"
              style="width: 250px"
              clearable
              @keyup.enter="loadMessages"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="loadMessages">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="messageSearch = ''; messageSortField = ''; messageSortOrder = ''; loadMessages()">重置</el-button>
          </div>
        </div>

        <el-table :data="pagedMessages" style="width: 100%" v-loading="loadingMessages" @sort-change="handleMessageSortChange">
          <el-table-column prop="message_id" label="ID" width="80" sortable="custom" />
          <el-table-column prop="creator_name" label="发送人" width="120" sortable="custom">
            <template #default="{ row }">
              <span v-if="row.creator && row.creator.user_id">
                <el-link type="primary" :underline="false" @click="router.push({ name: 'UserDetail', params: { id: row.creator.user_id } })">
                  {{ row.creator.username }}
                </el-link>
              </span>
              <span v-else>N/A</span>
            </template>
          </el-table-column>
          <el-table-column prop="recipients" label="接收人" width="150" sortable="custom">
            <template #default="{ row }">
              <span v-if="row.recipients && row.recipients.length">
                <template v-for="(recipient, idx) in row.recipients" :key="recipient.user_id">
                  <el-link
                    type="primary"
                    :underline="false"
                    @click="router.push({ name: 'UserDetail', params: { id: recipient.user_id } })"
                  >
                    {{ recipient.username }}
                  </el-link>
                  <span v-if="idx < row.recipients.length - 1">, </span>
                </template>
              </span>
              <span v-else>N/A</span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip sortable="custom" />
          <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip />
          <el-table-column prop="created_at" label="发送时间" width="180" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewMessageDetail(row)">查看详情</el-button>
              <el-button size="small" type="danger" @click="deleteMessage(row.message_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="messagePage"
          :page-size="PAGE_SIZE"
          :total="totalMessages"
          layout="total, prev, pager, next"
          @current-change="onMessagePageChange"
          style="margin-top: 20px; text-align: center"
        />
      </el-tab-pane>

      <!-- 题目管理 -->
      <el-tab-pane label="题目管理" name="problems">
        <div class="tab-header">
          <h3>题目管理</h3>
          <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
            <el-input
              v-model="problemSearch"
              placeholder="搜索题目标题"
              style="width: 250px"
              @keyup.enter="loadProblems"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select 
              v-model="problemTagsArray" 
              placeholder="选择标签（可多选）" 
              style="width: auto; min-width: 280px; max-width: 600px;" 
              multiple
              @change="loadProblems"
            >
              <el-option v-for="tag in allProblemTags" :key="tag" :label="tag" :value="tag" />
            </el-select>
            <el-button type="primary" @click="loadProblems">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetProblemFilters">重置</el-button>
            <el-button type="primary" @click="showCreateProblem">
              <el-icon><Plus /></el-icon>
              创建题目
            </el-button>
          </div>
        </div>

        <el-table :data="problems" style="width: 100%" v-loading="loadingProblems" @sort-change="handleProblemSortChange">
          <el-table-column prop="problem_id" label="ID" width="80" sortable="custom" />
          <el-table-column prop="title" label="标题" min-width="180" sortable="custom">
            <template #default="{ row }">
              <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="difficulty" label="难度" width="90" sortable="custom">
            <template #default="{ row }">
              <el-tag :type="getDifficultyType(row.difficulty)" size="small">
                {{ getDifficultyText(row.difficulty) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tags" label="标签" min-width="130">
            <template #default="{ row }">
              <span v-if="row.tags">
                <el-tag
                  v-for="rawTag in row.tags.split(',')"
                  :key="rawTag"
                  size="small"
                  :type="problemTagsArray.includes(rawTag.trim()) ? 'primary' : 'info'"
                  style="margin-right: 6px; cursor: pointer"
                  @click.stop="addTagFilter(rawTag.trim())"
                >
                  {{ rawTag.trim() }}
                </el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="time_limit" label="时间 - 内存" width="240" sortable="custom">
            <template #default="{ row }">
              {{ row.time_limit }}ms  -  {{ (row.memory_limit / 1024).toFixed(0) }}MB/{{ (row.memory_limit).toFixed(0) }}KB
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="360" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewProblemDetail(row)">详情</el-button>
              <el-button size="small" @click="editProblem(row)">编辑</el-button>
              <el-button size="small" type="primary" @click="manageTestCases(row)">测试点</el-button>
              <el-button size="small" type="danger" @click="deleteProblem(row.problem_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

      </el-tab-pane>

      <!-- 用户管理 -->
      <!-- 题目讨论管理 -->
      <el-tab-pane label="题目讨论" name="discussions">
        <div class="tab-header">
          <h3>题目讨论管理</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-input
              v-model="discussionSearch"
              placeholder="搜索讨论标题"
              style="width: 250px"
              @keyup.enter="loadDiscussions"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="loadDiscussions">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="discussionSearch = ''; discussionSortField = ''; discussionSortOrder = ''; loadDiscussions()">重置</el-button>
          </div>
        </div>

        <el-table :data="pagedDiscussions" style="width: 100%" v-loading="loadingDiscussions" @sort-change="handleDiscussionSortChange">
          <el-table-column prop="message_id" label="ID" width="80" sortable="custom" />
          <el-table-column prop="problem_title" label="题目" min-width="180" sortable="custom">
            <template #default="{ row }">
              <el-link v-if="row.problem" @click="goToProblemDetail(row.problem.problem_id)" type="primary">
                {{ row.problem.title }}
              </el-link>
              <span v-else>无关联题目</span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="200" sortable="custom">
            <template #default="{ row }">
              <span v-if="row.problem && row.problem.problem_id">
                <el-link type="primary" :underline="false"
                  @click="goToProblemDetail(row.problem.problem_id, row.message_id)">
                  {{ row.title }}
                </el-link>
              </span>
              <span v-else>
                <el-link type="primary" :underline="false" @click="viewDiscussionDetail(row)">
                  {{ row.title }}
                </el-link>
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="发帖人" width="120" sortable="custom">
            <template #default="{ row }">
              <span v-if="row.creator && row.creator.user_id">
                <el-link type="primary" :underline="false" @click="router.push({ name: 'UserDetail', params: { id: row.creator.user_id } })">
                  {{ row.creator.username }}
                </el-link>
              </span>
              <span v-else>N/A</span>
            </template>
          </el-table-column>
          <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip />
          <el-table-column prop="created_at" label="发布时间" width="180" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewDiscussionDetail(row)">查看详情</el-button>
              <el-button size="small" type="danger" @click="deleteDiscussion(row.message_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="discussionPage"
          :page-size="PAGE_SIZE"
          :total="totalDiscussions"
          layout="total, prev, pager, next"
          @current-change="onDiscussionPageChange"
          style="margin-top: 20px; text-align: center"
        />
      </el-tab-pane>

      <!-- 私信管理 -->
      <!-- 比赛管理 -->
      <!-- 提交记录管理 -->
      <el-tab-pane label="提交记录" name="submissions">
        <div class="tab-header">
          <h3>提交记录管理</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-input
              v-model="submissionUserSearch"
              placeholder="搜索用户"
              style="width: 150px"
              clearable
              @keyup.enter="loadSubmissions"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
            <el-select
              v-model="problemSubmissionFilterId"
              placeholder="筛选题目"
              filterable
              clearable
              style="width: 240px"
              @change="handleProblemSubmissionFilterChange"
            >
              <el-option
                v-for="p in problems"
                :key="p.problem_id"
                :label="`#${p.problem_id} ${p.title}`"
                :value="p.problem_id"
              />
            </el-select>
            <el-button type="primary" @click="loadSubmissions">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetSubmissionFilters">重置</el-button>
            <el-button type="warning" @click="openBulkRejudgeDialog">
              批量重测
            </el-button>
          </div>
        </div>

  <el-table :data="pagedSubmissions" style="width: 100%; table-layout: auto;" v-loading="loadingSubmissions" @sort-change="handleSubmissionSortChange">
          <el-table-column prop="submission_id" label="ID" width="70" sortable="custom" />
          <el-table-column prop="username" label="用户" min-width="110" sortable="custom" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.user?.username || 'N/A' }}
            </template>
          </el-table-column>
          <el-table-column prop="problem_id" label="题目ID" min-width="90" sortable="custom">
            <template #default="{ row }">
              <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
                #{{ row.problem_id }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="problem_title" label="题目标题" min-width="160" sortable="custom" show-overflow-tooltip>
            <template #default="{ row }">
              <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
                {{ row.problem?.title || '未知题目' }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="contest_id" label="来源" min-width="110" sortable="custom">
            <template #default="{ row }">
              <el-tag v-if="!row.contest_id" type="info" size="small">题库</el-tag>
              <el-tag v-else type="success" size="small">比赛#{{ row.contest_id }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="language" label="语言" min-width="90" sortable="custom" />
          <el-table-column prop="status" label="状态" min-width="110" sortable="custom">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="exec_time" label="时间/内存" min-width="140" sortable="custom">
            <template #default="{ row }">
              {{ row.exec_time }}ms / {{ formatMemory(row.exec_memory) }}
            </template>
          </el-table-column>
          <el-table-column prop="submitted_at" label="提交时间" min-width="170" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.submitted_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="360">
            <template #default="{ row }">
              <el-button size="small" @click="viewSubmissionDetail(row, true)">详情</el-button>
              <el-button size="small" @click="viewCode(row)">代码</el-button>
              <el-button size="small" type="warning" @click="rejudgeSubmission(row.submission_id)" :loading="row.rejudging">重测</el-button>
              <el-button size="small" type="primary" @click="editSubmission(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteSubmission(row.submission_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="submissionPage"
          :page-size="PAGE_SIZE"
          :total="totalSubmissions"
          layout="total, prev, pager, next"
          @current-change="onSubmissionPageChange"
          style="margin-top: 20px; text-align: center"
        />
      </el-tab-pane>

      <!-- 测试点管理 -->
      <!-- 比赛管理 -->
      <el-tab-pane label="比赛管理" name="contests">
        <div class="tab-header">
          <h3>比赛管理</h3>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-input
              v-model="contestSearch"
              placeholder="搜索比赛标题"
              style="width: 250px"
              @keyup.enter="loadContests"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="loadContests">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="contestSearch = ''; contestSortField = ''; contestSortOrder = ''; loadContests()">重置</el-button>
            <el-button type="primary" @click="showCreateContest">
              <el-icon><Plus /></el-icon>
              创建比赛
            </el-button>
          </div>
        </div>

        <el-table :data="contests" style="width: 100%" v-loading="loadingContests" @sort-change="handleContestSortChange">
          <el-table-column prop="contest_id" label="ID" width="70" sortable="custom" />
          <el-table-column prop="title" label="标题" min-width="180" sortable="custom">
            <template #default="{ row }">
              <el-link @click="() => router.push({ name: 'ContestDetail', params: { id: row.contest_id } })" type="primary">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90" sortable="custom">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'upcoming'" type="info" size="small">未开始</el-tag>
              <el-tag v-else-if="row.status === 'ongoing'" type="success" size="small">进行中</el-tag>
              <el-tag v-else type="info" size="small">已结束</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" label="开始时间" width="170" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="end_time" label="结束时间" width="170" sortable="custom">
            <template #default="{ row }">
              {{ formatDate(row.end_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="problem_count" label="题目数" width="90" sortable="custom" />
          <el-table-column prop="participant_count" label="参赛人数" width="100" sortable="custom" />
          <el-table-column label="操作" min-width="460" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewContestDetail(row)">详情</el-button>
              <el-button size="small" @click="manageContestProblems(row)">题目</el-button>
              <el-button size="small" @click="manageContestParticipants(row)">参赛者</el-button>
              <el-button size="small" type="primary" @click="editContest(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteContestAdmin(row.contest_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 系统统计 -->
      <!-- 系统统计 -->
      <el-tab-pane label="系统统计" name="stats">
        <div class="stats-container">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon user-icon">
                  <el-icon :size="40"><User /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ stats.totalUsers }}</div>
                  <div class="stat-label">总用户数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon problem-icon">
                  <el-icon :size="40"><Document /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ stats.totalProblems }}</div>
                  <div class="stat-label">总题目数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon submission-icon">
                  <el-icon :size="40"><Tickets /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ stats.totalSubmissions }}</div>
                  <div class="stat-label">总提交数</div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card class="stat-card">
                <div class="stat-icon contest-icon">
                  <el-icon :size="40"><Trophy /></el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ stats.totalContests }}</div>
                  <div class="stat-label">总比赛数</div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card style="margin-top: 12px; margin-bottom: 10px;">
            <h4>评测线程池</h4>
            <div style="display:flex; gap:12px; align-items:center;">
              <div>运行中: <strong>{{ stats.judge_running || 0 }}</strong></div>
              <div>等待中: <strong>{{ stats.judge_pending || 0 }}</strong></div>
              <div>最大并发: <strong>{{ stats.judge_max_workers || 0 }}</strong></div>
            </div>
          </el-card>

          <el-card style="margin-top: 20px">
            <h3>最近活动</h3>
            <el-empty v-if="recentActivities.length === 0" description="暂无最近活动" />
            <el-timeline v-else>
              <el-timeline-item 
                v-for="activity in recentActivities" 
                :key="activity.id"
                :timestamp="formatDate(activity.time)"
                placement="top"
              >
                {{ activity.content }}
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 题目讨论管理 -->
    </el-tabs>

    <!-- 创建/编辑题目对话框 -->
    <el-dialog 
      v-model="problemDialogVisible" 
      :title="isEditMode ? '编辑题目' : '创建题目'" 
      width="60%"
    >
      <el-form :model="problemForm" label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="problemForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <MarkdownEditor
            v-model="problemForm.description"
            :rows="8"
            placeholder="请输入题目描述（支持 Markdown 格式）"
          />
        </el-form-item>
        <el-form-item label="输入格式">
          <el-input v-model="problemForm.input_format" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="输出格式">
          <el-input v-model="problemForm.output_format" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="样例输入">
          <el-input v-model="problemForm.sample_input" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="样例输出">
          <el-input v-model="problemForm.sample_output" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="时间限制">
              <el-input v-model.number="problemForm.time_limit" type="number">
                <template #append>ms</template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="内存限制">
              <el-input v-model.number="problemForm.memory_limit" type="number">
                <template #append>KB</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="难度">
          <el-select v-model="problemForm.difficulty">
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="problemForm.tags" placeholder="用逗号分隔，如：数组,哈希表" />
        </el-form-item>
        <el-form-item label="可见性" v-if="!isEditMode">
          <el-radio-group v-model="problemForm.visible">
            <el-radio :label="true">公开可见（题库ID>=10000）</el-radio>
            <el-radio :label="false">不可见（保留ID 1-9999，可用于比赛）</el-radio>
          </el-radio-group>
          <div style="color: #909399; font-size: 12px; margin-top: 5px;">
            不可见题目用于比赛专用，不会在公开题库中显示。比赛结束后可发布到题库。
          </div>
        </el-form-item>

        <!-- 编辑模式下显示只读当前可见性 -->
        <el-form-item label="可见性" v-if="isEditMode">
          <div style="display:flex; align-items:center; gap:10px;">
            <el-tag :type="problemForm.visible ? 'success' : 'info'">
              {{ problemForm.visible ? '公开' : '不可见' }}
            </el-tag>
            <small style="color: #909399;">（创建后不可更改）</small>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="problemDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProblem">保存</el-button>
      </template>
    </el-dialog>
    <!-- 批量重测对话框 -->
    <el-dialog v-model="bulkDialogVisible" title="批量重测提交" width="80%">
      <div style="display:flex; gap:12px; margin-bottom:10px; align-items:center">
        <el-input v-model="bulkFilters.user_search" placeholder="用户搜索" style="width:200px" clearable />
        <el-input v-model="bulkFilters.problem_id" placeholder="题目ID" style="width:120px" />
        <el-input v-model="bulkFilters.contest_id" placeholder="比赛ID" style="width:120px" />
        <el-button type="primary" @click="loadBulkSubmissions">查询</el-button>
  <el-button @click="resetBulkFilters">重置</el-button>
      </div>
      <el-table :data="bulkPageSubmissions" style="width: 100%" @selection-change="onSubmissionSelectionChange">
        <el-table-column type="selection" width="55"></el-table-column>
        <el-table-column prop="submission_id" label="ID" width="80" />
        <el-table-column prop="user.username" label="用户" width="140">
          <template #default="{ row }">{{ row.user?.username || row.username || 'N/A' }}</template>
        </el-table-column>
        <el-table-column prop="problem_id" label="题目ID" width="100" />
        <el-table-column prop="problem_title" label="题目标题" min-width="200" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="submitted_at" label="提交时间" width="180" />
      </el-table>
      <div style="display:flex; justify-content:center; margin:8px 0;">
        <el-pagination
          v-model:current-page="bulkPage"
          :page-size="bulkPageSize"
          :total="bulkSubmissions.length"
          layout="prev, pager, next"
        />
      </div>
      <template #footer>
        <div style="display:flex; justify-content: flex-end; gap: 10px;">
          <el-button @click="bulkDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmBulkRejudge">提交重测</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 查看代码对话框 -->
    <el-dialog v-model="codeDialogVisible" title="提交代码" width="60%">
      <CodeViewer :code="currentCode" :language="currentCodeLang" />
      <template #footer>
        <el-button type="primary" @click="codeDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 编辑提交记录对话框 -->
    <el-dialog v-model="submissionEditDialogVisible" title="编辑提交记录" width="500px">
      <el-form :model="submissionEditForm" label-width="100px">
        <el-form-item label="提交ID">
          <el-input v-model="submissionEditForm.submission_id" disabled />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="submissionEditForm.status" style="width: 100%">
            <el-option label="通过" value="accepted" />
            <el-option label="答案错误" value="wrong_answer" />
            <el-option label="超时" value="time_limit_exceeded" />
            <el-option label="运行错误" value="runtime_error" />
            <el-option label="编译错误" value="compile_error" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行时间">
          <el-input v-model.number="submissionEditForm.exec_time" type="number">
            <template #append>ms</template>
          </el-input>
        </el-form-item>
        <el-form-item label="内存使用">
          <el-input v-model.number="submissionEditForm.exec_memory" type="number">
            <template #append>KB</template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="submissionEditDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSubmissionEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 创建/编辑比赛对话框 -->
    <el-dialog
      v-model="contestDialogVisible"
      :title="isEditingContest ? '编辑比赛' : '创建比赛'"
      width="600px"
    >
      <el-form :model="contestForm" label-width="100px">
        <el-form-item label="比赛标题">
          <el-input v-model="contestForm.title" placeholder="请输入比赛标题" />
        </el-form-item>
        <el-form-item label="比赛描述">
          <el-input
            v-model="contestForm.description"
            type="textarea"
            :rows="4"
            placeholder="请输入比赛描述"
          />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="contestForm.start_time"
            type="datetime"
            placeholder="选择开始时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="contestForm.end_time"
            type="datetime"
            placeholder="选择结束时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contestDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveContest">保存</el-button>
      </template>
    </el-dialog>

    <!-- 管理比赛题目对话框 -->
    <el-dialog v-model="contestProblemsDialogVisible" title="管理比赛题目" width="800px">
      <div style="margin-bottom: 20px; display: flex; gap: 10px; align-items: center;">
        <el-input
          v-model.number="addContestProblemId"
          placeholder="输入题目ID"
          style="width: 200px"
        />
        <el-button type="primary" @click="addProblemToContest">添加题目</el-button>
        <span style="color: #909399; margin: 0 10px;">或</span>
        <el-button type="success" @click="openProblemSelector">
          <el-icon><Search /></el-icon>
          从列表选择
        </el-button>
      </div>
      
      <el-table :data="currentContestProblems" style="width: 100%">
        <el-table-column prop="problem_id" label="题目ID" width="100" />
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
              {{ row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="100">
          <template #default="{ row }">
            <el-tag :type="getDifficultyType(row.difficulty)">
              {{ getDifficultyText(row.difficulty) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeProblemFromContest(row.problem_id)">
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <template #footer>
        <el-button type="primary" @click="contestProblemsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 题目选择器对话框 -->
    <el-dialog v-model="problemSelectorVisible" title="选择题目" width="900px">
      <div style="margin-bottom: 20px;">
        <div style="display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; align-items: center;">
          <el-input
            v-model="problemSelectorSearch"
            placeholder="搜索题目标题"
            style="width: 200px"
            clearable
            @keyup.enter="loadAvailableProblems"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select
            v-model="problemSelectorDifficulty"
            placeholder="难度"
            style="width: 120px"
            clearable
          >
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
          
          <el-select
            v-model="problemSelectorTagsArray"
            multiple
            placeholder="标签"
            style="width: auto; min-width: 200px; max-width: 400px;"
          >
            <el-option v-for="tag in availableTags" :key="tag" :label="tag" :value="tag" />
          </el-select>
          
          <el-select
            v-model="problemSelectorVisibility"
            placeholder="可见性"
            style="width: 150px"
            clearable
          >
            <el-option label="公开可见" value="visible" />
            <el-option label="不可见（比赛专用）" value="invisible" />
          </el-select>
          
          <el-button type="primary" @click="loadAvailableProblems">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetProblemSelector">重置</el-button>
        </div>
      </div>
      
      <el-table 
        :data="availableProblems" 
        style="width: 100%" 
        v-loading="loadingAvailableProblems"
      >
        <el-table-column prop="problem_id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
              {{ row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="100">
          <template #default="{ row }">
            <el-tag :type="getDifficultyType(row.difficulty)">
              {{ getDifficultyText(row.difficulty) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" min-width="150">
          <template #default="{ row }">
            <span v-if="row.tags">
              <el-tag 
                v-for="tag in row.tags.split(',')" 
                :key="tag" 
                size="small" 
                style="margin-right: 5px"
              >
                {{ tag }}
              </el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="visible" label="可见性" width="100">
          <template #default="{ row }">
            <el-tag :type="row.visible ? 'success' : 'info'" size="small">
              {{ row.visible ? '公开' : '不可见' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="primary" 
              @click="addProblemFromSelector(row.problem_id)"
              :disabled="currentContestProblems.some(p => p.problem_id === row.problem_id)"
            >
              {{ currentContestProblems.some(p => p.problem_id === row.problem_id) ? '已添加' : '添加' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <template #footer>
        <el-button type="primary" @click="problemSelectorVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 查看讨论详情对话框 -->
    <el-dialog v-model="discussionDetailDialogVisible" title="讨论详情" width="60%">
      <el-descriptions :column="2" border v-if="currentDiscussion">
        <el-descriptions-item label="讨论ID">{{ currentDiscussion.message_id }}</el-descriptions-item>
        <el-descriptions-item label="题目">
          {{ currentDiscussion.problem?.title || `#${currentDiscussion.problem_id}` }}
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentDiscussion.title }}</el-descriptions-item>
        <el-descriptions-item label="发帖人">{{ currentDiscussion.creator?.username }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentDiscussion.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <div style="white-space: pre-wrap;">{{ currentDiscussion.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="discussionDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 查看私信详情对话框 -->
    <el-dialog v-model="messageDetailDialogVisible" title="私信详情" width="60%">
      <el-descriptions :column="2" border v-if="currentMessage">
        <el-descriptions-item label="私信ID" :span="2">{{ currentMessage.message_id }}</el-descriptions-item>
        <el-descriptions-item label="发送人">{{ currentMessage.creator?.username }}</el-descriptions-item>
        <el-descriptions-item label="发送时间">{{ formatDate(currentMessage.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="接收人" :span="2">
          <el-tag 
            v-for="recipient in currentMessage.recipients" 
            :key="recipient.user_id"
            style="margin-right: 5px"
          >
            {{ recipient.username }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentMessage.title }}</el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <div style="white-space: pre-wrap;">{{ currentMessage.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="messageDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 测试点管理对话框 -->
    <el-dialog v-model="testCaseDialogVisible" title="测试点管理" width="80%">
      <div v-if="currentProblemForTestCase">
        <h3>{{ currentProblemForTestCase.title }}</h3>
        <el-button type="primary" @click="addNewTestCase" style="margin-bottom: 20px">添加测试点</el-button>
        
  <el-table :data="displayTestCases" style="width: 100%" :row-class-name="testCaseRowClass">
          <el-table-column label="移动" width="60">
            <template #default="{ $index }">
              <div class="drag-cell" draggable="true" @dragstart="onDragStart($event, $index)" @dragover.prevent="onDragOver($event, $index)" @dragleave="onDragLeave($event, $index)" @drop="onDrop($event, $index)" title="拖动调整顺序">
                <i class="drag-handle">☰</i>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="序号" min-width="60">
            <template #default="{ row, $index }">{{ row.__placeholder ? '' : ($index + 1) }}</template>
          </el-table-column>
          <el-table-column label="是否样例" min-width="120">
            <template #default="{ row }">
              <el-switch v-model="row.is_sample" :active-value="1" :inactive-value="0" />
            </template>
          </el-table-column>
          <el-table-column label="输入" min-width="160">
            <template #default="{ row }">
              <div v-if="row.__placeholder" class="drag-placeholder">&nbsp;</div>
              <div v-else>
                <el-input v-model="row.input_data" type="textarea" :rows="2" style="font-family: 'Courier New', monospace;" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="期望输出" min-width="200">
            <template #default="{ row }">
              <div v-if="row.__placeholder" class="drag-placeholder">&nbsp;</div>
              <div v-else>
                <el-input v-model="row.output_data" type="textarea" :rows="2" style="font-family: 'Courier New', monospace;" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="分数" min-width="90">
            <template #default="{ row }">
              <div v-if="row.__placeholder" class="drag-placeholder">&nbsp;</div>
              <div v-else>
                <el-input-number v-model="row.score" :min="0" :max="100" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row, $index }">
              <el-button size="small" type="danger" @click="removeTestCase($index)" :disabled="row.__placeholder">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="testCaseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTestCases">保存</el-button>
      </template>
    </el-dialog>

    <!-- 提交详情对话框 -->
    <el-dialog v-model="submissionDetailDialogVisible" :title="`提交详情 #${currentSubmissionDetail?.submission_id || ''}`" width="80%">
      <div v-if="currentSubmissionDetail">
        <el-descriptions :column="2" border style="margin-bottom: 20px">
          <el-descriptions-item label="提交ID">{{ currentSubmissionDetail.submission_id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ currentSubmissionDetail.user?.username || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="题目">{{ currentSubmissionDetail.problem?.title || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="语言">{{ currentSubmissionDetail.language }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentSubmissionDetail.status)">
              {{ getStatusText(currentSubmissionDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag v-if="!currentSubmissionDetail.contest_id" type="info">题库</el-tag>
            <el-tag v-else type="success">比赛 #{{ currentSubmissionDetail.contest_id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">{{ currentSubmissionDetail.exec_time }}ms</el-descriptions-item>
          <el-descriptions-item label="内存使用">{{ formatMemory(currentSubmissionDetail.exec_memory) }}</el-descriptions-item>
          <el-descriptions-item label="提交时间" :span="2">{{ formatDate(currentSubmissionDetail.submitted_at) }}</el-descriptions-item>
        </el-descriptions>

        <h3>测试点详情</h3>
        <el-table :data="currentSubmissionDetail.judge_results" style="width: 100%">
          <el-table-column label="测试点" width="100">
            <template #default="{ row }">测试点 {{ row.test_case_index + 1 }}</template>
          </el-table-column>
          <el-table-column label="状态" width="150">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="用时" width="100">
            <template #default="{ row }">{{ row.time_used }}ms</template>
          </el-table-column>
          <el-table-column label="内存" width="120">
            <template #default="{ row }">{{ formatMemory(row.memory_used) }}</template>
          </el-table-column>
          <el-table-column label="得分" width="80">
            <template #default="{ row }">{{ row.score }}</template>
          </el-table-column>
          <el-table-column v-if="showTestCaseIO" label="输入" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.input || 'N/A' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="showTestCaseIO" label="期望输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.expected_output || 'N/A' }}</pre>
            </template>
          </el-table-column>
          <el-table-column v-if="showTestCaseIO" label="实际输出" min-width="150">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0;">{{ row.actual_output || 'N/A' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <span style="color: red;">{{ row.error_message || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>

  <h3 style="margin-top: 20px">提交代码</h3>
  <CodeViewer :code="currentSubmissionDetail.code" :language="currentSubmissionDetail.language" />
      </div>
      <template #footer>
        <el-button type="primary" @click="submissionDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 用户详情对话框 -->
    <el-dialog v-model="userDetailDialogVisible" title="用户详细信息" width="60%">
      <el-descriptions :column="2" border v-if="currentUserDetail">
        <el-descriptions-item label="用户ID">{{ currentUserDetail.user_id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ currentUserDetail.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ currentUserDetail.email }}</el-descriptions-item>
        <el-descriptions-item label="学校">{{ currentUserDetail.school || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="积分">{{ currentUserDetail.rating }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="currentUserDetail.role === 'admin' ? 'danger' : ''">
            {{ currentUserDetail.role === 'admin' ? '管理员' : '用户' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间" :span="2">{{ formatDate(currentUserDetail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="头像" :span="2">{{ currentUserDetail.avatar || '未设置' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="userDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 题目详情对话框 -->
    <el-dialog v-model="problemDetailDialogVisible" title="题目详细信息" width="70%">
      <el-descriptions :column="2" border v-if="currentProblemDetail">
        <el-descriptions-item label="题目ID">{{ currentProblemDetail.problem_id }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ currentProblemDetail.title }}</el-descriptions-item>
        <el-descriptions-item label="难度">
          <el-tag :type="getDifficultyType(currentProblemDetail.difficulty)">
            {{ getDifficultyText(currentProblemDetail.difficulty) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标签">{{ currentProblemDetail.tags || '无' }}</el-descriptions-item>
        <el-descriptions-item label="时间限制">{{ currentProblemDetail.time_limit }}ms</el-descriptions-item>
        <el-descriptions-item label="内存限制">{{ (currentProblemDetail.memory_limit / 1024).toFixed(0) }}MB / {{ (currentProblemDetail.memory_limit).toFixed(0) }}KB</el-descriptions-item>
        <el-descriptions-item label="创建者ID">{{ currentProblemDetail.creator_id }}</el-descriptions-item>
        <el-descriptions-item label="测试点数量">{{ currentProblemDetail.test_cases?.length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          <div style="white-space: pre-wrap;">{{ currentProblemDetail.description }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="输入格式" :span="2">
          <div style="white-space: pre-wrap;">{{ currentProblemDetail.input_format }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="输出格式" :span="2">
          <div style="white-space: pre-wrap;">{{ currentProblemDetail.output_format }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="样例输入" :span="2">
          <pre style="margin: 0;">{{ currentProblemDetail.sample_input }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="样例输出" :span="2">
          <pre style="margin: 0;">{{ currentProblemDetail.sample_output }}</pre>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 测试点列表 -->
      <div v-if="currentProblemDetail?.test_cases && currentProblemDetail.test_cases.length > 0" style="margin-top: 20px;">
        <h3>测试点信息</h3>
  <el-table :data="currentProblemDetail.test_cases" style="width: 100%">
          <el-table-column label="序号" width="80" type="index" :index="(index) => index + 1" />
          <el-table-column label="输入数据" min-width="200">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0; font-size: 12px;">{{ row.input_data || 'N/A' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="期望输出" min-width="200">
            <template #default="{ row }">
              <pre style="max-height: 100px; overflow-y: auto; margin: 0; font-size: 12px;">{{ row.output_data || 'N/A' }}</pre>
            </template>
          </el-table-column>
          <el-table-column label="分数" width="80">
            <template #default="{ row }">{{ row.score }}</template>
          </el-table-column>
          <el-table-column label="是否样例" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_sample ? 'success' : 'info'" size="small">
                {{ row.is_sample ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else-if="currentProblemDetail" description="暂无测试点" style="margin-top: 20px;" />

      <template #footer>
        <el-button type="primary" @click="problemDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 比赛详情对话框 -->
    <el-dialog v-model="contestDetailDialogVisible" title="比赛详细信息" width="70%">
      <el-descriptions :column="2" border v-if="currentContestDetail">
        <el-descriptions-item label="比赛ID">{{ currentContestDetail.contest_id }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ currentContestDetail.title }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="currentContestDetail.status === 'upcoming'" type="info">未开始</el-tag>
          <el-tag v-else-if="currentContestDetail.status === 'ongoing'" type="success">进行中</el-tag>
          <el-tag v-else type="info">已结束</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建者ID">{{ currentContestDetail.creator_id }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatDate(currentContestDetail.start_time) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ formatDate(currentContestDetail.end_time) }}</el-descriptions-item>
        <el-descriptions-item label="题目数量">{{ currentContestDetail.problems?.length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="参赛人数">{{ currentContestDetail.participants?.length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          <div style="white-space: pre-wrap;">{{ currentContestDetail.description }}</div>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 题目列表 -->
      <div v-if="currentContestDetail" style="margin-top: 20px;">
        <h4>包含的题目 ({{ currentContestDetail.problems?.length || 0 }})</h4>
  <el-table :data="currentContestDetail.problems" style="width: 100%">
          <el-table-column prop="problem_id" label="题目ID" width="80" />
          <el-table-column prop="title" label="标题" min-width="200">
            <template #default="{ row }">
              <el-link @click="goToProblemDetail(row.problem_id)" type="primary">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="difficulty" label="难度" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.difficulty === 'easy'" type="success">简单</el-tag>
              <el-tag v-else-if="row.difficulty === 'medium'" type="warning">中等</el-tag>
              <el-tag v-else-if="row.difficulty === 'hard'" type="danger">困难</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tags" label="标签" width="150" />
          <template #empty>
            <el-empty description="暂无题目" />
          </template>
        </el-table>
      </div>

      <template #footer>
        <el-button type="primary" @click="contestDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 参赛用户管理对话框 -->
    <el-dialog v-model="participantsDialogVisible" title="参赛用户管理" width="70%">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <h4 style="margin: 0;">参赛用户 ({{ currentContestParticipants?.length || 0 }})</h4>
        <el-button type="primary" size="small" @click="showAddParticipantDialog">
          <el-icon><Plus /></el-icon>
          添加参赛用户
        </el-button>
      </div>
  <el-table :data="currentContestParticipants" style="width: 100%">
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="school" label="学校" width="200" />
        <el-table-column prop="rating" label="积分" width="100" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeParticipant(row.user_id)">移除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无参赛用户" />
        </template>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="participantsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 添加参赛用户对话框 -->
    <el-dialog v-model="addParticipantDialogVisible" title="添加参赛用户" width="500px">
      <el-form>
        <el-form-item label="选择用户">
          <el-select 
            v-model="selectedParticipantId" 
            filterable 
            remote 
            placeholder="输入用户名搜索"
            :remote-method="searchUsers"
            :loading="searchingUsers"
            style="width: 100%"
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.user_id"
              :label="`${user.username} (ID: ${user.user_id})`"
              :value="user.user_id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addParticipantDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addParticipant">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, User, Document, Tickets, Trophy, Collection } from '@element-plus/icons-vue'
import api from '../api'
import CodeViewer from '@/components/CodeViewer.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const PAGE_SIZE = 20

const router = useRouter()
const route = useRoute()
const activeTab = ref('users')

// 题目相关
const problems = ref([])
const loadingProblems = ref(false)
const problemDialogVisible = ref(false)
const isEditMode = ref(false)
const currentEditId = ref(null)
const problemSearch = ref('')
const problemTagsArray = ref([])  // 改为数组，支持多选
const problemSortField = ref('')
const problemSortOrder = ref('')
const allProblemTags = ref([])
const problemForm = ref({
  title: '',
  description: '',
  input_format: '',
  output_format: '',
  sample_input: '',
  sample_output: '',
  time_limit: 1000,
  memory_limit: 262144,
  difficulty: 'easy',
  tags: '',
  visible: true
})
const problemSubmissionFilterId = ref(null)

// 用户相关
const users = ref([])
const loadingUsers = ref(false)
const userSearch = ref('')
const userSortField = ref('')
const userSortOrder = ref('')
const userPage = ref(1)
const totalUsers = ref(0)

// 提交记录相关
const submissions = ref([])
const loadingSubmissions = ref(false)
const submissionUserSearch = ref('')
const submissionSortField = ref('')
const submissionSortOrder = ref('')
const submissionPage = ref(1)
const totalSubmissions = ref(0)
const codeDialogVisible = ref(false)
const currentCode = ref('')
const submissionEditDialogVisible = ref(false)
const currentCodeLang = ref('')
const submissionEditForm = ref({
  submission_id: null,
  status: '',
  exec_time: 0,
  exec_memory: 0
})

// 比赛相关
const contests = ref([])
const loadingContests = ref(false)
const contestSearch = ref('')
const contestSortField = ref('')
const contestSortOrder = ref('')
const contestDialogVisible = ref(false)
const isEditingContest = ref(false)
const contestForm = ref({
  contest_id: null,
  title: '',
  description: '',
  start_time: null,
  end_time: null
})
const contestProblemsDialogVisible = ref(false)
const currentContestId = ref(null)
const currentContestProblems = ref([])
const addContestProblemId = ref(null)

// 题目选择器相关
const problemSelectorVisible = ref(false)
const availableProblems = ref([])
const loadingAvailableProblems = ref(false)
const problemSelectorSearch = ref('')
const problemSelectorDifficulty = ref('')
const problemSelectorTagsArray = ref([])
const problemSelectorVisibility = ref('') // 'visible', 'invisible', ''

// 讨论相关
const discussions = ref([])
const loadingDiscussions = ref(false)
const discussionSearch = ref('')
const discussionSortField = ref('')
const discussionSortOrder = ref('')
const discussionPage = ref(1)
const totalDiscussions = ref(0)
const discussionDetailDialogVisible = ref(false)
const currentDiscussion = ref(null)

// 私信相关
const messages = ref([])
const loadingMessages = ref(false)
const messageSearch = ref('')
const messageSortField = ref('')
const messageSortOrder = ref('')
const messagePage = ref(1)
const totalMessages = ref(0)
const messageDetailDialogVisible = ref(false)
const currentMessage = ref(null)

// 测试点管理相关
const testCaseDialogVisible = ref(false)
const currentProblemForTestCase = ref(null)
const currentTestCases = ref([])
// 用于跟踪原始的 test_case_id 集合和被删除的 id 列表，避免运行时未定义引用
const originalTestCaseIds = ref([])
const removedTestCaseIds = ref([])

// 提交详情相关
const submissionDetailDialogVisible = ref(false)
const currentSubmissionDetail = ref(null)
const showTestCaseIO = ref(false) // 是否显示测试点的输入输出（管理员才显示）

// 用户详情对话框
const userDetailDialogVisible = ref(false)
const currentUserDetail = ref(null)

// 题目详情对话框
const problemDetailDialogVisible = ref(false)
const currentProblemDetail = ref(null)

// 比赛详情对话框
const contestDetailDialogVisible = ref(false)
const currentContestDetail = ref(null)

// 参赛用户管理对话框
const participantsDialogVisible = ref(false)
const currentContestParticipants = ref([])
const currentManageContestId = ref(null)
const addParticipantDialogVisible = ref(false)
const selectedParticipantId = ref(null)
const availableUsers = ref([])
const searchingUsers = ref(false)

// 统计数据
const stats = ref({
  totalUsers: 0,
  totalProblems: 0,
  totalSubmissions: 0,
  totalContests: 0
})
const recentActivities = ref([])

// 分页后的展示数据
const pagedUsers = computed(() => {
  const start = (userPage.value - 1) * PAGE_SIZE
  return users.value.slice(start, start + PAGE_SIZE)
})

const pagedMessages = computed(() => {
  const start = (messagePage.value - 1) * PAGE_SIZE
  return messages.value.slice(start, start + PAGE_SIZE)
})

const pagedDiscussions = computed(() => {
  const start = (discussionPage.value - 1) * PAGE_SIZE
  return discussions.value.slice(start, start + PAGE_SIZE)
})

const pagedSubmissions = computed(() => {
  const start = (submissionPage.value - 1) * PAGE_SIZE
  return submissions.value.slice(start, start + PAGE_SIZE)
})

const ensurePageInRange = (pageRef, total) => {
  const maxPage = Math.max(1, Math.ceil((total || 0) / PAGE_SIZE) || 1)
  if (pageRef.value > maxPage) {
    pageRef.value = maxPage
  }
}

onMounted(async () => {
  // load core data
  await loadProblems()
  await loadProblemTags()
  loadUsers()
  loadSubmissions()
  loadContests()
  loadStats()

  // 如果路由查询中包含 manage_problem_id，自动打开该题目的测试点管理面板
  const manageId = route.query.manage_problem_id
  if (manageId) {
    const pid = parseInt(manageId)
    // 等待 problems 加载后尝试找到题目
    const problem = problems.value.find(p => p.problem_id === pid)
    if (problem) {
      activeTab.value = 'problems'
      // 延迟让 UI 渲染后打开对话框
      setTimeout(() => {
        try {
          manageTestCases(problem)
        } catch (e) {
          console.error('自动打开测试点管理失败', e)
        }
      }, 50)
    }
  }

  // 如果路由查询中包含 tab，使用它作为激活的子页面（允许在不同页面间跳转后返回保留上次标签）
  const tabFromQuery = route.query.tab
  if (tabFromQuery) {
    try {
      activeTab.value = String(tabFromQuery)
    } catch (e) {
      console.warn('无效的 tab query:', tabFromQuery)
    }
  }
})

// 监听标签切换，当切换到系统统计时刷新最近活动
watch(activeTab, (newTab) => {
  // 同步到路由查询参数，便于跳转回管理页时恢复当前子页
  try {
    router.replace({ query: { ...route.query, tab: newTab } })
  } catch (e) {
    // ignore replace errors
  }

  if (newTab === 'stats') {
    loadRecentActivities()
  } else if (newTab === 'discussions') {
    loadDiscussions()
  } else if (newTab === 'messages') {
    loadMessages()
  }
})

// 如果路由 query 的 tab 发生变化（比如用户通过浏览器后退/前进），同步到 activeTab
watch(() => route.query.tab, (newVal) => {
  if (newVal && String(newVal) !== activeTab.value) {
    activeTab.value = String(newVal)
  }
})

// 题目表格排序处理
const handleProblemSortChange = ({ prop, order }) => {
  if (order) {
    problemSortField.value = prop
    problemSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    problemSortField.value = ''
    problemSortOrder.value = ''
  }
  loadProblems()
}

// 加载题目列表
const loadProblems = async () => {
  loadingProblems.value = true
  try {
    const params = {}
    // 传递管理员 user_id，以便后端返回所有题目（包括保留ID题目）
    const userId = localStorage.getItem('userId')
    if (userId) params.user_id = userId
    if (problemSearch.value) params.search = problemSearch.value
    // 将标签数组转换为逗号分隔的字符串
    if (problemTagsArray.value.length > 0) {
      params.tags = problemTagsArray.value.join(',')
    }
    if (problemSortField.value) {
      params.sort_by = problemSortField.value
      params.sort_order = problemSortOrder.value
    }
    const response = await api.get('/problems', { params })
    problems.value = response.data
    // 如果前端指定了排序字段，确保在客户端也对数据进行排序（以保证列排序一致）
    if (problemSortField.value) {
      applyLocalSort(problems.value, problemSortField.value, problemSortOrder.value)
    }
  } catch (error) {
    ElMessage.error('加载题目失败')
  } finally {
    loadingProblems.value = false
  }
}

// 重置题目筛选条件
const resetProblemFilters = () => {
  problemSearch.value = ''
  problemTagsArray.value = []
  problemSortField.value = ''
  problemSortOrder.value = ''
  loadProblems()
}

const handleProblemSubmissionFilterChange = async (value) => {
  problemSubmissionFilterId.value = value
  submissionPage.value = 1
  await loadSubmissions()
}

// 加载所有题目标签
const loadProblemTags = async () => {
  try {
    // 传递管理员 user_id，以便获取所有题目的标签（包括保留ID题目）
    const userId = localStorage.getItem('userId')
    const params = userId ? { user_id: userId } : {}
    const response = await api.get('/problems', { params })
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
    allProblemTags.value = Array.from(tagsSet).sort()
  } catch (error) {
    console.error('加载标签失败', error)
  }
}

// 显示创建题目对话框
const showCreateProblem = () => {
  isEditMode.value = false
  problemForm.value = {
    title: '',
    description: '',
    input_format: '',
    output_format: '',
    sample_input: '',
    sample_output: '',
    time_limit: 1000,
    memory_limit: 262144,
    difficulty: 'easy',
    tags: '',
    visible: true
  }
  problemDialogVisible.value = true
}

// 编辑题目
const editProblem = (problem) => {
  isEditMode.value = true
  currentEditId.value = problem.problem_id
  problemForm.value = { ...problem }
  problemDialogVisible.value = true
}

// 保存题目
const saveProblem = async () => {
  try {
    const userId = localStorage.getItem('userId')
    if (isEditMode.value) {
      // 发送前确保 test_cases 为数组（兼容后端 Pydantic 校验）
      const payload = { ...problemForm.value }
      if (payload.test_cases && typeof payload.test_cases === 'string') {
        try {
          payload.test_cases = JSON.parse(payload.test_cases)
        } catch (e) {
          // 如果解析失败，置为空数组以避免 422
          payload.test_cases = []
        }
      }
      // 编辑时不可修改可见性：从 payload 中移除 visible 字段以防止被更新
      if (payload.hasOwnProperty('visible')) {
        delete payload.visible
      }
      await api.put(`/problems/${currentEditId.value}`, payload, {
        params: { user_id: userId }
      })
      ElMessage.success('题目更新成功')
    } else {
      const payload = { ...problemForm.value }
      if (payload.test_cases && typeof payload.test_cases === 'string') {
        try {
          payload.test_cases = JSON.parse(payload.test_cases)
        } catch (e) {
          payload.test_cases = []
        }
      }
      await api.post('/problems', payload, {
        params: { creator_id: userId }
      })
      ElMessage.success('题目创建成功')
    }
    problemDialogVisible.value = false
    loadProblems()
    loadRecentActivities() // 刷新最近活动
  } catch (error) {
    ElMessage.error(isEditMode.value ? '更新失败' : '创建失败')
  }
}

// 删除题目
const deleteProblem = async (problemId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个题目吗？', '警告', {
      type: 'warning'
    })
    const userId = localStorage.getItem('userId')
    await api.delete(`/problems/${problemId}`, {
      params: { user_id: userId }
    })
    ElMessage.success('删除成功')
    loadProblems()
    loadRecentActivities() // 刷新最近活动
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 用户表格排序处理
const handleUserSortChange = ({ prop, order }) => {
  if (order) {
    userSortField.value = prop
    userSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    userSortField.value = ''
    userSortOrder.value = ''
  }
  loadUsers()
}

// 加载用户列表
const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const params = {}
    if (userSearch.value) params.search = userSearch.value
    if (userSortField.value) {
      params.sort_by = userSortField.value
      params.sort_order = userSortOrder.value
    }
    
    const response = await api.get('/users', { params })
    users.value = response.data
    // 本地排序以支持对嵌套或后端不可排序字段的列排序
    if (userSortField.value) {
      applyLocalSort(users.value, userSortField.value, userSortOrder.value)
    }
    totalUsers.value = response.data.length
    ensurePageInRange(userPage, totalUsers.value)
  } catch (error) {
    ElMessage.error('加载用户失败')
  } finally {
    loadingUsers.value = false
  }
}

// 删除用户
const deleteUser = async (userId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个用户吗？', '警告', {
      type: 'warning'
    })
    const currentUserId = localStorage.getItem('userId')
    await api.delete(`/users/${userId}`, {
      params: { admin_id: currentUserId }
    })
    ElMessage.success('删除成功')
    loadUsers()
    loadRecentActivities() // 刷新活动日志
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 提交记录表格排序处理
const handleSubmissionSortChange = ({ prop, order }) => {
  if (order) {
    submissionSortField.value = prop
    submissionSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    submissionSortField.value = ''
    submissionSortOrder.value = ''
  }
  loadSubmissions()
}

// 分页切换处理
const onUserPageChange = (page) => {
  userPage.value = page
}

const onMessagePageChange = (page) => {
  messagePage.value = page
}

const onDiscussionPageChange = (page) => {
  discussionPage.value = page
}

const onSubmissionPageChange = (page) => {
  submissionPage.value = page
}

const resetSubmissionFilters = () => {
  submissionUserSearch.value = ''
  submissionSortField.value = ''
  submissionSortOrder.value = ''
  problemSubmissionFilterId.value = null
  submissionPage.value = 1
  loadSubmissions()
}

// 加载提交记录
const loadSubmissions = async () => {
  loadingSubmissions.value = true
  try {
    const params = {}
    if (submissionUserSearch.value) params.user_search = submissionUserSearch.value
    if (problemSubmissionFilterId.value) params.problem_id = problemSubmissionFilterId.value
    if (submissionSortField.value) {
      params.sort_by = submissionSortField.value
      params.sort_order = submissionSortOrder.value
    }
    
    const response = await api.get('/submissions', { params })
    submissions.value = response.data
    // 本地排序，支持对嵌套字段（如 user.username）排序
    if (submissionSortField.value) {
      applyLocalSort(submissions.value, submissionSortField.value, submissionSortOrder.value)
    }
    totalSubmissions.value = response.data.length
    ensurePageInRange(submissionPage, totalSubmissions.value)
  } catch (error) {
    ElMessage.error('加载提交记录失败')
  } finally {
    loadingSubmissions.value = false
  }
}

// 查看代码
const viewCode = (submission) => {
  currentCode.value = submission.code
  currentCodeLang.value = submission.language || ''
  codeDialogVisible.value = true
}

// 编辑提交记录
const editSubmission = (submission) => {
  submissionEditForm.value = {
    submission_id: submission.submission_id,
    status: submission.status,
    exec_time: submission.exec_time,
    exec_memory: submission.exec_memory
  }
  submissionEditDialogVisible.value = true
}

// 保存提交记录编辑
const saveSubmissionEdit = async () => {
  try {
    const { submission_id, ...updateData } = submissionEditForm.value
    await api.put(`/submissions/${submission_id}`, updateData)
    ElMessage.success('提交记录更新成功')
    submissionEditDialogVisible.value = false
    loadSubmissions()
    loadRecentActivities() // 刷新最近活动
  } catch (error) {
    ElMessage.error('更新提交记录失败')
  }
}

// 重测提交记录
const rejudgeSubmission = async (submissionId) => {
  try {
    await ElMessageBox.confirm(
      '确定要重新评测这条提交记录吗？将根据当前题目的最新测试点重新评测。',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 找到对应的提交记录，设置加载状态并把状态显示为评测中
    const submission = submissions.value.find(s => s.submission_id === submissionId)
    if (submission) {
      submission.rejudging = true
      submission.status = 'judging'
    }

    const userId = localStorage.getItem('userId')
    await api.post(`/submissions/${submissionId}/rejudge`, null, {
      params: { user_id: userId }
    })
    ElMessage.info('重测任务已提交，等待评测结果...')

    // 自动轮询该提交直到评测完成，然后刷新列表
    const finished = await pollSubmissionStatuses([submissionId], 2000, 120000)
    if (finished) {
      ElMessage.success('重测完成，结果已更新')
    } else {
      ElMessage.warning('重测可能仍在进行，已刷新列表。')
    }
    await loadSubmissions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重测失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    // 清除加载状态
    const submission = submissions.value.find(s => s.submission_id === submissionId)
    if (submission) {
      submission.rejudging = false
    }
  }
}

// 轮询一组提交，直到它们的 status 都不再是 'judging' 或超时
const pollSubmissionStatuses = async (ids, intervalMs = 2000, timeoutMs = 120000) => {
  const start = Date.now()
  const sleep = (ms) => new Promise(r => setTimeout(r, ms))
  try {
    while (Date.now() - start < timeoutMs) {
      const results = await Promise.all(ids.map(id => api.get(`/submissions/${id}`).then(r => r.data).catch(() => null)))
      const stillJudging = results.filter(r => r && r.status === 'judging').length
      if (stillJudging === 0) return true
      await sleep(intervalMs)
    }
  } catch (e) {
    console.warn('pollSubmissionStatuses error', e)
  }
  return false
}

// 删除提交记录
const deleteSubmission = async (submissionId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条提交记录吗？此操作不可恢复。',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const userId = localStorage.getItem('userId')
    await api.delete(`/submissions/${submissionId}`, {
      params: { user_id: userId }
    })
    ElMessage.success('提交记录删除成功')
    loadSubmissions()
    loadRecentActivities() // 刷新最近活动
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除提交记录失败')
    }
  }
}

// --- 批量重测相关 ---
const bulkDialogVisible = ref(false)
const bulkFilters = ref({ contest_id: null, problem_id: null, user_search: '' })
const bulkSubmissions = ref([])
const bulkSelected = ref([])
// 分页控制：在批量重测对话框中按页展示，避免内部滚动条
const bulkPage = ref(1)
const bulkPageSize = ref(10)
const bulkPageSubmissions = computed(() => {
  const start = (bulkPage.value - 1) * bulkPageSize.value
  return bulkSubmissions.value.slice(start, start + bulkPageSize.value)
})

const openBulkRejudgeDialog = async () => {
  bulkDialogVisible.value = true
  // 初始化筛选并加载默认提交（当前 submissions 列表的前几条）
  bulkFilters.value = { contest_id: null, problem_id: null, user_search: '' }
  bulkPage.value = 1
  await loadBulkSubmissions()
}

const loadBulkSubmissions = async () => {
  try {
    const params = {}
    if (bulkFilters.value.contest_id) params.contest_id = bulkFilters.value.contest_id
    if (bulkFilters.value.problem_id) params.problem_id = bulkFilters.value.problem_id
    if (bulkFilters.value.user_search) params.user_search = bulkFilters.value.user_search
    // 限制返回量以避免过大
    params.limit = 200
    const res = await api.get('/submissions', { params })
    bulkSubmissions.value = res.data
  } catch (e) {
    ElMessage.error('加载可重测提交失败')
    bulkSubmissions.value = []
  }
}

const onSubmissionSelectionChange = (selection) => {
  bulkSelected.value = selection
}

const confirmBulkRejudge = async () => {
  if (!bulkSelected.value || bulkSelected.value.length === 0) {
    ElMessage.warning('请先选择要重测的提交')
    return
  }
  try {
    await ElMessageBox.confirm(`确定要对选中的 ${bulkSelected.value.length} 条提交进行批量重测吗？`, '确认', { type: 'warning' })
    const ids = bulkSelected.value.map(s => s.submission_id)
    // 乐观更新主表中已显示的提交：标记为评测中并显示加载态
    ids.forEach(id => {
      const s = submissions.value.find(x => x.submission_id === id)
      if (s) {
        s.rejudging = true
        s.status = 'judging'
      }
    })
    const userId = localStorage.getItem('userId')
    const res = await api.post('/submissions/rejudge_bulk', { submission_ids: ids }, { params: { user_id: userId } })
    const processedIds = res.data.processed_ids || ids
    ElMessage.info(`批量重测任务已提交，共 ${processedIds.length} 条，正在等待结果...`)
    bulkDialogVisible.value = false
    // 自动轮询已处理的提交，等全部完成后刷新
    const finished = await pollSubmissionStatuses(processedIds, 2000, 180000)
    if (finished) {
      ElMessage.success(`批量重测完成，已更新 ${processedIds.length} 条提交`)
    } else {
      ElMessage.warning('部分重测可能仍在进行，已刷新提交列表')
    }
    await loadSubmissions()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量重测失败: ' + (e.response?.data?.detail || e.message))
  }
}

const resetBulkFilters = async () => {
  bulkFilters.value.user_search = ''
  bulkFilters.value.problem_id = null
  bulkFilters.value.contest_id = null
  bulkPage.value = 1
  await loadBulkSubmissions()
}

// 比赛表格排序处理
const handleContestSortChange = ({ prop, order }) => {
  if (order) {
    contestSortField.value = prop
    contestSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    contestSortField.value = ''
    contestSortOrder.value = ''
  }
  loadContests()
}

// 比赛管理函数
const loadContests = async () => {
  loadingContests.value = true
  try {
    const params = {}
    if (contestSearch.value) params.search = contestSearch.value
    if (contestSortField.value) {
      params.sort_by = contestSortField.value
      params.sort_order = contestSortOrder.value
    }
    
    const response = await api.get('/contests/', { params })
    contests.value = response.data
    // 如果后端没有按照我们请求的字段排序，前端再做一次本地排序以保证列排序一致
    if (contestSortField.value) {
      const dir = contestSortOrder.value === 'asc' ? 1 : -1
      contests.value.sort((a, b) => {
        const av = a[contestSortField.value] ?? ''
        const bv = b[contestSortField.value] ?? ''
        if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * dir
        if (av > bv) return 1 * dir
        if (av < bv) return -1 * dir
        return 0
      })
    }
  } catch (error) {
    ElMessage.error('加载比赛列表失败')
  } finally {
    loadingContests.value = false
  }
}

const showCreateContest = () => {
  isEditingContest.value = false
  contestForm.value = {
    contest_id: null,
    title: '',
    description: '',
    start_time: null,
    end_time: null
  }
  contestDialogVisible.value = true
}

const editContest = (contest) => {
  isEditingContest.value = true
  contestForm.value = {
    contest_id: contest.contest_id,
    title: contest.title,
    description: contest.description,
    start_time: new Date(contest.start_time),
    end_time: new Date(contest.end_time)
  }
  contestDialogVisible.value = true
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

    // 将时间转换为本地时间字符串（北京时间），避免时区转换问题
    const data = {
      title: contestForm.value.title,
      description: contestForm.value.description,
      start_time: formatDateTimeLocal(contestForm.value.start_time),
      end_time: formatDateTimeLocal(contestForm.value.end_time)
    }

    if (isEditingContest.value) {
      await api.put(`/contests/${contestForm.value.contest_id}?user_id=${creatorId}`, data)
      ElMessage.success('比赛更新成功')
    } else {
      await api.post(`/contests/?creator_id=${creatorId}`, data)
      ElMessage.success('比赛创建成功')
    }

    contestDialogVisible.value = false
    loadContests()
    loadRecentActivities() // 刷新活动日志
  } catch (error) {
    ElMessage.error(isEditingContest.value ? '更新比赛失败' : '创建比赛失败')
  }
}

const deleteContestAdmin = async (contestId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个比赛吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const userId = localStorage.getItem('userId')
    await api.delete(`/contests/${contestId}`, {
      params: { user_id: userId }
    })
    ElMessage.success('删除成功')
    loadContests()
    loadRecentActivities() // 刷新活动日志
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const manageContestProblems = async (contest) => {
  currentContestId.value = contest.contest_id
  try {
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${contest.contest_id}?user_id=${userId}`)
    currentContestProblems.value = response.data.problems || []
    contestProblemsDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载比赛题目失败')
  }
}

const addProblemToContest = async () => {
  if (!addContestProblemId.value) {
    ElMessage.warning('请输入题目ID')
    return
  }
  
  try {
    await api.post(`/contests/${currentContestId.value}/problems?problem_id=${addContestProblemId.value}`)
    ElMessage.success('添加成功')
    addContestProblemId.value = null
    
    // 重新加载题目列表
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${currentContestId.value}?user_id=${userId}`)
    currentContestProblems.value = response.data.problems || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '添加失败')
  }
}

const removeProblemFromContest = async (problemId) => {
  try {
    await api.delete(`/contests/${currentContestId.value}/problems/${problemId}`)
    ElMessage.success('移除成功')
    
    // 重新加载题目列表
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${currentContestId.value}?user_id=${userId}`)
    currentContestProblems.value = response.data.problems || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '移除失败')
  }
}

// 打开题目选择器
const openProblemSelector = async () => {
  problemSelectorVisible.value = true
  await loadAvailableProblems()
}

// 加载可用题目列表
const loadAvailableProblems = async () => {
  loadingAvailableProblems.value = true
  try {
    const userId = localStorage.getItem('userId')
    const params = {
      user_id: userId,
      skip: 0,
      limit: 100
    }
    
    if (problemSelectorSearch.value) {
      params.search = problemSelectorSearch.value
    }
    if (problemSelectorDifficulty.value) {
      params.difficulty = problemSelectorDifficulty.value
    }
    if (problemSelectorTagsArray.value.length > 0) {
      params.tags = problemSelectorTagsArray.value.join(',')
    }
    if (problemSelectorVisibility.value === 'visible') {
      params.visible = 'true'
    } else if (problemSelectorVisibility.value === 'invisible') {
      params.visible = 'false'
    }
    
    const response = await api.get('/problems', { params })
    availableProblems.value = response.data
  } catch (error) {
    ElMessage.error('加载题目列表失败')
  } finally {
    loadingAvailableProblems.value = false
  }
}

// 从题目选择器添加题目
const addProblemFromSelector = async (problemId) => {
  try {
    await api.post(`/contests/${currentContestId.value}/problems?problem_id=${problemId}`)
    ElMessage.success('添加成功')
    
    // 重新加载比赛题目列表
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${currentContestId.value}?user_id=${userId}`)
    currentContestProblems.value = response.data.problems || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '添加失败')
  }
}

// 重置题目选择器筛选条件
const resetProblemSelector = () => {
  problemSelectorSearch.value = ''
  problemSelectorDifficulty.value = ''
  problemSelectorTagsArray.value = []
  problemSelectorVisibility.value = ''
  loadAvailableProblems()
}

// 讨论表格排序处理
const handleDiscussionSortChange = ({ prop, order }) => {
  if (order) {
    discussionSortField.value = prop
    discussionSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    discussionSortField.value = ''
    discussionSortOrder.value = ''
  }
  loadDiscussions()
}

// 加载讨论列表
const loadDiscussions = async () => {
  loadingDiscussions.value = true
  try {
    const params = {
      message_type: 'topic'
    }
    if (discussionSearch.value) {
      params.search = discussionSearch.value
    }
    if (discussionSortField.value) {
      params.sort_by = discussionSortField.value
      params.sort_order = discussionSortOrder.value
    }
    
    const response = await api.get('/messages/admin/all', { params })
    discussions.value = response.data
    // 本地排序以支持对嵌套字段（如 problem.title 或 creator.username）排序
    if (discussionSortField.value) {
      applyLocalSort(discussions.value, discussionSortField.value, discussionSortOrder.value)
    }
    totalDiscussions.value = response.data.length
    ensurePageInRange(discussionPage, totalDiscussions.value)
  } catch (error) {
    ElMessage.error('加载讨论列表失败')
  } finally {
    loadingDiscussions.value = false
  }
}

// 查看讨论详情
const viewDiscussionDetail = (discussion) => {
  currentDiscussion.value = discussion
  discussionDetailDialogVisible.value = true
}

// 删除讨论
const deleteDiscussion = async (messageId) => {
  try {
    await ElMessageBox.confirm('确定要删除这条讨论吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const userId = localStorage.getItem('userId')
    await api.delete(`/messages/${messageId}`, {
      params: { user_id: userId }
    })
    ElMessage.success('删除成功')
    loadDiscussions()
    loadRecentActivities() // 刷新活动日志
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 私信表格排序处理
const handleMessageSortChange = ({ prop, order }) => {
  if (order) {
    messageSortField.value = prop
    messageSortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    messageSortField.value = ''
    messageSortOrder.value = ''
  }
  loadMessages()
}

// 加载私信列表
const loadMessages = async () => {
  loadingMessages.value = true
  try {
    const params = {
      message_type: 'private'
    }
    if (messageSearch.value) {
      params.search = messageSearch.value
    }
    if (messageSortField.value) {
      params.sort_by = messageSortField.value
      params.sort_order = messageSortOrder.value
    }
    
    const response = await api.get('/messages/admin/all', { params })
    messages.value = response.data
    // 本地排序，支持对发送人、接收人等嵌套字段的排序
    if (messageSortField.value) {
      applyLocalSort(messages.value, messageSortField.value, messageSortOrder.value)
    }
    totalMessages.value = response.data.length
    ensurePageInRange(messagePage, totalMessages.value)
  } catch (error) {
    ElMessage.error('加载私信列表失败')
  } finally {
    loadingMessages.value = false
  }
}

// 查看私信详情
const viewMessageDetail = (message) => {
  currentMessage.value = message
  messageDetailDialogVisible.value = true
}

// 查看用户详情
const viewUserDetail = (user) => {
  currentUserDetail.value = user
  userDetailDialogVisible.value = true
}

// 查看题目详情
const viewProblemDetail = async (problem) => {
  try {
    // 从API获取完整的题目信息（包括test_cases）
    const response = await api.get(`/problems/${problem.problem_id}`)
    currentProblemDetail.value = response.data
    problemDetailDialogVisible.value = true
  } catch (error) {
    console.error('加载题目详情失败:', error)
    ElMessage.error('加载题目详情失败')
  }
}

// 跳转到题目详情页面
// 跳转到题目详情页面
// 如果提供 messageId，会在 query 中带上 message_id，前端的 ProblemDetail 页可根据该参数滚动到对应讨论位置
const goToProblemDetail = (problemId, messageId = null) => {
  if (messageId) {
    router.push({ name: 'ProblemDetail', params: { id: problemId }, query: { message_id: messageId } })
  } else {
    router.push({ name: 'ProblemDetail', params: { id: problemId } })
  }
}

// 查看比赛详情
const viewContestDetail = async (contest) => {
  try {
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${contest.contest_id}?user_id=${userId}`)
    currentContestDetail.value = response.data
    contestDetailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取比赛详情失败')
  }
}

// 管理参赛用户
const manageContestParticipants = async (contest) => {
  try {
    currentManageContestId.value = contest.contest_id
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${contest.contest_id}?user_id=${userId}`)
    currentContestParticipants.value = response.data.participants || []
    participantsDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取参赛用户失败')
  }
}

// 显示添加参赛用户对话框
const showAddParticipantDialog = () => {
  selectedParticipantId.value = null
  availableUsers.value = []
  addParticipantDialogVisible.value = true
}

// 搜索用户
const searchUsers = async (query) => {
  if (!query) {
    availableUsers.value = []
    return
  }
  
  try {
    searchingUsers.value = true
    const response = await api.get('/users/', {
      params: { search: query, limit: 20 }
    })
    availableUsers.value = response.data
  } catch (error) {
    ElMessage.error('搜索用户失败')
  } finally {
    searchingUsers.value = false
  }
}

// 添加参赛用户
const addParticipant = async () => {
  if (!selectedParticipantId.value) {
    ElMessage.warning('请选择用户')
    return
  }
  
  try {
    await api.post(`/contests/${currentManageContestId.value}/register?user_id=${selectedParticipantId.value}`)
    ElMessage.success('添加成功')
    addParticipantDialogVisible.value = false
    // 重新加载参赛用户列表
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${currentManageContestId.value}?user_id=${userId}`)
    currentContestParticipants.value = response.data.participants || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '添加失败')
  }
}

// 移除参赛用户
const removeParticipant = async (userId) => {
  try {
    await ElMessageBox.confirm('确定要移除该用户吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.delete(`/contests/${currentManageContestId.value}/register/${userId}`)
    ElMessage.success('移除成功')
    // 重新加载参赛用户列表
    const adminId = localStorage.getItem('userId')
    const response = await api.get(`/contests/${currentManageContestId.value}?user_id=${adminId}`)
    currentContestParticipants.value = response.data.participants || []
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '移除失败')
    }
  }
}

// 删除私信
const deleteMessage = async (messageId) => {
  try {
    await ElMessageBox.confirm('确定要删除这条私信吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const userId = localStorage.getItem('userId')
    await api.delete(`/messages/${messageId}`, {
      params: { user_id: userId }
    })
    ElMessage.success('删除成功')
    loadMessages()
    loadRecentActivities() // 刷新活动日志
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 管理测试点
const manageTestCases = async (problem) => {
  currentProblemForTestCase.value = problem
  try {
    // 优先从独立的 test_case 表加载测试点（尝试包含隐藏点）
    // 如果当前会话没有查看隐藏测试点的权限，后端会返回 403；
    // 若该接口不存在或返回 404，也回退到读取 /problems/{id} 的 test_cases 字段（兼容旧数据）
    let testCases = []
    try {
      const response = await api.get(`/test-cases/problem/${problem.problem_id}`, { params: { include_hidden: true } })
      testCases = response.data || []
    } catch (err) {
      // 如果接口返回 404 或 403（无权限），尝试回退到 /problems/{id}
      if (err.response && (err.response.status === 404 || err.response.status === 403)) {
        const resp = await api.get(`/problems/${problem.problem_id}`)
        testCases = resp.data.test_cases || []
      } else {
        throw err
      }
    }
    // 保存原始 id 集合，用于检测删除
    originalTestCaseIds.value = testCases.filter(tc => tc.test_case_id).map(tc => tc.test_case_id)
    currentTestCases.value = Array.isArray(testCases) ? testCases.map((tc, idx) => ({
      // stable uuid id (tc.id) 和兼容的数组索引 test_case_id 都保留在本地状态
      id: tc.id,
      test_case_id: tc.test_case_id,
      input_data: tc.input_data || '',
      output_data: tc.output_data || '',
      score: tc.score ?? 10,
      is_sample: tc.is_sample ?? 0,
      order: tc.order ?? idx
    })) : []
    testCaseDialogVisible.value = true
  } catch (error) {
    console.error('加载测试点失败:', error)
    ElMessage.error('加载测试点失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 添加新测试点
const addNewTestCase = () => {
  currentTestCases.value.push({
    input_data: '',
    output_data: '',
    score: 10,
    is_sample: 0,
    order: currentTestCases.value.length,
    // 新增项没有 test_case_id
    test_case_id: undefined,
    id: undefined
  })
}

// 计算用于渲染的显示数组：当正在悬停时，在显示数组中插入一个占位项以提供视觉占位
const dragOverIndex = ref(null)
const dragOverPosition = ref(null) // 'before' | 'after'
const currentDragIndex = ref(null) // 存储被拖拽项在真实 currentTestCases 中的索引

const displayTestCases = computed(() => {
  // 如果没有悬停位置，直接返回当前真实数组的浅拷贝
  const arr = currentTestCases.value.slice()
  if (dragOverIndex.value === null || dragOverPosition.value === null) return arr

  // 计算在显示数组中的插入位置（以 displayIndex 表示）
  const displayInsert = dragOverIndex.value + (dragOverPosition.value === 'after' ? 1 : 0)
  const placeholder = { __placeholder: true }
  const newArr = arr.slice(0)
  newArr.splice(displayInsert, 0, placeholder)
  return newArr
})

// 将 displayIndex 映射为真实 currentTestCases 的索引；如果 displayIndex 指向占位，则返回 null
const displayIndexToReal = (displayIndex) => {
  const display = displayTestCases.value
  if (!display || displayIndex < 0 || displayIndex >= display.length) return null
  if (display[displayIndex].__placeholder) return null
  // 真实索引等于 display 中该位置之前的非占位项数量
  let count = 0
  for (let i = 0; i <= displayIndex; i++) {
    if (!display[i].__placeholder) count++
  }
  return count - 1
}

// 将 display 中的插入位置转换为真实数组的插入索引（displayInsert 可等于 display.length）
const displayInsertToRealInsert = (displayInsert) => {
  const display = displayTestCases.value
  // 真实插入索引为 display 中 insert 位置之前的非占位项数量
  let count = 0
  for (let i = 0; i < displayInsert && i < display.length; i++) {
    if (!display[i].__placeholder) count++
  }
  // 如果 displayInsert 指向数组末尾（大于等于 display.length），则 count 已是最终插入位置
  return count
}

const onDragStart = (event, displayIndex) => {
  const realIndex = displayIndexToReal(displayIndex)
  if (realIndex === null) return
  currentDragIndex.value = realIndex
  try { event.dataTransfer.effectAllowed = 'move' } catch (e) {}
}

const onDragOver = (event, displayIndex) => {
  // 当拖动到某一行时，按照相对垂直位置决定是插入在目标之前还是之后
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

  // 计算 displayInsert（占位所在的 display 索引）
  const displayInsert = dragOverIndex.value !== null && dragOverPosition.value !== null ?
    (dragOverIndex.value + (dragOverPosition.value === 'after' ? 1 : 0)) : (displayIndex + 1)

  // 将 displayInsert 转换为真实数组的插入索引
  const insertIndex = Math.max(0, Math.min(displayInsertToRealInsert(displayInsert), currentTestCases.value.length))

  // 从真实数组中移除并插入
  const from = currentDragIndex.value
  const item = currentTestCases.value.splice(from, 1)[0]
  // 调整插入索引，如果移除项在插入点之前则需要 -1
  let finalInsert = insertIndex
  if (from < insertIndex) finalInsert = insertIndex - 1
  finalInsert = Math.max(0, Math.min(finalInsert, currentTestCases.value.length))
  currentTestCases.value.splice(finalInsert, 0, item)
  reindexCurrentTestCases()
  currentDragIndex.value = null
  dragOverIndex.value = null
  dragOverPosition.value = null
}
const reindexCurrentTestCases = () => {
  currentTestCases.value.forEach((tc, idx) => {
    tc.order = idx
  })
}

// 用于 el-table 的行 class，显示上/下插入线并高亮拖拽中的行
const testCaseRowClass = (row, rowIndex) => {
  const classes = []
  // 如果该行是占位，不高亮为拖拽项
  if (!row.__placeholder) {
    const realIdx = currentTestCases.value.indexOf(row)
    if (realIdx === currentDragIndex.value) classes.push('dragging-row')
  }
  if (dragOverIndex.value !== null && dragOverPosition.value !== null && rowIndex === dragOverIndex.value) {
    classes.push(dragOverPosition.value === 'before' ? 'drag-over-before' : 'drag-over-after')
  }
  return classes.join(' ')
}

// 删除测试点（接受 displayIndex，需要映射为真实索引）
const removeTestCase = (displayIndex) => {
  const realIndex = displayIndexToReal(displayIndex)
  if (realIndex === null) return
  const removed = currentTestCases.value.splice(realIndex, 1)[0]
  if (removed && removed.test_case_id) {
    removedTestCaseIds.value.push(removed.test_case_id)
  }
}

// 保存测试点（原子化替换整个 test_cases 列表，避免索引位移问题）
const saveTestCases = async () => {
  try {
    const problemId = currentProblemForTestCase.value.problem_id

    // 构建要写入的最终数组（确保字段类型正确）
    const payload = currentTestCases.value.map((tc, idx) => ({
      // 包含可选的稳定 id（若存在则发送，后端会保留或为新项生成）
      id: tc.id,
      input_data: tc.input_data || '',
      output_data: tc.output_data || '',
      score: Number(tc.score ?? 0),
      is_sample: Number(tc.is_sample ?? 0),
      order: Number(tc.order != null ? tc.order : idx)
    }))

    // 本地简单校验总分，必须严格等于100
    const total = payload.reduce((s, t) => s + (Number(t.score) || 0), 0)
    if (total !== 100) {
      ElMessage.error('测试点总分必须等于100分（当前总分：' + total + '）')
      return
    }

    // 调用后端的原子替换接口（PUT /test-cases/sync?problem_id=...）
    await api.put('/test-cases/sync', payload, { params: { problem_id: problemId } })

    ElMessage.success('测试点保存成功')
    testCaseDialogVisible.value = false
    // 清理临时删除列表
    removedTestCaseIds.value = []

    // 重新加载题目列表和详情，以反映最新状态
    loadProblems()
    if (currentProblemDetail.value && currentProblemDetail.value.problem_id === problemId) {
      const resp = await api.get(`/problems/${problemId}`)
      currentProblemDetail.value = resp.data
    }
  } catch (error) {
    console.error('保存测试点失败:', error)
    ElMessage.error('保存测试点失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 查看提交详情
const viewSubmissionDetail = async (submission, isAdmin = false) => {
  try {
    showTestCaseIO.value = isAdmin
    const userId = localStorage.getItem('userId')
    const response = await api.get(`/submissions/${submission.submission_id}/detail`, {
      params: { user_id: userId }
    })
    currentSubmissionDetail.value = response.data
    submissionDetailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载提交详情失败')
  }
}

// 加载统计数据
const loadStats = async () => {
  try {
    // 加载统计数据
    const [usersRes, problemsRes, submissionsRes, contestsRes] = await Promise.all([
      api.get('/users'),
      api.get('/problems'),
      api.get('/submissions'),
      api.get('/contests/')
    ])
    
    stats.value = {
      totalUsers: usersRes.data.length,
      totalProblems: problemsRes.data.length,
      totalSubmissions: submissionsRes.data.length,
      totalContests: contestsRes.data.length
    }

    // 加载评测线程池统计
    try {
      const judgeStatsRes = await api.get('/submissions/worker_stats')
      const js = judgeStatsRes.data || {}
      stats.value.judge_running = js.running || 0
      stats.value.judge_pending = js.pending || 0
      stats.value.judge_max_workers = js.max_workers || 0
    } catch (e) {
      // ignore judge stats errors
      stats.value.judge_running = 0
      stats.value.judge_pending = 0
      stats.value.judge_max_workers = 0
    }

    // 加载最近活动（最近的提交记录）
    loadRecentActivities()
  } catch (error) {
    ElMessage.error('加载统计数据失败')
  }
}

// 加载最近活动
const loadRecentActivities = async () => {
  try {
    const response = await api.get('/activity-logs/', {
      params: {
        limit: 20
      }
    })
    
    recentActivities.value = response.data.map(log => {
      return {
        id: log.log_id,
        content: log.description,
        time: log.created_at
      }
    })
  } catch (error) {
    console.error('加载最近活动失败:', error)
    recentActivities.value = []
  }
}

// 工具函数
const getDifficultyType = (difficulty) => {
  const types = {
    easy: 'success',
    medium: 'warning',
    hard: 'danger'
  }
  return types[difficulty] || ''
}

const getDifficultyText = (difficulty) => {
  const texts = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return texts[difficulty] || difficulty
}

// 点击 Admin 页的标签时，将其加入筛选并刷新题目列表（与题库页行为一致）
const addTagFilter = (tag) => {
  if (!tag) return
  // 去重并加入
  if (!problemTagsArray.value.includes(tag)) {
    problemTagsArray.value.push(tag)
  }
  // 触发重新加载题目（会把 tags 数组转为逗号字符串）
  loadProblems()
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
    wrong_answer: '错误',
    time_limit_exceeded: '超时',
    runtime_error: '运行错误'
  }
  return texts[status] || status
}

// 通用本地排序器：支持简单字段和常见的嵌套字段（如 creator.username / problem.title / user.username）
const applyLocalSort = (arr, field, order) => {
  if (!arr || !field) return
  const dir = order === 'asc' ? 1 : -1

  const getVal = (item) => {
    try {
      switch (field) {
        case 'creator_name':
        case 'creator.username':
          return (item.creator && item.creator.username) ? item.creator.username : ''
        case 'problem_title':
          return (item.problem && item.problem.title) ? item.problem.title : ''
        case 'recipients':
          // 多接收人时按用户名拼接比较
          if (item.recipients && item.recipients.length) {
            return item.recipients.map(r => r.username || '').join(',')
          }
          return ''
        case 'difficulty':
          // 自定义难度排序：easy < medium < hard
          const map = { easy: 0, medium: 1, hard: 2 }
          return map[item.difficulty] ?? (typeof item.difficulty === 'string' ? item.difficulty : 0)
        case 'username':
          return item.username ?? (item.user && item.user.username) ?? (item.creator && item.creator.username) ?? ''
        case 'user.username':
          return (item.user && item.user.username) ? item.user.username : ''
        case 'title':
          return item.title ?? ''
        case 'content':
          return item.content ?? ''
        case 'created_at':
          return item.created_at ? new Date(item.created_at).getTime() : 0
        case 'submission_id':
          return item.submission_id ?? item.submissionId ?? 0
        case 'rating':
          return item.rating ?? 0
        default:
          // 支持点号访问，比如 "user.username"
          if (field.includes('.')) {
            return field.split('.').reduce((o, k) => (o ? o[k] : undefined), item) ?? ''
          }
          return item[field] ?? ''
      }
    } catch (e) {
      return ''
    }
  }

  arr.sort((a, b) => {
    const va = getVal(a)
    const vb = getVal(b)
    // 数字比较
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    const sa = String(va).toLowerCase()
    const sb = String(vb).toLowerCase()
    if (sa < sb) return -1 * dir
    if (sa > sb) return 1 * dir
    return 0
  })
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 将 Date 对象格式化为本地时间字符串（用于发送到后端）
// 格式: YYYY-MM-DD HH:mm:ss
const formatDateTimeLocal = (date) => {
  if (!date) return null
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
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
</script>

<style scoped>
.admin-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
  text-align: center;
}

.header-card h2 {
  margin: 0 0 10px 0;
  color: #409eff;
}

.header-card p {
  margin: 0;
  color: #909399;
}

.admin-tabs {
  min-height: 600px;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tab-header h3 {
  margin: 0;
}

/* 统计卡片 */
.stats-container {
  padding: 20px;
}

.stat-card {
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
}

.user-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.problem-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.submission-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.contest-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
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

/* 拖拽时的视觉效果 */
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
tr.drag-over-before td::before {
  top: 0;
}
tr.drag-over-after td::after {
  bottom: 0;
}

@keyframes slide-highlight {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}

/* 兼容较老版本的表格渲染：额外提供边框和背景 */
.drag-over-before td { border-top: 3px solid #409eff; background: rgba(64,158,255,0.03); }
.drag-over-after td { border-bottom: 3px solid #409eff; background: rgba(64,158,255,0.03); }

/* 占位行样式，用于在拖拽时显示平滑过渡的空白行 */
.drag-placeholder {
  height: 48px; /* 与表格行高度接近 */
  background: rgba(64,158,255,0.06);
  border: 1px dashed rgba(64,158,255,0.25);
  border-radius: 4px;
  transition: height 180ms ease, opacity 180ms ease, transform 180ms ease;
  opacity: 0.95;
}

.drag-placeholder::before {
  content: '';
  display: block;
  height: 100%;
}

.stat-content {
  padding: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

/* 代码查看器 */
.code-viewer {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  max-height: 500px;
  overflow: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
}
</style>
