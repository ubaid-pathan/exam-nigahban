import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

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
          <div className="d-flex align-items-center gap-3 ms-auto">
            {user && (
              <span className="text-light small">
                {user.username} <span className="badge text-bg-secondary ms-1">Student</span>
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
