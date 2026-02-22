import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authApi } from './api/auth'
import type { User } from './types'

interface AuthContextValue {
  user: User | null
  token: string | null
  loading: boolean
  login: (token: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  isAdmin: boolean
  isOrganizer: boolean
  canManageEvents: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async (t: string) => {
    try {
      localStorage.setItem('access_token', t)
      const me = await authApi.getMe()
      setUser(me)
      setToken(t)
    } catch {
      localStorage.removeItem('access_token')
      setUser(null)
      setToken(null)
    }
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) {
      fetchUser(stored).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [fetchUser])

  const login = useCallback(
    async (newToken: string) => {
      setLoading(true)
      await fetchUser(newToken)
      setLoading(false)
    },
    [fetchUser],
  )

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setUser(null)
    setToken(null)
  }, [])

  const isAuthenticated = !!user
  const isAdmin = user?.role === 'ADMIN'
  const isOrganizer = user?.role === 'ORGANIZER' || isAdmin
  const canManageEvents = isOrganizer

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        isAuthenticated,
        isAdmin,
        isOrganizer,
        canManageEvents,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
