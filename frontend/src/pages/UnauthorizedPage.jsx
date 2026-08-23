import { Link } from 'react-router-dom'

export default function UnauthorizedPage() {
  return (
    <div className="d-flex align-items-center justify-content-center min-vh-100">
      <div className="text-center">
        <h1 className="h4 mb-2">Access Restricted</h1>
        <p className="text-muted mb-4">
          Your account does not have permission to view this page.
        </p>
        <Link to="/login" className="btn btn-primary">
          Back to Login
        </Link>
      </div>
    </div>
  )
}
