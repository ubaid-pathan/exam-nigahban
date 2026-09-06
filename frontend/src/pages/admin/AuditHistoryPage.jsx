import { useCallback, useEffect, useState } from 'react'
import { listAuditLog } from '../../api/audit'
import { getErrorMessage } from '../../utils/apiError'
import { eventStatusBadgeClass, eventStatusLabel } from '../../utils/monitoringStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import { groupAuditEntriesBySession } from '../../utils/auditGrouping'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'

const PAGE_SIZE = 10
const ACTION_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'CONFIRMED', label: 'Confirmed' },
  { value: 'IGNORED', label: 'Ignored' },
]

export default function AuditHistoryPage() {
  const [action, setAction] = useState('')
  // Narrows the log to one student's exam session. The rows themselves are
  // never merged -- each admin decision stays separately listed and
  // attributable, which is the property that makes an audit trail
  // defensible; the grouping below is presentation only.
  const [sessionId, setSessionId] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listAuditLog({
        action: action || undefined,
        sessionId: sessionId ? Number(sessionId) : undefined,
        page,
        pageSize: PAGE_SIZE,
      })
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load audit history right now.'))
    } finally {
      setLoading(false)
    }
  }, [action, sessionId, page])

  useEffect(() => {
    load()
  }, [load])

  const handleActionChange = (e) => {
    setAction(e.target.value)
    setPage(1)
  }

  const handleSessionChange = (e) => {
    setSessionId(e.target.value)
    setPage(1)
  }

  const handlePrevious = () => setPage((current) => Math.max(1, current - 1))
  const handleNext = () =>
    setPage((current) => (data && current < data.total_pages ? current + 1 : current))

  return (
    <div>
      <h1 className="h4 mb-4">Audit History</h1>

      <div className="row g-2 align-items-end mb-4">
        <div className="col-6 col-md-3">
          <label htmlFor="filter-action" className="form-label small">
            Action
          </label>
          <select
            id="filter-action"
            className="form-select form-select-sm"
            value={action}
            onChange={handleActionChange}
          >
            {ACTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="filter-session-id" className="form-label small">
            Session ID
          </label>
          <input
            id="filter-session-id"
            type="number"
            min="1"
            className="form-control form-control-sm"
            value={sessionId}
            onChange={handleSessionChange}
            placeholder="All sessions"
          />
        </div>
      </div>

      {loading && <LoadingState message="Loading audit history..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          title="No audit records"
          message="No administrative review actions match the current filter."
        />
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="d-flex flex-column gap-3">
            {groupAuditEntriesBySession(data.items).map((group) => (
              <div key={group.sessionId} className="card">
                <div className="card-body">
                  <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
                    <div>
                      <h2 className="h6 mb-1">
                        {group.studentFullName}{' '}
                        <span className="text-muted fw-normal">({group.studentId})</span>
                      </h2>
                      <p className="text-muted small mb-0">
                        {group.examTitle} &middot; session {group.sessionId}
                      </p>
                    </div>
                    <p className="text-muted small mb-0">
                      {group.entries.length} decision{group.entries.length === 1 ? '' : 's'}
                      {' '}&middot; {group.confirmedCount} confirmed &middot; {group.ignoredCount} ignored
                    </p>
                  </div>

                  {/* Every decision stays its own row: an audit trail's
                      value is that each act is separately attributable to
                      an administrator and a moment. */}
                  <div className="table-responsive">
                    <table className="table table-sm table-hover align-middle mb-0">
                      <thead>
                        <tr>
                          <th>Event Type</th>
                          <th>Action</th>
                          <th>Reason</th>
                          <th>Admin</th>
                          <th>Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.entries.map((item) => (
                          <tr key={item.id}>
                            <td>{item.event_type}</td>
                            <td>
                              <span className={`badge ${eventStatusBadgeClass(item.action)}`}>
                                {eventStatusLabel(item.action)}
                              </span>
                            </td>
                            <td>
                              {item.reason || <span className="text-muted small">&mdash;</span>}
                            </td>
                            <td>{item.admin_username}</td>
                            <td className="text-nowrap">{formatDateTimePKT(item.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ))}
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
    </div>
  )
}
