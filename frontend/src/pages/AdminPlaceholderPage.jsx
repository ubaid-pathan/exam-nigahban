import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// The admin dashboard is out of scope for this milestone (student examination
// frontend only). This page exists so an administrator login has somewhere
// to land instead of a dead end, until the admin dashboard milestone is built.
export default function AdminPlaceholderPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="d-flex align-items-center justify-content-center min-vh-100">
      <div className="text-center" style={{ maxWidth: '420px' }}>
        <h1 className="h4 mb-2">Welcome, {user?.username}</h1>
        <p className="text-muted mb-4">
          The administrator dashboard has not been built yet. It will be delivered in a
          future milestone. In the meantime, admin management is available via the API.
        </p>
        <button type="button" className="btn btn-outline-secondary" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </div>
  )
}
