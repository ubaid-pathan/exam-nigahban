export const SESSION_STATUS_LABELS = {
  in_progress: 'In Progress',
  submitted: 'Completed',
  expired: 'Expired',
}

export const SESSION_STATUS_BADGE_CLASS = {
  in_progress: 'text-bg-warning',
  submitted: 'text-bg-success',
  expired: 'text-bg-danger',
}

export function sessionStatusLabel(status) {
  return SESSION_STATUS_LABELS[status] || 'Not Started'
}

export function sessionStatusBadgeClass(status) {
  return SESSION_STATUS_BADGE_CLASS[status] || 'text-bg-secondary'
}
