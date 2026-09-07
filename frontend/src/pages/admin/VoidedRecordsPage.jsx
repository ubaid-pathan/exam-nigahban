import { useCallback, useEffect, useState } from 'react'
import { listVoidedRecords } from '../../api/void'
import { useAuth } from '../../context/AuthContext'
import { getErrorMessage } from '../../utils/apiError'
import { formatDateTimePKT } from '../../utils/dateFormat'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'

// The counterpart to voiding, and the reason voiding is not deletion.
//
// A voided record leaves every queue, count and report -- but it must not
// leave the system unaccounted for. Without this page, an administrator
// withdrawing a violation would be indistinguishable from one deleting it,
// and "what happened to event 412?" would have no answer.
export default function VoidedRecordsPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await listVoidedRecords())
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load voided records.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // The API refuses this to anyone else, so this only replaces a raw 403
  // with an explanation of why the page is empty for them.
  if (!user?.is_system_admin) {
    return (
      <div>
        <h1 className="h4 mb-4">Voided Records</h1>
        <EmptyState
          title="System administrator only"
          message="Withdrawn records are visible to the system administrator account."
        />
      </div>
    )
  }

  return (
    <div>
      <h1 className="h4 mb-2">Voided Records</h1>
      <p className="text-muted small mb-4">
        Records withdrawn from the monitoring queues, counts and reports. Nothing here
        was deleted &mdash; each entry keeps who withdrew it, when, and why.
      </p>

      {loading && <LoadingState message="Loading voided records..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data && data.total === 0 && (
        <EmptyState
          title="Nothing has been voided"
          message="No monitoring event or exam has been withdrawn from the record."
        />
      )}

      {!loading && !error && data && data.total > 0 && (
        <div className="table-responsive">
          <table className="table table-sm table-hover align-middle">
            <thead>
              <tr>
                <th>Type</th>
                <th>Record</th>
                <th>Voided By</th>
                <th>Voided At</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={`${item.kind}-${item.id}`}>
                  <td>
                    <span className="badge text-bg-secondary">
                      {item.kind === 'monitoring_event' ? 'Violation' : 'Exam'}
                    </span>
                  </td>
                  <td>
                    {item.label}
                    <div className="text-muted small">#{item.id}</div>
                  </td>
                  <td>{item.voided_by}</td>
                  <td className="text-nowrap">{formatDateTimePKT(item.voided_at)}</td>
                  <td>{item.void_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
