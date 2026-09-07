import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listMonitoringEvents, listMonitoringSessions } from '../../api/monitoring'
import { getErrorMessage } from '../../utils/apiError'
import { useAuth } from '../../context/AuthContext'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  eventTypeLabel,
  sessionAlertLevel,
  sortEventTypeCounts,
  studentInitials,
} from '../../utils/monitoringStatus'
import { sessionStatusBadgeClass, sessionStatusLabel } from '../../utils/sessionStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import LoadingState from '../LoadingState'
import ErrorState from '../ErrorState'
import EmptyState from '../EmptyState'
import EvidenceReviewPanel from '../EvidenceReviewPanel'

/**
 * Which full-page state, if any, should REPLACE the whole view.
 *
 * Exists as a named, exported predicate because getting it wrong is
 * invisible until it bites: this component renders the Evidence Review
 * dialog, and reviewing an event triggers a background refetch. Returning
 * a spinner whenever `loading` is true unmounted that dialog mid-review
 * and discarded the state that reveals the enforcement ladder after a
 * confirmation -- so the ladder was unreachable from this view entirely,
 * while working fine from the flat events list.
 *
 * The rule: only replace the view when there is nothing to show yet. Once
 * data has arrived, a refetch or a transient failure is reported in place.
 *
 * @returns {'loading'|'error'|null}
 */
export function fullPageState({ loading, error, data }) {
  if (loading && !data) return 'loading'
  if (error && !data) return 'error'
  return null
}

