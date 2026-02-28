import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token on each request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 — redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password })

// Admin endpoints
export const getUsers = (params?: object) => api.get('/admin/users', { params })
export const getUser = (id: string) => api.get(`/admin/users/${id}`)
export const updateUser = (id: string, data: object) => api.put(`/admin/users/${id}`, data)
export const getSystemStats = () => api.get('/admin/users/stats')
export const getAdminLogs = () => api.get('/admin/logs')
export const getAllPositions = (params?: object) => api.get('/admin/positions', { params })

// Market
export const getAllTickers = () => api.get('/market/tickers')
export const getTicker = (symbol: string) => api.get(`/market/ticker/${symbol}`)
export const getKlines = (symbol: string, interval = '1h', limit = 200) =>
  api.get(`/market/klines/${symbol}`, { params: { interval, limit } })
