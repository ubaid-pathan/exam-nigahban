import { useCallback, useEffect, useState } from 'react'
import { liftEnforcementAction, listEnforcementActions } from '../../api/enforcement'
import { getErrorMessage } from '../../utils/apiError'
import {
  ACTION_TYPE_LABELS,
  ENFORCEMENT_STATUS_LABELS,
  actionTypeBadgeClass,
  actionTypeLabel,
  enforcementStatusBadgeClass,
  enforcementStatusLabel,
} from '../../utils/enforcementStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'

const PAGE_SIZE = 10
const EMPTY_FILTERS = { actionType: '', status: '' }

// Read-only audit view of every enforcement action taken by admins (the
// actions themselves are taken from the evidence review panel). The one
// mutation available here is lifting a still-active block early; CANCEL_EXAM
// and UFM_CASE rows are terminal by design and can only be read.
export default function EnforcementActionsPage() {
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // The active-block row pending lift confirmation, or null.
  const [pendingLift, setPendingLift] = useState(null)
  const [lifting, setLifting] = useState(false)
  const [liftError, setLiftError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listEnforcementActions({
        actionType: appliedFilters.actionType,
        status: appliedFilters.status,
        page,
        pageSize: PAGE_SIZE,
      })
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load enforcement actions right now.'))
    } finally {
      setLoading(false)
    }
  }, [appliedFilters, page])

  useEffect(() => {
    load()
  }, [load])

  const handleApplyFilters = (event) => {
    event.preventDefault()
    setPage(1)
    setAppliedFilters(draftFilters)
  }

  const handleClearFilters = () => {
    setDraftFilters(EMPTY_FILTERS)
    setAppliedFilters(EMPTY_FILTERS)
    setPage(1)
  }

  const handlePrevious = () => setPage((current) => Math.max(1, current - 1))
  const handleNext = () =>
    setPage((current) => (data && current < data.total_pages ? current + 1 : current))

  const handleLift = async () => {
    setLifting(true)
    setLiftError('')
    try {
      await liftEnforcementAction(pendingLift.id)
      setPendingLift(null)
      load()
    } catch (err) {
      setLiftError(getErrorMessage(err, 'Unable to lift this block. Please try again.'))
    } finally {
      setLifting(false)
    }
  }

  return (
    <div>
      <h1 className="h4 mb-4">Enforcement Actions</h1>

      <form className="row g-2 align-items-end mb-4" onSubmit={handleApplyFilters}>
        <div className="col-6 col-md-3">
          <label htmlFor="filter-action-type" className="form-label small">
            Action Type
          </label>
          <select
            id="filter-action-type"
            className="form-select form-select-sm"
            value={draftFilters.actionType}
            onChange={(e) => setDraftFilters((f) => ({ ...f, actionType: e.target.value }))}
          >
            <option value="">All</option>
            {Object.keys(ACTION_TYPE_LABELS).map((type) => (
              <option key={type} value={type}>
                {actionTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="filter-status" className="form-label small">
            Status
          </label>
          <select
            id="filter-status"
            className="form-select form-select-sm"
            value={draftFilters.status}
            onChange={(e) => setDraftFilters((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">All</option>
            {Object.keys(ENFORCEMENT_STATUS_LABELS).map((status) => (
              <option key={status} value={status}>
                {enforcementStatusLabel(status)}
              </option>
            ))}
          </select>
        </div>

        <div className="col-12 col-md-3 d-flex gap-2">
          <button type="submit" className="btn btn-primary btn-sm">
            Apply
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={handleClearFilters}
          >
            Clear
          </button>
        </div>
      </form>

      {loading && <LoadingState message="Loading enforcement actions..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          title="No enforcement actions"
          message="No enforcement actions have been recorded, or none match the current filters."
        />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Exam</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Admin</th>
                  <th>Created At</th>
                  <th>Blocked Until</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.student_full_name}
                      <div className="text-muted small">{item.student_id}</div>
                    </td>
                    <td>{item.exam_title}</td>
                    <td>
                      <span className={`badge ${actionTypeBadgeClass(item.action_type)}`}>
                        {actionTypeLabel(item.action_type)}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${enforcementStatusBadgeClass(item.effective_status)}`}>
                        {enforcementStatusLabel(item.effective_status)}
                      </span>
                    </td>
                    <td className="small text-truncate" style={{ maxWidth: '220px' }} title={item.reason}>
                      {item.reason}
                    </td>
                    <td>{item.admin_username}</td>
                    <td className="text-nowrap">{formatDateTimePKT(item.created_at)}</td>
                    <td className="text-nowrap">
                      {item.blocked_until ? formatDateTimePKT(item.blocked_until) : '—'}
                    </td>
                    <td>
                      {item.action_type === 'BLOCK' && item.effective_status === 'ACTIVE' ? (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-warning"
                          onClick={() => {
                            setLiftError('')
                            setPendingLift(item)
                          }}
                        >
                          Lift Block
                        </button>
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="d-flex justify-content-between align-items-center mt-3">
            <p className="text-muted small mb-0">
              Page {data.page} of {data.total_pages} (Total: {data.total})
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
                disabled={page >= data.total_pages}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {pendingLift && (
        <ConfirmModal
          title="Lift This Block?"
          confirmLabel={lifting ? 'Lifting...' : 'Lift Block'}
          confirmVariant="warning"
          confirmDisabled={lifting}
          onConfirm={handleLift}
          onCancel={() => !lifting && setPendingLift(null)}
        >
          <p>
            <strong>{pendingLift.student_full_name}</strong> will regain write access to{' '}
            <strong>{pendingLift.exam_title}</strong> immediately, before the block&apos;s
            scheduled end{pendingLift.blocked_until ? ` (${formatDateTimePKT(pendingLift.blocked_until)})` : ''}.
          </p>
          <p className="mb-0 small text-muted">
            The block is recorded as lifted in the enforcement log; the original action and its
            reason are kept.
          </p>
          {liftError && (
            <div className="alert alert-danger py-2 small mt-2 mb-0" role="alert">
              {liftError}
            </div>
          )}
        </ConfirmModal>
      )}
    </div>
  )
}
