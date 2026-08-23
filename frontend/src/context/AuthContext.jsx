import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '../api/auth'
import { TOKEN_KEY, UNAUTHORIZED_EVENT } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadCurrentUser() {
      if (!token) {
        setLoading(false)
        return
      }
      setLoading(true)
      try {
        const me = await fetchCurrentUser()
        if (!cancelled) {
          setUser(me)
        }
      } catch {
        if (!cancelled) {
          clearAuth()
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadCurrentUser()
    return () => {
      cancelled = true
    }
  }, [token, clearAuth])

  useEffect(() => {
    const handleUnauthorized = () => clearAuth()
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [clearAuth])

  const login = useCallback(async (username, password) => {
    const { access_token: accessToken } = await loginRequest(username, password)
    localStorage.setItem(TOKEN_KEY, accessToken)
    setToken(accessToken)
    const me = await fetchCurrentUser()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } catch {
      // Logout is best-effort server-side; local session is cleared regardless.
    }
    clearAuth()
  }, [clearAuth])

  const value = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
