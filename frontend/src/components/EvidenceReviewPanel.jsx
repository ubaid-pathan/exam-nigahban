import { useEffect, useState } from 'react'
import { fetchEvidenceImageBlob, reviewEvidence } from '../api/evidence'
import { createEnforcementAction } from '../api/enforcement'
import { getErrorMessage } from '../utils/apiError'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  eventTypeLabel,
  severityBadgeClass,
  severityLabel,
} from '../utils/monitoringStatus'
import { formatDateTimePKT } from '../utils/dateFormat'
import ConfirmModal from './ConfirmModal'

// Renders the evidence image for `event.evidence_id` and lets an admin
// record a CONFIRMED/IGNORED decision. The image endpoint requires the same
// JWT bearer auth as every other admin request, so it is fetched as a blob
// through the authenticated apiClient (see api/evidence.js) rather than
// loaded via a plain <img src="...">, and the resulting object URL is
// always revoked on unmount/close/event-change to avoid leaking memory.
//
// For a CONFIRMED event it additionally offers the enforcement ladder
// (pause / cancel / UFM case) -- punishment is only reachable after a
// human has confirmed the evidence, never straight from an alert.
export default function EvidenceReviewPanel({ event, onClose, onReviewed }) {
  const [imageUrl, setImageUrl] = useState(null)
  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  // Enforcement state (CONFIRMED events only).
  const [enforcementReason, setEnforcementReason] = useState('')
  const [blockMinutes, setBlockMinutes] = useState(5)
  // Which destructive action's ConfirmModal is open ('CANCEL_EXAM' |
  // 'UFM_CASE' | null). BLOCK needs no modal -- it is reversible.
  const [pendingAction, setPendingAction] = useState(null)
  const [enforcing, setEnforcing] = useState(false)
  const [enforcementError, setEnforcementError] = useState('')

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

  const hasEnforcementReason = enforcementReason.trim().length >= 3

  // Opens the ConfirmModal for a destructive action. The reason is
  // validated up front so the modal never confirms into a guaranteed 422,
  // and the error lands on the enforcement section instead of behind the
  // modal.
  const requestEnforcement = (actionType) => {
    if (!hasEnforcementReason) {
      setEnforcementError('A reason of at least 3 characters is required for every enforcement action.')
      return
    }
    setEnforcementError('')
    setPendingAction(actionType)
  }

  const handleEnforce = async (actionType, minutes = null) => {
    if (!hasEnforcementReason) {
      setEnforcementError('A reason of at least 3 characters is required for every enforcement action.')
      return
    }
    setEnforcing(true)
    setEnforcementError('')
    try {
      const result = await createEnforcementAction({
        session_id: event.session_id,
        action_type: actionType,
        reason: enforcementReason.trim(),
        event_id: event.id,
        ...(minutes !== null ? { block_minutes: minutes } : {}),
      })
      // Same callback chain as a review decision: the parent closes this
      // panel and refetches, so the action is visible in the enforcement
      // log rather than silently applied from a stale modal.
      onReviewed(result)
    } catch (err) {
      setEnforcementError(
        getErrorMessage(err, 'Unable to record this enforcement action. Please try again.'),
      )
      setEnforcing(false)
    }
  }

  // Clamp defensively on use (not on change): clamping while typing makes
  // the field fight the admin, and the backend would reject out-of-range
  // minutes with a 422 anyway.
  const clampedBlockMinutes = Math.min(60, Math.max(1, Number(blockMinutes) || 5))

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

            {event.status === 'CONFIRMED' && (
              <div className="mt-4 pt-3 border-top">
                <h2 className="h6 mb-1">Enforcement</h2>
                <p className="text-muted small mb-2">
                  This violation is confirmed. You may take an action against{' '}
                  {event.student_full_name}; a reason is required and every action is recorded
                  permanently in the enforcement log.
                </p>

                <label htmlFor="enforcement-reason" className="form-label small">
                  Reason (required)
                </label>
                <textarea
                  id="enforcement-reason"
                  className="form-control form-control-sm"
                  rows={2}
                  value={enforcementReason}
                  onChange={(e) => setEnforcementReason(e.target.value)}
                  disabled={submitting || enforcing}
                  maxLength={1000}
                />

                <div className="d-flex flex-wrap align-items-center gap-2 mt-3">
                  <div className="input-group input-group-sm" style={{ maxWidth: '230px' }}>
                    <input
                      id="block-minutes"
                      type="number"
                      className="form-control"
                      min="1"
                      max="60"
                      value={blockMinutes}
                      onChange={(e) => setBlockMinutes(e.target.value)}
                      disabled={submitting || enforcing}
                      aria-label="Pause duration in minutes"
                    />
                    <span className="input-group-text">min</span>
                    <button
                      type="button"
                      className="btn btn-warning"
                      onClick={() => handleEnforce('BLOCK', clampedBlockMinutes)}
                      disabled={submitting || enforcing}
                    >
                      Pause Exam
                    </button>
                  </div>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => requestEnforcement('CANCEL_EXAM')}
                    disabled={submitting || enforcing}
                  >
                    Cancel Exam
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-danger"
                    onClick={() => requestEnforcement('UFM_CASE')}
                    disabled={submitting || enforcing}
                  >
                    File UFM Case
                  </button>
                </div>

                {enforcementError && (
                  <p className="text-danger small mt-2 mb-0">{enforcementError}</p>
                )}
              </div>
            )}
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-outline-dark"
              onClick={() => handleReview('IGNORED')}
              disabled={submitting || enforcing}
            >
              Mark Ignored
            </button>
            <button
              type="button"
              className="btn btn-success"
              onClick={() => handleReview('CONFIRMED')}
              disabled={submitting || enforcing}
            >
              Confirm
            </button>
          </div>
        </div>
      </div>

      {/* Nested confirmations for the destructive actions: rendered after
          the dialog (later in DOM order) so they paint above it while
          staying inside this panel's root element. */}
      {pendingAction === 'CANCEL_EXAM' && (
        <ConfirmModal
          title="Cancel This Exam?"
          confirmLabel={enforcing ? 'Cancelling...' : 'Cancel Exam'}
          confirmVariant="danger"
          confirmDisabled={enforcing}
          onConfirm={() => handleEnforce('CANCEL_EXAM')}
          onCancel={() => !enforcing && setPendingAction(null)}
        >
          <p>
            You are cancelling <strong>{event.student_full_name}</strong>&apos;s attempt at{' '}
            <strong>{event.exam_title}</strong>.
          </p>
          <ul className="small text-muted mb-2">
            <li>The session is ended immediately and marked as cancelled.</li>
            <li>The score is voided and recorded as 0.</li>
            <li>The student cannot retake this exam.</li>
            <li>This action cannot be undone.</li>
          </ul>
          <p className="mb-0 small">
            Reason: <em>{enforcementReason.trim()}</em>
          </p>
        </ConfirmModal>
      )}

      {pendingAction === 'UFM_CASE' && (
        <ConfirmModal
          title="File UFM Case?"
          confirmLabel={enforcing ? 'Filing...' : 'File Case'}
          confirmVariant="danger"
          confirmDisabled={enforcing}
          onConfirm={() => handleEnforce('UFM_CASE')}
          onCancel={() => !enforcing && setPendingAction(null)}
        >
          <p>
            You are filing an Unfair Means (UFM) case against{' '}
            <strong>{event.student_full_name}</strong> for <strong>{event.exam_title}</strong>.
          </p>
          <ul className="small text-muted mb-2">
            <li>A formal record is added to the student&apos;s academic file.</li>
            <li>The record is permanent and references this confirmed evidence.</li>
          </ul>
          <p className="mb-0 small">
            Reason: <em>{enforcementReason.trim()}</em>
          </p>
        </ConfirmModal>
      )}
    </div>
  )
}
