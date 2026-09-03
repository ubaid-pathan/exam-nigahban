import { useEffect, useRef, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { fetchDashboardSummary } from '../../api/adminDashboard'
import { getErrorMessage, isForbiddenError } from '../../utils/apiError'
import { formatDateTimePKT } from '../../utils/dateFormat'
import { useAuth } from '../../context/AuthContext'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import {
  AuditIcon,
  CheckCircleIcon,
  CloseIcon,
  EditIcon,
  ExamsIcon,
  FileIcon,
  MonitoringIcon,
  PlayIcon,
  ShieldAlertIcon,
  UsersIcon,
} from '../../components/admin/icons'

// The exact same ten summary fields fetchDashboardSummary() has always
// returned -- only grouped into sections and paired with a display
// icon/color here. No key, label, or value derivation changed from the
// previous flat ten-card list.
const STAT_SECTIONS = [
  {
    label: 'Exam Activity',
    cards: [
      { key: 'active_exams', label: 'Active Exams', icon: ExamsIcon, tone: 'primary' },
      { key: 'active_sessions', label: 'Active Sessions', icon: PlayIcon, tone: 'info' },
      { key: 'active_students', label: 'Active Students', icon: UsersIcon, tone: 'secondary' },
    ],
  },
  {
    label: 'Monitoring Events',
    cards: [
      { key: 'total_events', label: 'Total Events', icon: MonitoringIcon, tone: 'secondary' },
      { key: 'pending_review_events', label: 'Pending Reviews', icon: AuditIcon, tone: 'warning' },
      {
        key: 'high_severity_pending_events',
        label: 'High-Severity Pending',
        icon: ShieldAlertIcon,
        tone: 'danger',
      },
    ],
  },
  {
    label: 'Review Outcomes',
    cards: [
      { key: 'confirmed_events', label: 'Confirmed Events', icon: CheckCircleIcon, tone: 'success' },
      { key: 'ignored_events', label: 'Ignored Events', icon: CloseIcon, tone: 'secondary' },
      { key: 'evidence_count', label: 'Evidence Count', icon: FileIcon, tone: 'info' },
      { key: 'total_review_actions', label: 'Total Review Actions', icon: EditIcon, tone: 'primary' },
    ],
  },
]

const LIVE_REFRESH_DEBOUNCE_MS = 1000

export default function DashboardPage() {
  const { latestAlert, wsConnected } = useOutletContext()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [forbidden, setForbidden] = useState(false)
  const [loading, setLoading] = useState(true)
  const debounceRef = useRef(null)
  const initialLoadRef = useRef(true)

  const load = async () => {
    setLoading(true)
    setError('')
    setForbidden(false)
    try {
      const data = await fetchDashboardSummary()
      setSummary(data)
    } catch (err) {
      if (isForbiddenError(err)) {
        // 403 means the session token does not match an admin account --
        // most common cause is a stale token left in localStorage after a
        // backend reset or a role change.  Clearing the session and
        // re-logging-in resolves it.
        setForbidden(true)
        setError(
          'Your session does not have admin privileges. This usually happens when a previous session token is still active. Please log out and sign in again.',
        )
      } else {
        setError(getErrorMessage(err, 'Unable to load dashboard statistics right now.'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRelogin = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  // Silent background refresh -- no loading spinner so the dashboard stays
  // stable while the admin is scanning it. Used only for auto-refresh
  // triggered by incoming WebSocket alerts; manual "Refresh" calls load()
  // which does show a full loading state.
  const silentRefresh = async () => {
    try {
      const data = await fetchDashboardSummary()
      setSummary(data)
    } catch {
      // Transient failure during auto-refresh is non-critical; the next
      // alert or manual refresh will retry.
    }
  }

  // Initial load.
  useEffect(() => {
    load()
  }, [])

  // Auto-refresh when a new monitoring event arrives via WebSocket.
  // Debounced at 1s trailing edge so a burst of rapid events triggers one
  // refetch rather than one per event.
  useEffect(() => {
    if (initialLoadRef.current) {
      initialLoadRef.current = false
      return
    }
    if (latestAlert) {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(silentRefresh, LIVE_REFRESH_DEBOUNCE_MS)
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [latestAlert])

  if (loading) return <LoadingState message="Loading dashboard..." />
  if (error) {
    // 403 gets a dedicated error with a "Log out & sign in" action because
    // retrying with the same stale token will always fail -- the user must
    // re-authenticate to get a fresh token that matches their admin role.
    if (forbidden) {
      return (
        <div className="alert alert-warning" role="alert">
          <h2 className="h6 mb-1">Session mismatch</h2>
          <p className="mb-2">{error}</p>
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-sm btn-warning"
              onClick={handleRelogin}
            >
              Log out &amp; sign in again
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-warning"
              onClick={load}
            >
              Retry
            </button>
          </div>
        </div>
      )
    }
    return <ErrorState message={error} onRetry={load} />
  }
  // The summary always returns a full set of aggregate counts (zeros
  // included), so there is no meaningful "empty" state distinct from
  // successfully-loaded data with all-zero values -- EmptyState does not
  // apply here.
  if (!summary) return null

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-2">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <h1 className="h4 mb-0">Admin Dashboard</h1>
            {wsConnected && (
              <span className="dashboard-live-indicator">
                <span className="dashboard-live-indicator__dot" />
                Live
              </span>
            )}
          </div>
          <p className="text-muted small mb-0">
            Snapshot generated at {formatDateTimePKT(summary.generated_at)}
          </p>
        </div>
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={load}>
          Refresh
        </button>
      </div>

      {STAT_SECTIONS.map((section, index) => (
        <div className={index === STAT_SECTIONS.length - 1 ? '' : 'mb-4'} key={section.label}>
          <h2 className="dashboard-section-label">{section.label}</h2>
          <div className="row g-3">
            {section.cards.map((card) => {
              const Icon = card.icon
              return (
                <div className="col-12 col-sm-6 col-lg-4 col-xl-3" key={card.key}>
                  <div className="card h-100">
                    <div className="card-body d-flex align-items-start gap-3">
                      <span
                        className={`dashboard-stat-card__icon dashboard-stat-card__icon--${card.tone}`}
                      >
                        <Icon width={18} height={18} />
                      </span>
                      <div>
                        <p className="text-muted small mb-1">{card.label}</p>
                        <p className="h3 mb-0">{summary[card.key]}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
