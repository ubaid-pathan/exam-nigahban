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
