import { useCallback, useEffect, useState } from 'react'
import { listAuditLog } from '../../api/audit'
import { getErrorMessage } from '../../utils/apiError'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  severityBadgeClass,
  severityLabel,
} from '../../utils/monitoringStatus'
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
        page,
        pageSize: PAGE_SIZE,
      })
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load audit history right now.'))
    } finally {
      setLoading(false)
    }
  }, [action, page])

  useEffect(() => {
    load()
  }, [load])

  const handleActionChange = (e) => {
    setAction(e.target.value)
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
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Exam</th>
                  <th>Event Type</th>
                  <th>Severity</th>
                  <th>Session</th>
                  <th>Action</th>
                  <th>Reason</th>
                  <th>Admin</th>
                  <th>Timestamp</th>
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
                    <td>{item.event_type}</td>
                    <td>
                      <span className={`badge ${severityBadgeClass(item.severity)}`}>
                        {severityLabel(item.severity)}
                      </span>
                    </td>
                    <td>{item.session_id}</td>
                    <td>
                      <span className={`badge ${eventStatusBadgeClass(item.action)}`}>
                        {eventStatusLabel(item.action)}
                      </span>
                    </td>
                    <td>
                      {item.reason || <span className="text-muted small">&mdash;</span>}
                    </td>
                    <td>{item.admin_username}</td>
                    <td className="text-nowrap">{new Date(item.created_at).toLocaleString()}</td>
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
    </div>
  )
}
