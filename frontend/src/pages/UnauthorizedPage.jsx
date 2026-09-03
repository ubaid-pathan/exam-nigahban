import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DashboardIcon, ShieldAlertIcon } from '../components/admin/icons'

// Reached in two distinct ways: (1) RequireRole redirects an authenticated
// user whose role doesn't match the route they tried -- the normal,
// expected case, handled by the role-aware button below; (2) this route
// isn't wrapped in ProtectedRoute, so it's also directly reachable by URL
// while signed out, which the `user`-less fallback below covers by sending
// them to the normal Login page instead, without exposing anything else.
export default function UnauthorizedPage() {
  const { user } = useAuth()

  return (
    <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light px-3">
      <div className="text-center" style={{ maxWidth: '380px' }}>
        <div className="text-primary mb-3">
          <ShieldAlertIcon width={48} height={48} />
        </div>
        <h1 className="h4 mb-2">Access Restricted</h1>
        <p className="text-muted mb-4">
          Your account does not have permission to view this page.
        </p>
        {user ? (
          <Link
            to={user.role === 'admin' ? '/admin' : '/student/exams'}
            className="btn btn-primary d-inline-flex align-items-center gap-2"
          >
            <DashboardIcon width={16} height={16} />
            Go to {user.role === 'admin' ? 'Admin' : 'Student'} Dashboard
          </Link>
        ) : (
          <Link to="/login" className="btn btn-primary">
            Back to Login
          </Link>
        )}
      </div>
    </div>
  )
}
