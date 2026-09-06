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

/**
 * Turns a session rollup's `events_by_type` map into a display-ordered
 * list of { type, label, count }, busiest activity first and ties broken
 * alphabetically so the order is stable across refetches.
 *
 * Pure, so the ordering rule the admin UI depends on is testable without
 * rendering anything.
 */
export function sortEventTypeCounts(eventsByType) {
  return Object.entries(eventsByType || {})
    .filter(([, count]) => count > 0)
    .sort(([typeA, countA], [typeB, countB]) =>
      countB - countA || typeA.localeCompare(typeB),
    )
    .map(([type, count]) => ({ type, label: eventTypeLabel(type), count }))
}

/**
 * How urgently a session rollup needs an invigilator's attention.
 *
 *   'critical' - high-severity violations are still awaiting review
 *   'pending'  - violations await review, none of them high severity
 *   'clear'    - every violation in this session has been reviewed
 *
 * Pure, and separate from the rendering, so the triage rule the admin
 * screen sorts its visual weight by is testable on its own.
 */
export function sessionAlertLevel(session) {
  const pending = session?.pending_events ?? 0
  if (pending === 0) return 'clear'
  // high_severity_events counts high-severity violations in the session,
  // which may already have been reviewed -- so a session is only critical
  // when it has BOTH high-severity activity and outstanding review work.
  return (session?.high_severity_events ?? 0) > 0 ? 'critical' : 'pending'
}

/**
 * Two-letter initials for a student's name, used by the roster-style
 * avatar on the session rollup. Falls back to '?' for an empty name.
 */
export function studentInitials(fullName) {
  const parts = String(fullName || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}
