import { defineStore } from 'pinia'
import { loginApi, getMeApi, logoutApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),
  getters: {
    isLoggedIn: state => !!state.token,
    isAdmin: state => state.user?.role === 'admin',
    username: state => state.user?.username || '未登录',
    roleName: state => state.user?.role === 'admin' ? '系统管理员' : '普通员工'
  },
  actions: {
    async login(loginForm) {
      const res = await loginApi(loginForm)
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      return res
    },
    async fetchUserInfo() {
      if (!this.token) return null
      try {
        const user = await getMeApi()
        this.user = user
        localStorage.setItem('user', JSON.stringify(user))
        return user
      } catch (err) {
        this.logout()
        throw err
      }
    },
    async logout() {
      try {
        if (this.token) {
          await logoutApi()
        }
      } catch (e) {
        // 忽略退出接口的报错
      } finally {
        this.token = ''
        this.user = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
  }
})
