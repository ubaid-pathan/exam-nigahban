// Displays AI-monitoring status using CLAUDE.md-approved terminology only.
// Never implies an autonomous cheating determination — this is a live
// system/observation status indicator, not a verdict.

const STATUS_TEXT = {
  idle: { label: 'Monitoring Inactive', variant: 'secondary' },
  'loading-model': { label: 'Initializing AI Monitoring...', variant: 'secondary' },
  running: { label: 'Monitoring Active', variant: 'success' },
  error: { label: 'AI Monitoring Unavailable', variant: 'warning' },
}

const OBSERVATION_TEXT = {
  'single-face': null,
  'no-face': { label: 'Face Not Visible', variant: 'warning' },
  'multiple-faces': { label: 'Multiple Faces Detected', variant: 'warning' },
}

export default function MonitoringStatusPanel({ status, observationStatus, errorMessage, cameraStatus }) {
  if (cameraStatus !== 'granted') {
    return (
      <div className="alert alert-secondary py-2 small mb-0" role="status">
        Camera access is required for AI-assisted monitoring during this exam.
      </div>
    )
  }

  const statusInfo = STATUS_TEXT[status] ?? STATUS_TEXT.idle
  const observationInfo = status === 'running' ? OBSERVATION_TEXT[observationStatus] : null

  return (
    <div className="d-flex flex-column gap-2">
      <div className="d-flex align-items-center gap-2">
        <span className={`badge text-bg-${statusInfo.variant}`}>{statusInfo.label}</span>
        {observationInfo && (
          <span className={`badge text-bg-${observationInfo.variant}`}>{observationInfo.label}</span>
        )}
      </div>
      {status === 'error' && (
        <p className="small text-muted mb-0">
          {errorMessage || 'AI monitoring could not start. Your exam is not affected.'}
        </p>
      )}
      <p className="small text-muted mb-0">
        Suspicious activity is recorded as evidence for administrator review. It is never an
        automatic determination of misconduct.
      </p>
    </div>
  )
}
