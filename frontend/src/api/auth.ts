import { apiFetch } from './client'
import type { User } from '../types'

export const authApi = {
  getMe(): Promise<User> {
    return apiFetch<User>('/api/v1/auth/me')
  },

  getLoginUrl(provider: 'google' | 'github'): string {
    const base = import.meta.env.VITE_API_URL || window.location.origin
    return `${base}/api/v1/auth/login/${provider}`
  },
}
