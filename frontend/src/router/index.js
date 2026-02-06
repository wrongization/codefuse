import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Problems from '../views/Problems.vue'
import ProblemDetail from '../views/ProblemDetail.vue'
import Submissions from '../views/Submissions.vue'
import Contests from '../views/Contests.vue'
import ContestDetail from '../views/ContestDetail.vue'
import Admin from '../views/Admin.vue'
import Profile from '../views/Profile.vue'
import UserDetail from '../views/UserDetail.vue'
import TestCaseManager from '../views/TestCaseManager.vue'
import Messages from '../views/Messages.vue'
import Friends from '../views/Friends.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/problems',
    name: 'Problems',
    component: Problems
  },
  {
    path: '/problems/:id',
    name: 'ProblemDetail',
    component: ProblemDetail
  },
  {
    path: '/problems/:id/test-cases',
    name: 'TestCaseManager',
    component: TestCaseManager,
    meta: { requiresAuth: true }
  },
  {
    path: '/submissions',
    name: 'Submissions',
    component: Submissions
  },
  {
    path: '/contests',
    name: 'Contests',
    component: Contests
  },
  {
    path: '/contests/:id',
    name: 'ContestDetail',
    component: ContestDetail
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin,
    meta: { requiresAdmin: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  },
  {
    path: '/users/:id',
    name: 'UserDetail',
    component: UserDetail
  },
  {
    path: '/messages',
    name: 'Messages',
    component: Messages,
    meta: { requiresAuth: true }
  },
  {
    path: '/friends',
    name: 'Friends',
    component: Friends,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：检查管理员权限
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAdmin) {
    const userRole = localStorage.getItem('userRole')
    if (userRole !== 'admin') {
      // 非管理员访问管理页面，重定向到首页
      next('/')
      return
    }
  }
  next()
})

export default router
