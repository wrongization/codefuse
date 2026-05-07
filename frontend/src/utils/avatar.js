/**
 * 头像工具函数
 * 用于处理头像 URL 并避免浏览器缓存
 */

import { ref } from 'vue'
import api from '../api'

// 全局头像时间戳缓存
export const avatarTimestamps = ref({})

/**
 * 构建带时间戳的头像 URL，避免浏览器缓存
 * @param {string} avatarPath - 头像路径
 * @param {number} userId - 用户ID
 * @returns {string} 完整的头像 URL
 */
export const buildAvatarUrl = (avatarPath, userId) => {
  if (!avatarPath) return ''
  if (avatarPath.startsWith('http')) return avatarPath
  const ts = avatarTimestamps.value[userId] || ''
  return `${api.defaults.baseURL}${avatarPath}${ts ? `?t=${ts}` : ''}`
}

/**
 * 更新指定用户的头像时间戳
 * @param {number|Array<number>} userIds - 单个用户ID或用户ID数组
 */
export const updateAvatarTimestamp = (userIds) => {
  const now = Date.now()
  if (Array.isArray(userIds)) {
    userIds.forEach(id => {
      if (id) avatarTimestamps.value[id] = now
    })
  } else if (userIds) {
    avatarTimestamps.value[userIds] = now
  }
}

/**
 * 批量更新多个用户的头像时间戳
 * @param {Array<Object>} users - 用户对象数组，每个对象需包含 user_id
 */
export const updateAvatarTimestampsForUsers = (users) => {
  const now = Date.now()
  users.forEach(user => {
    if (user?.user_id) {
      avatarTimestamps.value[user.user_id] = now
    }
  })
}

/**
 * 刷新所有头像时间戳（强制所有头像重新加载）
 */
export const refreshAllAvatarTimestamps = () => {
  const now = Date.now()
  Object.keys(avatarTimestamps.value).forEach(userId => {
    avatarTimestamps.value[userId] = now
  })
}
