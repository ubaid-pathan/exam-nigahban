import { useEffect, useState } from 'react'
import { fetchEvidenceImageBlob, reviewEvidence } from '../api/evidence'
import { createEnforcementAction, listEnforcementActions } from '../api/enforcement'
import {
  actionTypeBadgeClass,
  actionTypeLabel,
  enforcementStatusBadgeClass,
  enforcementStatusLabel,
} from '../utils/enforcementStatus'
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
//
// Confirming happens IN PLACE: the panel stays open and reveals the
// enforcement section, rather than closing and forcing the admin to find
// and reopen the same event just to act on it. The human-gating rule is
// unchanged by this -- enforcement still appears only once the server has
// actually recorded a CONFIRMED decision, never on the strength of a
// client-side guess.
//
// `onReviewed` means "finished with this event -- close and refetch";
// `onRefresh` means "the list is stale, refetch it but leave me open".
export default function EvidenceReviewPanel({ event, onClose, onReviewed, onRefresh }) {
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

  // The status the SERVER returned for a decision recorded in this panel,
  // or null before any. Held locally because `event` is a row from the
  // parent's list fetch and keeps its original status until that list
  // reloads -- this is what lets the panel reflect the new decision (and
  // reveal enforcement) without closing. Never set optimistically: only
  // ever assigned from a successful review response.
  const [reviewedStatus, setReviewedStatus] = useState(null)
  const [reviewedReason, setReviewedReason] = useState('')

  // Enforcement already recorded against this student's session, so an
  // admin can see that the exam is (for example) already paused before
  // stacking a second action on top of it.
  const [priorActions, setPriorActions] = useState([])
  const [priorActionsError, setPriorActionsError] = useState('')

  const effectiveStatus = reviewedStatus ?? event.status
  const isConfirmed = effectiveStatus === 'CONFIRMED'

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

  // Read-only context load. A failure here must never block reviewing or
  // enforcing -- it only hides the history strip and says so.
  const loadPriorActions = async (signal) => {
    try {
      const data = await listEnforcementActions({
        sessionId: event.session_id,
        page: 1,
        pageSize: 10,
      })
      if (!signal.cancelled) {
        setPriorActions(data?.items ?? [])
        setPriorActionsError('')
      }
    } catch (err) {
      if (!signal.cancelled) {
        setPriorActions([])
        setPriorActionsError(
          getErrorMessage(err, 'Unable to load previous enforcement actions for this session.'),
        )
      }
    }
  }

  useEffect(() => {
    const signal = { cancelled: false }
    loadPriorActions(signal)
    return () => {
      signal.cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.session_id])

  const handleReview = async (action) => {
    setSubmitting(true)
    setSubmitError('')
    try {
      const result = await reviewEvidence(event.evidence_id, action, reason.trim() || undefined)

      if (action === 'CONFIRMED') {
        // Stay open on the server's actual resulting status so the
        // enforcement ladder becomes reachable for the violation the admin
        // is already looking at, instead of making them reopen it. The
        // list behind the panel is refreshed regardless, so it never shows
        // a stale PENDING_REVIEW row.
        setReviewedStatus(result?.status ?? 'CONFIRMED')
        setReviewedReason(reason.trim())
        setSubmitting(false)
        onRefresh?.()
        return
      }

      // IGNORED needs no follow-up action, so the review ends here: the
      // parent closes this panel and refetches, exactly as before.
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
                    <span className={`badge ${eventStatusBadgeClass(effectiveStatus)}`}>
                      {eventStatusLabel(effectiveStatus)}
                    </span>
                    {reviewedStatus && (
                      <span className="text-muted small ms-2">recorded just now</span>
                    )}
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

            {/* Once a decision is recorded the review reason becomes a
                read-only summary. Leaving it editable alongside the
                enforcement section's own required reason would put two
                near-identical boxes on screen with only one of them still
                doing anything. */}
            {reviewedStatus ? (
              <div className="mt-3 small">
                <span className="text-muted">Review reason: </span>
                {reviewedReason ? (
                  <span>{reviewedReason}</span>
                ) : (
                  <span className="text-muted fst-italic">none given</span>
                )}
              </div>
            ) : (
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
            )}

            {submitError && <p className="text-danger small mt-2 mb-0">{submitError}</p>}

            {/* Enforcement already on this session -- shown whatever the
                review status is, so an admin about to confirm can see the
                student is (say) already paused. Read-only. */}
            {priorActions.length > 0 && (
              <div className="mt-4 pt-3 border-top">
                <h3 className="h6 mb-2">Enforcement on this session</h3>
                <ul className="list-unstyled mb-0 d-flex flex-column gap-2">
                  {priorActions.map((action) => (
                    <li key={action.id} className="d-flex flex-wrap align-items-center gap-2 small">
                      <span className={`badge ${actionTypeBadgeClass(action.action_type)}`}>
                        {actionTypeLabel(action.action_type)}
                      </span>
                      <span className={`badge ${enforcementStatusBadgeClass(action.effective_status)}`}>
                        {enforcementStatusLabel(action.effective_status)}
                      </span>
                      <span className="text-muted">
                        by {action.admin_username} · {formatDateTimePKT(action.created_at)}
                      </span>
                      <span className="text-truncate" style={{ maxWidth: '100%' }}>
                        {action.reason}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {priorActionsError && (
              <p className="text-muted small mt-3 mb-0">{priorActionsError}</p>
            )}

            {isConfirmed && (
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
            {/* After a decision is recorded in this panel, "Confirm" would
                only append a duplicate audit row saying the same thing, so
                it is replaced by Done. Mark Ignored stays available: it is
                a genuine reversal, and the backend records it as another
                audit entry rather than editing the first. */}
            <button
              type="button"
              className="btn btn-outline-dark"
              onClick={() => handleReview('IGNORED')}
              disabled={submitting || enforcing}
            >
              {reviewedStatus ? 'Change to Ignored' : 'Mark Ignored'}
            </button>
            {isConfirmed ? (
              <button
                type="button"
                className="btn btn-success"
                onClick={() => onReviewed(null)}
                disabled={submitting || enforcing}
              >
                Done
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-success"
                onClick={() => handleReview('CONFIRMED')}
                disabled={submitting || enforcing}
              >
                Confirm
              </button>
            )}
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
