import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
})

// Request interceptor — attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — unified error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      const detail = data?.detail || data?.error || '未知錯誤'

      if (status === 401) {
        localStorage.removeItem('token')
        router.push('/login')
        ElMessage.error('登入已過期，請重新登入')
      } else if (status === 403) {
        ElMessage.error(`權限不足：${detail}`)
      } else if (status === 404) {
        ElMessage.error(`找不到資源：${detail}`)
      } else if (status === 413) {
        ElMessage.error('檔案過大')
      } else if (status === 422) {
        ElMessage.error(`參數錯誤：${detail}`)
      } else if (status >= 500) {
        ElMessage.error('伺服器錯誤，請稍後再試')
      } else {
        ElMessage.error(detail)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('連線逾時，請檢查網路')
    } else {
      ElMessage.error('網路錯誤，無法連線到伺服器')
    }
    return Promise.reject(error)
  }
)

export default api
