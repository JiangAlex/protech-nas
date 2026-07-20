import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)

      const res = await api.post('/api/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      this.token = res.data.access_token
      localStorage.setItem('token', this.token)
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
    loadToken() {
      this.token = localStorage.getItem('token') || ''
    },
  },
})
