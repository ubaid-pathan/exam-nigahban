import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

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
          </div>
          <div className="d-flex align-items-center gap-3">
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
          <Outlet />
        </div>
      </main>
    </div>
  )
}
