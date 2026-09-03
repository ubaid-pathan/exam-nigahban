import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LogoutIcon } from '../components/admin/icons'

export default function StudentLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <nav className="navbar navbar-expand navbar-dark bg-dark">
        <div className="container">
          <span className="navbar-brand mb-0">Exam Nigahban</span>
          {/* Same structure/spacing/sizing as AdminLayout's header account
              area (username, role badge, Logout as three flex siblings on
              one gap-2 row) -- but keeping the light-on-dark button/text
              variants (btn-outline-light / text-light) rather than
              AdminLayout's btn-outline-secondary, since this navbar stays
              dark (bg-dark, unchanged) while the admin header is a light
              surface; reusing the admin header's dark-on-light classes
              here would be nearly invisible against this background. */}
          {user && (
            <div className="student-header__account d-flex align-items-center gap-2 ms-auto">
              <span className="student-header__username text-light text-truncate small">
                {user.username}
              </span>
              <span className="badge text-bg-secondary">Student</span>
              <button
                type="button"
                className="btn btn-outline-light btn-sm d-flex align-items-center gap-1"
                onClick={handleLogout}
              >
                <LogoutIcon width={14} height={14} />
                Logout
              </button>
            </div>
          )}
        </div>
      </nav>
      <main className="app-main">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
