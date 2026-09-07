import { useState } from 'react'
import { getErrorMessage, getStatusCode } from '../../utils/apiError'

// Minimum matches VoidRequest.reason in backend/app/schemas/void.py. Checked
// here only so the dialog can explain the requirement before submitting --
// the server enforces it regardless.
const MIN_REASON_LENGTH = 10

// Confirmation for withdrawing a record from the visible system.
//
// Two things make this different from an ordinary confirm dialog, and both
// are deliberate:
//
//   * it asks for the administrator's own password, because an admin
//     session alone must not be enough to remove records from every queue
//     and report -- a stolen or unattended session cannot do this;
//   * it requires a written reason, which is kept permanently on the voided
//     record and is the only account of why something left the audit trail.
//
// The password lives in this component's state and nowhere else. It is
// passed to the request and discarded when the dialog closes; it is never
// lifted to a parent, stored, or logged.
export default function VoidConfirmDialog({
  title,
  recordLabel,
  consequences,
  onConfirm,
  onCancel,
  onVoided,
}) {
  const [password, setPassword] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const reasonIsUsable = reason.trim().length >= MIN_REASON_LENGTH
  const canSubmit = password.length > 0 && reasonIsUsable && !submitting

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setError('')
    try {
      const result = await onConfirm({ password, reason: reason.trim() })
      // Cleared before anything else happens, so the password does not
      // survive in state while the parent re-renders or refetches.
      setPassword('')
      onVoided?.(result)
    } catch (err) {
      const status = getStatusCode(err)
      if (status === 401) {
        setError('That password is not correct. Please try again.')
      } else if (status === 429) {
        // The server locks the action after repeated failures; its message
        // carries the retry window, so it is shown rather than replaced.
        setError(getErrorMessage(err, 'Too many incorrect attempts. Try again later.'))
      } else if (status === 409) {
        // Refused for a defensible reason -- most often that the record
        // supports enforcement still in force. Worth reading verbatim.
        setError(getErrorMessage(err, 'This record cannot be voided.'))
      } else {
        setError(getErrorMessage(err, 'Unable to void this record.'))
      }
      setPassword('')
      setSubmitting(false)
    }
  }

  return (
    <div
      className="modal-backdrop-manual"
      role="dialog"
      aria-modal="true"
      aria-labelledby="void-dialog-title"
    >
      <div className="modal-dialog" style={{ margin: 0, maxWidth: 'min(520px, 92vw)' }}>
        <div className="modal-content">
          <form onSubmit={handleSubmit}>
            <div className="modal-header">
              <h2 className="modal-title h5 mb-0" id="void-dialog-title">
                {title}
              </h2>
            </div>

            <div className="modal-body">
              <p className="mb-2">
                You are voiding <strong>{recordLabel}</strong>.
              </p>

              <ul className="small text-muted mb-3">
                {consequences.map((line) => (
                  <li key={line}>{line}</li>
                ))}
                <li>
                  The record is <strong>not deleted</strong>. It keeps your name, the
                  time, and your reason, and stays listed under Voided Records.
                </li>
              </ul>

              <div className="mb-3">
                <label htmlFor="void-reason" className="form-label small">
                  Reason (required, at least {MIN_REASON_LENGTH} characters)
                </label>
                <textarea
                  id="void-reason"
                  className="form-control form-control-sm"
                  rows={3}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  disabled={submitting}
                  maxLength={1000}
                  placeholder="This is kept permanently and is the only record of why this was withdrawn."
                />
                {reason.length > 0 && !reasonIsUsable && (
                  <p className="form-text text-muted mb-0">
                    {MIN_REASON_LENGTH - reason.trim().length} more character
                    {MIN_REASON_LENGTH - reason.trim().length === 1 ? '' : 's'} needed.
                  </p>
                )}
              </div>

              <div className="mb-2">
                <label htmlFor="void-password" className="form-label small">
                  Confirm your password
                </label>
                <input
                  id="void-password"
                  type="password"
                  className="form-control form-control-sm"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={submitting}
                  autoComplete="current-password"
                />
                <p className="form-text text-muted mb-0">
                  Your own password, re-entered so that an unattended session cannot
                  withdraw records.
                </p>
              </div>

              {error && (
                <div className="alert alert-danger py-2 small mb-0" role="alert">
                  {error}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onCancel}
                disabled={submitting}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-danger" disabled={!canSubmit}>
                {submitting ? 'Voiding...' : 'Void Record'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
