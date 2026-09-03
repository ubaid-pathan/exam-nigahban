import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '../api/auth'
import { TOKEN_KEY, UNAUTHORIZED_EVENT } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // login() already fetches and sets the current user itself -- it has to,
  // so it can return that user synchronously to its caller for role-based
  // routing. Set to true right before login() changes `token`, so the
  // effect below (whose job is hydrating `user` from a token already
  // sitting in localStorage on a cold page load/refresh) knows to skip the
  // redundant GET /api/auth/me and loading flicker it would otherwise
  // trigger for a token change login() already resolved. Without this,
  // every login fires two concurrent fetches and toggles `loading`
  // true -> false again after the user is already authenticated, which
  // unmounts and remounts every protected layout an extra, avoidable time
  // -- for AdminLayout, that means an extra, avoidable WebSocket connection.
  const skipNextTokenEffect = useRef(false)

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    if (skipNextTokenEffect.current) {
      skipNextTokenEffect.current = false
      return undefined
    }

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
    // The flag is set synchronously, immediately before the one setToken()
    // call, with no `await` between them -- the effect above is guaranteed
    // to see it as true when it reacts to this exact `token` change.
    skipNextTokenEffect.current = true
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
