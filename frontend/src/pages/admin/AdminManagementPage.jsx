import { useCallback, useEffect, useState } from 'react'
import { listAdmins, updateAdminStatus } from '../../api/admins'
import { useAuth } from '../../context/AuthContext'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'

const PAGE_SIZE = 10

function statusBadgeClass(isActive) {
  return isActive ? 'text-bg-success' : 'text-bg-warning'
}

function statusLabel(isActive) {
  return isActive ? 'Active' : 'Inactive'
}

export default function AdminManagementPage() {
  const { user: currentAdmin } = useAuth()

  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ total: 0, total_pages: 0 })

  const [pendingAction, setPendingAction] = useState(null)
  const [actionError, setActionError] = useState('')
  const [actionSubmitting, setActionSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listAdmins({ search, page, pageSize: PAGE_SIZE })
      setAdmins(data.items)
      setPagination({ total: data.total, total_pages: data.total_pages })
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load administrators right now.'))
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => {
    load()
  }, [load])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setSearch(searchInput.trim())
    setPage(1)
  }

  const handleClearSearch = () => {
    setSearchInput('')
    setSearch('')
    setPage(1)
  }

  const handlePrevious = () => setPage((current) => Math.max(1, current - 1))
  const handleNext = () =>
    setPage((current) => (current < pagination.total_pages ? current + 1 : current))

  const openPendingAction = (type, admin) => {
    setActionError('')
    setPendingAction({ type, admin })
  }

  const closePendingAction = () => {
    if (actionSubmitting) return
    setPendingAction(null)
    setActionError('')
  }

  const handleConfirmAction = async () => {
    if (!pendingAction) return
    setActionSubmitting(true)
    setActionError('')
    try {
      const activate = pendingAction.type === 'activate'
      await updateAdminStatus(pendingAction.admin.id, activate)
      setSuccessMessage(
        activate
          ? 'Administrator activated successfully.'
          : 'Administrator deactivated successfully.',
      )
      setPendingAction(null)
      await load()
    } catch (err) {
      // Business-rule violations (self-deactivation, last active admin)
      // come back from the backend as 409 with a human-readable detail --
      // getErrorMessage already surfaces that text as-is.
      setActionError(getErrorMessage(err, 'Unable to complete this action right now.'))
    } finally {
      setActionSubmitting(false)
    }
  }

  return (
    <div>
      <div className="mb-4">
        <h1 className="h4 mb-1">Administrator Management</h1>
        <p className="text-muted small mb-0">
          View administrator accounts and manage their access.
        </p>
      </div>

      {successMessage && (
        <div
          className="alert alert-success d-flex justify-content-between align-items-start"
          role="alert"
        >
          <span>{successMessage}</span>
          <button
            type="button"
            className="btn-close"
            aria-label="Dismiss"
            onClick={() => setSuccessMessage('')}
          />
        </div>
      )}

      <form className="row g-2 align-items-end mb-4" onSubmit={handleSearchSubmit}>
        <div className="col-12 col-md-4">
          <label htmlFor="admin-search" className="form-label small">
            Search
          </label>
          <input
            id="admin-search"
            type="text"
            className="form-control form-control-sm"
            placeholder="Username"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        <div className="col-auto d-flex gap-2">
          <button type="submit" className="btn btn-outline-primary btn-sm">
            Search
          </button>
          {search && (
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={handleClearSearch}
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {loading && <LoadingState message="Loading administrators..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && admins.length === 0 && (
        <EmptyState
          title="No administrators found"
          message={search ? 'No administrators match your search.' : 'No administrators yet.'}
        />
      )}

      {!loading && !error && admins.length > 0 && (
        <>
          <div className="card shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
              <span className="fw-semibold">Administrators</span>
              <span className="text-muted small">{pagination.total} total</span>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th className="ps-3">Username</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th className="pe-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {admins.map((admin) => {
                      const isSelf = currentAdmin && admin.id === currentAdmin.id
                      return (
                        <tr key={admin.id}>
                          <td className="ps-3">
                            <span className="fw-semibold">{admin.username}</span>
                            {isSelf && (
                              <span className="badge text-bg-light text-dark border ms-2">
                                You
                              </span>
                            )}
                          </td>
                          <td>
                            <span className={`badge ${statusBadgeClass(admin.status)}`}>
                              {statusLabel(admin.status)}
                            </span>
                          </td>
                          <td className="text-nowrap text-muted small">
                            {new Date(admin.created_at).toLocaleDateString(undefined, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </td>
                          <td className="pe-3">
                            {isSelf ? (
                              <span className="text-muted small">
                                You cannot deactivate your own account
                              </span>
                            ) : admin.status ? (
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-warning"
                                onClick={() => openPendingAction('deactivate', admin)}
                              >
                                Deactivate
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-success"
                                onClick={() => openPendingAction('activate', admin)}
                              >
                                Activate
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="d-flex justify-content-between align-items-center mt-3">
            <p className="text-muted small mb-0">
              Page {page} of {pagination.total_pages} (Total: {pagination.total})
            </p>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={handlePrevious}
                disabled={page <= 1}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={handleNext}
                disabled={page >= pagination.total_pages}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {pendingAction && (
        <ConfirmModal
          title={
            pendingAction.type === 'activate' ? 'Activate Administrator?' : 'Deactivate Administrator?'
          }
          confirmLabel={
            actionSubmitting
              ? 'Working...'
              : pendingAction.type === 'activate'
                ? 'Activate'
                : 'Deactivate'
          }
          confirmDisabled={actionSubmitting}
          onConfirm={handleConfirmAction}
          onCancel={closePendingAction}
        >
          {pendingAction.type === 'activate' ? (
            <p>
              Activate <strong>{pendingAction.admin.username}</strong>? They will regain
              administrator access.
            </p>
          ) : (
            <p>
              Deactivate <strong>{pendingAction.admin.username}</strong>? They will lose
              administrator access immediately.
            </p>
          )}
          {actionError && (
            <div className="alert alert-danger py-2 small mb-0" role="alert">
              {actionError}
            </div>
          )}
        </ConfirmModal>
      )}
    </div>
  )
}
