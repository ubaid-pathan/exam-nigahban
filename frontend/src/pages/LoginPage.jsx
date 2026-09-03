import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/apiError'
import { LockIcon, PersonIcon } from '../components/admin/icons'

export default function LoginPage() {
  const { isAuthenticated, user, login } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Always the role's own home route -- never a location.state.from carried
  // over from an earlier, unrelated redirect. A student who first tried an
  // admin URL while signed out arrives here with
  // state.from.pathname === "/admin/...": honoring that blindly would send
  // a successfully-authenticated student straight back to the admin URL,
  // which RequireRole then correctly rejects, landing them on
  // /unauthorized right after a successful login. Both roles now redirect
  // the same, simple way, matching how the admin branch already worked.
  if (isAuthenticated) {
    if (user.role === 'student') {
      return <Navigate to="/student/exams" replace />
    }
    return <Navigate to="/admin" replace />
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const me = await login(username, password)
      if (me.role === 'student') {
        navigate('/student/exams', { replace: true })
      } else {
        navigate('/admin', { replace: true })
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to log in. Please try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light px-3">
      <div className="card shadow-sm" style={{ width: '100%', maxWidth: '340px' }}>
        <div className="card-body p-4">
          <h1 className="h4 mb-1 text-center">Exam Nigahban</h1>
          <p className="text-muted text-center mb-4">Sign in to continue</p>

          {error && (
            <div className="alert alert-danger py-2" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-3">
              <label htmlFor="username" className="form-label">
                Username
              </label>
              <div className="form-icon-group">
                <PersonIcon width={18} height={18} className="form-icon-group__icon" />
                <input
                  id="username"
                  type="text"
                  className="form-control ps-5"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
            </div>
            <div className="mb-4">
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <div className="form-icon-group">
                <LockIcon width={18} height={18} className="form-icon-group__icon" />
                <input
                  id="password"
                  type="password"
                  className="form-control ps-5"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
              {submitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