// One row per student exam session, combining every violation that session
// produced -- so a student who triggers Face Absent three times and Mobile
// Phone twice reads as one record rather than five unrelated rows.
//
// The grouping is display-only. Expanding a row fetches that session's
// individual events through the unchanged
// GET /api/monitoring/events?session_id=... endpoint, and review still
// happens per event, because each event carries its own evidence image.
export default function MonitoringSessionsView({ filters, pageSize }) {
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // sessionId -> { loading, error, items }. Fetched lazily on expand and
  // kept afterwards, so collapsing and reopening a row costs nothing.
  const [expanded, setExpanded] = useState({})
  const [selectedEvent, setSelectedEvent] = useState(null)
  const { user } = useAuth()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await listMonitoringSessions({ ...filters, page, pageSize }))
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load monitoring sessions right now.'))
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => {
    load()
  }, [load])

  // A filter change can shrink the result set below the current page.
  useEffect(() => {
    setPage(1)
  }, [filters])

  const loadSessionEvents = useCallback(
    async (sessionId) => {
      setExpanded((current) => ({
        ...current,
        [sessionId]: { loading: true, error: '', items: [] },
      }))
      try {
        const result = await listMonitoringEvents({
          sessionId,
          status: filters.status || undefined,
          eventType: filters.eventType || undefined,
          page: 1,
          // A single session's violations comfortably fit one page; the
          // rollup's own total_events tells the admin if more exist.
          pageSize: 100,
        })
        setExpanded((current) => ({
          ...current,
          [sessionId]: { loading: false, error: '', items: result.items },
        }))
      } catch (err) {
        setExpanded((current) => ({
          ...current,
          [sessionId]: {
            loading: false,
            error: getErrorMessage(err, 'Unable to load this session’s violations.'),
            items: [],
          },
        }))
      }
    },
    [filters.status, filters.eventType],
  )

  const toggleSession = (sessionId) => {
    if (expanded[sessionId]) {
      setExpanded((current) => {
        const next = { ...current }
        delete next[sessionId]
        return next
      })
      return
    }
    loadSessionEvents(sessionId)
  }

  // After a review, refresh both layers: the rollup's status counts and
  // the open session's own event rows.
  const refreshAfterReview = useCallback(() => {
    load()
    Object.keys(expanded).forEach((sessionId) => loadSessionEvents(Number(sessionId)))
  }, [load, expanded, loadSessionEvents])

  const pageState = fullPageState({ loading, error, data })
  if (pageState === 'loading') {
    return <LoadingState message="Loading monitoring sessions..." />
  }
  if (pageState === 'error') {
    return <ErrorState message={error} onRetry={load} />
  }
  if (!loading && !error && (!data || data.items.length === 0)) {
    return (
      <EmptyState
        title="No sessions with violations"
        message="No exam session has produced a monitoring alert matching the current filters."
      />
    )
  }

  return (
    <>
      {error && (
        <div className="alert alert-warning py-2 small" role="alert">
          {error}{' '}
          <button type="button" className="btn btn-link btn-sm p-0 align-baseline" onClick={load}>
            Retry
          </button>
        </div>
      )}

      <div className="d-flex flex-column gap-3">
        {(data?.items ?? []).map((session) => {
          const detail = expanded[session.session_id]
          const isOpen = Boolean(detail)
          const typeCounts = sortEventTypeCounts(session.events_by_type)
          const level = sessionAlertLevel(session)

          return (
            <div key={session.session_id} className={`card session-card session-card--${level}`}>
              <div className="card-body">
                <div className="d-flex flex-wrap justify-content-between align-items-start gap-3">
                  <div className="d-flex align-items-center gap-3 session-card__identity">
                    <span className="session-card__avatar" aria-hidden="true">
                      {studentInitials(session.student_full_name)}
                    </span>
                    <div className="session-card__identity">
                      <h2 className="h6 mb-1 text-truncate">{session.student_full_name}</h2>
                      <p className="text-muted small mb-0">
                        {session.student_id} &middot; {session.exam_title}{' '}
                        <span className={`badge ${sessionStatusBadgeClass(session.session_status)}`}>
                          {sessionStatusLabel(session.session_status)}
                        </span>
                      </p>
                    </div>
                  </div>

                  <div className="d-flex align-items-center gap-2 flex-shrink-0">
                    {/* The one number an invigilator acts on; everything
                        else is context and is demoted below. */}
                    {session.pending_events > 0 ? (
                      <span
                        className={`badge ${
                          level === 'critical' ? 'text-bg-danger' : 'text-bg-warning'
                        }`}
                      >
                        {session.pending_events} pending review
                      </span>
                    ) : (
                      <span className="badge text-bg-success">All reviewed</span>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => toggleSession(session.session_id)}
                      aria-expanded={isOpen}
                    >
                      {isOpen ? 'Hide' : `View ${session.total_events}`}
                    </button>
                    {/* The printable case report for this candidate. */}
                    <Link
                      to={`/admin/reports/sessions/${session.session_id}`}
                      className="btn btn-sm btn-outline-secondary"
                    >
                      Report
                    </Link>
                  </div>
                </div>

                {/* The combined record: what this student did, how often. */}
                <div className="d-flex flex-wrap gap-2 mt-3">
                  {typeCounts.map(({ type, label, count }) => (
                    <span key={type} className="badge text-bg-light border">
                      {label} <strong className="ms-1">&times;{count}</strong>
                    </span>
                  ))}
                </div>

                <p className="text-muted small mt-3 mb-0">
                  {session.total_events} violation{session.total_events === 1 ? '' : 's'}
                  {session.high_severity_events > 0 && (
                    <>
                      {' '}
                      &middot;{' '}
                      <span className="text-danger fw-semibold">
                        {session.high_severity_events} high severity
                      </span>
                    </>
                  )}
                  {' '}
                  &middot; {session.confirmed_events} confirmed &middot;{' '}
                  {session.ignored_events} ignored &middot; {session.evidence_count} with evidence
                  {' '}
                  &middot; session {session.session_id}
                </p>

                <p className="text-muted small mt-1 mb-0">
                  {formatDateTimePKT(session.first_detected_at)} &rarr;{' '}
                  {formatDateTimePKT(session.last_detected_at)}
                </p>

                {isOpen && (
                  <div className="mt-3 pt-3 border-top">
                    {detail.loading && <p className="text-muted small mb-0">Loading violations...</p>}
                    {detail.error && <p className="text-danger small mb-0">{detail.error}</p>}
                    {!detail.loading && !detail.error && (
                      <div className="table-responsive">
                        <table className="table table-sm table-hover align-middle mb-0">
                          <thead>
                            <tr>
                              <th>Activity</th>
                              <th>Confidence</th>
                              <th>Duration</th>
                              <th>Status</th>
                              <th>Detected At</th>
                              <th>Review</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detail.items.map((item) => (
                              <tr key={item.id}>
                                <td>{eventTypeLabel(item.event_type)}</td>
                                <td>{(item.confidence * 100).toFixed(1)}%</td>
                                <td>{Number(item.duration_seconds).toFixed(2)}s</td>
                                <td>
                                  <span className={`badge ${eventStatusBadgeClass(item.status)}`}>
                                    {eventStatusLabel(item.status)}
                                  </span>
                                </td>
                                <td className="text-nowrap">
                                  {formatDateTimePKT(item.detected_at)}
                                </td>
                                <td>
                                  {item.evidence_id != null ? (
                                    <button
                                      type="button"
                                      className="btn btn-sm btn-primary"
                                      onClick={() => setSelectedEvent(item)}
                                    >
                                      Review
                                    </button>
                                  ) : (
                                    <span className="text-muted small">&mdash;</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {data && (
      <div className="d-flex justify-content-between align-items-center mt-3">
        <p className="text-muted small mb-0">
          Page {data.page} of {data.total_pages} ({data.total} session
          {data.total === 1 ? '' : 's'})
        </p>
        <div className="d-flex gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            Previous
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={() =>
              setPage((current) => (current < data.total_pages ? current + 1 : current))
            }
            disabled={page >= data.total_pages}
          >
            Next
          </button>
        </div>
      </div>
      )}

      {selectedEvent && (
        <EvidenceReviewPanel
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onReviewed={() => {
            setSelectedEvent(null)
            refreshAfterReview()
          }}
          onRefresh={refreshAfterReview}
          canVoid={Boolean(user?.is_system_admin)}
        />
      )}
    </>
  )
}
