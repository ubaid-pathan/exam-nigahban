// Terminology follows CLAUDE.md's monitoring-language rules: the AI never
// confirms cheating, so labels describe review state only ("Pending
// Review", "Confirmed", "Ignored") -- never "cheating", "cheater", or
// "guilty" wording of any kind.
export const EVENT_STATUS_LABELS = {
  PENDING_REVIEW: 'Pending Review',
  CONFIRMED: 'Confirmed',
  IGNORED: 'Ignored',
}

export const EVENT_STATUS_BADGE_CLASS = {
  PENDING_REVIEW: 'text-bg-warning',
  CONFIRMED: 'text-bg-danger',
  IGNORED: 'text-bg-secondary',
}

export const SEVERITY_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

export const SEVERITY_BADGE_CLASS = {
  low: 'text-bg-secondary',
  medium: 'text-bg-warning',
  high: 'text-bg-danger',
}

export function eventStatusLabel(status) {
  return EVENT_STATUS_LABELS[status] || status || 'Unknown'
}

export function eventStatusBadgeClass(status) {
  return EVENT_STATUS_BADGE_CLASS[status] || 'text-bg-secondary'
}

export function severityLabel(severity) {
  return SEVERITY_LABELS[severity] || severity || 'Unknown'
}

export function severityBadgeClass(severity) {
  return SEVERITY_BADGE_CLASS[severity] || 'text-bg-secondary'
}

// Human-readable labels for the raw event_type identifiers the backend
// sends/expects (see monitoring/constants.js MONITORING_RULES and
// MOBILE_PHONE_RULE) -- display-only. The identifiers themselves are never
// changed: every filter value, API param, and stored event still uses
// these exact strings.
export const EVENT_TYPE_LABELS = {
  HEAD_LEFT: 'Head Left',
  HEAD_RIGHT: 'Head Right',
  HEAD_UP: 'Head Up',
  HEAD_DOWN: 'Head Down',
  LOOKING_AWAY: 'Looking Away',
  FACE_ABSENT: 'Face Absent',
  MULTIPLE_FACES: 'Multiple Faces',
  MOBILE_PHONE: 'Mobile Phone',
}

export function eventTypeLabel(type) {
  return EVENT_TYPE_LABELS[type] || type || 'Unknown'
}
