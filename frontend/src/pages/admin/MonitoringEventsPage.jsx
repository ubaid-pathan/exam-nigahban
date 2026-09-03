import { useCallback, useEffect, useState } from 'react'
import { listMonitoringEvents } from '../../api/monitoring'
import { getErrorMessage } from '../../utils/apiError'
import {
  EVENT_STATUS_LABELS,
  eventStatusBadgeClass,
  eventStatusLabel,
  eventTypeLabel,
} from '../../utils/monitoringStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import { MONITORING_EVENT_TYPES } from '../../monitoring/constants'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import EvidenceReviewPanel from '../../components/EvidenceReviewPanel'

const PAGE_SIZE = 10
const EMPTY_FILTERS = { status: '', eventType: '', sessionId: '' }
// MOBILE_PHONE is deliberately not part of MONITORING_EVENT_TYPES /
// MONITORING_RULES in monitoring/constants.js -- it's detected by a
// separate YOLOX rule engine (see MOBILE_PHONE_RULE and the comment above
// it in that file), not the face-monitoring engine those are derived from.
// Added here only, as a filter option -- the backend identifier string and
// detection logic are untouched.
const EVENT_TYPE_FILTER_OPTIONS = [...MONITORING_EVENT_TYPES, 'MOBILE_PHONE']

export default function MonitoringEventsPage() {
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedEvent, setSelectedEvent] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listMonitoringEvents({
        status: appliedFilters.status,
        eventType: appliedFilters.eventType,
        sessionId: appliedFilters.sessionId ? Number(appliedFilters.sessionId) : undefined,
        page,
        pageSize: PAGE_SIZE,
      })
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load monitoring events right now.'))
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

  const handleReviewed = () => {
    setSelectedEvent(null)
    load()
  }

  return (
    <div>
      <h1 className="h4 mb-4">Monitoring Events</h1>

      <form className="row g-2 align-items-end mb-4" onSubmit={handleApplyFilters}>
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
            {Object.keys(EVENT_STATUS_LABELS).map((status) => (
              <option key={status} value={status}>
                {eventStatusLabel(status)}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="filter-event-type" className="form-label small">
            Event Type
          </label>
          <select
            id="filter-event-type"
            className="form-select form-select-sm"
            value={draftFilters.eventType}
            onChange={(e) => setDraftFilters((f) => ({ ...f, eventType: e.target.value }))}
          >
            <option value="">All</option>
            {EVENT_TYPE_FILTER_OPTIONS.map((type) => (
              <option key={type} value={type}>
                {eventTypeLabel(type)}
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
            value={draftFilters.sessionId}
            onChange={(e) => setDraftFilters((f) => ({ ...f, sessionId: e.target.value }))}
          />
        </div>

        <div className="col-12 col-md-3 d-flex gap-2">
          <button type="submit" className="btn btn-primary btn-sm">
            Apply
          </button>
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={handleClearFilters}>
            Clear
          </button>
        </div>
      </form>

      {loading && <LoadingState message="Loading monitoring events..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          title="No monitoring events"
          message="No monitoring events match the current filters."
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
                  <th>Confidence</th>
                  <th>Duration</th>
                  <th>Occurrences</th>
                  <th>Status</th>
                  <th>Detected At</th>
                  <th>Review</th>
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
                    <td>{eventTypeLabel(item.event_type)}</td>
                    <td>{(item.confidence * 100).toFixed(1)}%</td>
                    <td>{item.duration_seconds}s</td>
                    <td>{item.occurrences}</td>
                    <td>
                      <span className={`badge ${eventStatusBadgeClass(item.status)}`}>
                        {eventStatusLabel(item.status)}
                      </span>
                    </td>
                    <td className="text-nowrap">{formatDateTimePKT(item.detected_at)}</td>
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

      {selectedEvent && (
        <EvidenceReviewPanel
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onReviewed={handleReviewed}
        />
      )}
    </div>
  )
}
