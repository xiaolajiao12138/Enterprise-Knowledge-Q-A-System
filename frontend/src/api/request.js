import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 60000 // 大模型问答和上传可能需要较长时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    let msg = '网络请求失败，请稍后重试'
    if (error.response) {
      const data = error.response.data
      msg = (data && data.detail) || msg

      if (error.response.status === 401) {
        ElMessage.error(msg || '登录凭据已过期，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      if (error.response.status === 403) {
        ElMessage.warning(msg || '您没有权限执行此操作')
        return Promise.reject(error)
      }
    }

    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default service
