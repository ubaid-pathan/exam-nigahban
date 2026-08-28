import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { TOKEN_KEY } from '../api/client'
import { connectAdminAlertsSocket } from '../api/adminAlertsSocket'
import LiveAlertIndicator from '../components/LiveAlertIndicator'

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [latestAlert, setLatestAlert] = useState(null)

  // AdminLayout stays mounted across every /admin/* page, so this is the
  // one place a single persistent connection makes sense -- opened only
  // for an authenticated admin with a real token, closed on cleanup
  // (covers unmount, logout, and React StrictMode's dev-mode double
  // mount/cleanup pass alike, since each effect run closes its own
  // `socket` instance rather than a shared one).
  useEffect(() => {
    if (!user || user.role !== 'admin') {
      return undefined
    }

    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      return undefined
    }

    const socket = connectAdminAlertsSocket({
      token,
      onMessage: (message) => setLatestAlert(message),
      onError: () => {
        // Best-effort real-time channel: a connection error must never
        // break the admin UI. Automatic reconnection is a later phase.
      },
    })

    return () => {
      socket?.close()
    }
  }, [user])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const navLinkClass = ({ isActive }) =>
    `nav-link${isActive ? ' active fw-semibold' : ''}`

  return (
    <div className="app-shell">
      <nav className="navbar navbar-expand navbar-dark bg-dark">
        <div className="container">
          <span className="navbar-brand mb-0">Exam Nigahban</span>
          <div className="navbar-nav me-auto flex-row gap-2">
            <NavLink to="/admin" end className={navLinkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/admin/monitoring" className={navLinkClass}>
              Monitoring Events
            </NavLink>
            <NavLink to="/admin/exams" className={navLinkClass}>
              Exams
            </NavLink>
            <NavLink to="/admin/audit" className={navLinkClass}>
              Audit History
            </NavLink>
          </div>
          <div className="d-flex align-items-center gap-3">
            <LiveAlertIndicator latestAlert={latestAlert} />
            {user && (
              <span className="text-light small">
                {user.username} <span className="badge text-bg-primary ms-1">Admin</span>
              </span>
            )}
            <button
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="app-main">
        <div className="container">
          <Outlet context={{ latestAlert }} />
        </div>
      </main>
    </div>
  )
}
