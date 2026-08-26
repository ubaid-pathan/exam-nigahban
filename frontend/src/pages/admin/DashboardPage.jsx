import { useEffect, useState } from 'react'
import { fetchDashboardSummary } from '../../api/adminDashboard'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'

const STAT_CARDS = [
  { key: 'active_exams', label: 'Active Exams' },
  { key: 'active_sessions', label: 'Active Sessions' },
  { key: 'active_students', label: 'Active Students' },
  { key: 'total_events', label: 'Total Events' },
  { key: 'pending_review_events', label: 'Pending Reviews' },
  { key: 'high_severity_pending_events', label: 'High-Severity Pending' },
  { key: 'confirmed_events', label: 'Confirmed Events' },
  { key: 'ignored_events', label: 'Ignored Events' },
  { key: 'evidence_count', label: 'Evidence Count' },
  { key: 'total_review_actions', label: 'Total Review Actions' },
]

export default function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchDashboardSummary()
      setSummary(data)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load dashboard statistics right now.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) return <LoadingState message="Loading dashboard..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  // The summary always returns a full set of aggregate counts (zeros
  // included), so there is no meaningful "empty" state distinct from
  // successfully-loaded data with all-zero values -- EmptyState does not
  // apply here.
  if (!summary) return null

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-2">
        <div>
          <h1 className="h4 mb-1">Admin Dashboard</h1>
          <p className="text-muted small mb-0">
            Snapshot generated at {new Date(summary.generated_at).toLocaleString()}
          </p>
        </div>
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="row g-3">
        {STAT_CARDS.map((card) => (
          <div className="col-12 col-sm-6 col-lg-4 col-xl-3" key={card.key}>
            <div className="card h-100">
              <div className="card-body">
                <p className="text-muted small mb-1">{card.label}</p>
                <p className="h3 mb-0">{summary[card.key]}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
