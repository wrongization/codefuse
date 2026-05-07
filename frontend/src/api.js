import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 是否正在处理401登出（防止多次触发）
let isLoggingOut = false

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401 && !isLoggingOut) {
      isLoggingOut = true
      console.warn('认证失败，自动登出')
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      // 使用setTimeout确保当前请求完成后再重定向
      setTimeout(() => {
        window.location.href = '/'
        isLoggingOut = false
      }, 100)
    }
    return Promise.reject(error)
  }
)

export default api
