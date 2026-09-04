import { useEffect, useState } from 'react'
import { fetchEvidenceImageBlob, reviewEvidence } from '../api/evidence'
import { getErrorMessage } from '../utils/apiError'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  eventTypeLabel,
  severityBadgeClass,
  severityLabel,
} from '../utils/monitoringStatus'
import { formatDateTimePKT } from '../utils/dateFormat'

// Renders the evidence image for `event.evidence_id` and lets an admin
// record a CONFIRMED/IGNORED decision. The image endpoint requires the same
// JWT bearer auth as every other admin request, so it is fetched as a blob
// through the authenticated apiClient (see api/evidence.js) rather than
// loaded via a plain <img src="...">, and the resulting object URL is
// always revoked on unmount/close/event-change to avoid leaking memory.
export default function EvidenceReviewPanel({ event, onClose, onReviewed }) {
  const [imageUrl, setImageUrl] = useState(null)
  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  useEffect(() => {
    let cancelled = false
    let objectUrl = null

    async function loadImage() {
      setImageLoading(true)
      setImageError('')
      try {
        const blob = await fetchEvidenceImageBlob(event.evidence_id)
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      } catch (err) {
        if (!cancelled) {
          setImageError(getErrorMessage(err, 'Unable to load the evidence image.'))
        }
      } finally {
        if (!cancelled) setImageLoading(false)
      }
    }

    loadImage()

    return () => {
      cancelled = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [event.evidence_id])

  const handleReview = async (action) => {
    setSubmitting(true)
    setSubmitError('')
    try {
      const result = await reviewEvidence(event.evidence_id, action, reason.trim() || undefined)
      // The parent refetches the event list after this, so the table
      // reflects the server's actual resulting status rather than a
      // client-guessed one.
      onReviewed(result)
    } catch (err) {
      setSubmitError(getErrorMessage(err, 'Unable to record this review. Please try again.'))
      setSubmitting(false)
    }
  }

  return (
    <div
      className="modal-backdrop-manual"
      role="dialog"
      aria-modal="true"
      aria-labelledby="evidence-review-title"
    >
      <div
        className="modal-dialog modal-lg"
        style={{ margin: 0, width: '100%', maxWidth: 'min(760px, 92vw)' }}
      >
        <div className="modal-content evidence-review-modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="evidence-review-title">
              Evidence Review
            </h5>
            <button
              type="button"
              className="btn-close"
              aria-label="Close"
              onClick={onClose}
              disabled={submitting}
            />
          </div>
          <div className="modal-body">
            <div className="row g-3 align-items-start">
              <div className="col-12 col-md-5">
                {imageLoading && <p className="text-muted small mb-0">Loading evidence image...</p>}
                {imageError && <p className="text-danger small mb-0">{imageError}</p>}
                {imageUrl && (
                  <img
                    src={imageUrl}
                    alt="Captured evidence for this monitoring event"
                    className="img-fluid rounded border"
                  />
                )}
              </div>
              <div className="col-12 col-md-7">
                <dl className="row gy-2 small mb-0">
                  <dt className="col-5">Student</dt>
                  <dd className="col-7">
                    {event.student_full_name} ({event.student_id})
                  </dd>
                  <dt className="col-5">Exam</dt>
                  <dd className="col-7">{event.exam_title}</dd>
                  <dt className="col-5">Activity</dt>
                  <dd className="col-7">{eventTypeLabel(event.event_type)}</dd>
                  <dt className="col-5">Severity</dt>
                  <dd className="col-7">
                    <span className={`badge ${severityBadgeClass(event.severity)}`}>
                      {severityLabel(event.severity)}
                    </span>
                  </dd>
                  <dt className="col-5">Status</dt>
                  <dd className="col-7">
                    <span className={`badge ${eventStatusBadgeClass(event.status)}`}>
                      {eventStatusLabel(event.status)}
                    </span>
                  </dd>
                  <dt className="col-5">Confidence</dt>
                  <dd className="col-7">{(event.confidence * 100).toFixed(1)}%</dd>
                  <dt className="col-5">Duration</dt>
                  <dd className="col-7">{Number(event.duration_seconds).toFixed(2)}s</dd>
                  <dt className="col-5">Detected At</dt>
                  <dd className="col-7">{formatDateTimePKT(event.detected_at)}</dd>
                </dl>
              </div>
            </div>

            <div className="mt-3">
              <label htmlFor="review-reason" className="form-label small">
                Reason (optional)
              </label>
              <textarea
                id="review-reason"
                className="form-control form-control-sm"
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={submitting}
              />
            </div>

            {submitError && <p className="text-danger small mt-2 mb-0">{submitError}</p>}
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-outline-dark"
              onClick={() => handleReview('IGNORED')}
              disabled={submitting}
            >
              Mark Ignored
            </button>
            <button
              type="button"
              className="btn btn-success"
              onClick={() => handleReview('CONFIRMED')}
              disabled={submitting}
            >
              Confirm
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
