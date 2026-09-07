// Labels for admin enforcement actions (see backend
// app/models/enforcement_action.py and app/schemas/enforcement.py).
// Terminology follows the project's monitoring-language rules: labels
// describe the action and its state only -- never "cheating", "cheater",
// or "guilty" wording of any kind.

// The three proportionate actions an admin may take after reviewing
// evidence, ordered by severity: BLOCK (reversible pause) < CANCEL_EXAM
// (terminal, score voided) < UFM_CASE (formal academic record).
export const ACTION_TYPE_LABELS = {
  BLOCK: 'Block',
  CANCEL_EXAM: 'Cancel Exam',
  UFM_CASE: 'UFM Case',
}

export const ACTION_TYPE_BADGE_CLASSES = {
  BLOCK: 'text-bg-warning',
  CANCEL_EXAM: 'text-bg-danger',
  UFM_CASE: 'text-bg-dark',
}

export function actionTypeLabel(actionType) {
  return ACTION_TYPE_LABELS[actionType] || actionType || 'Unknown'
}

export function actionTypeBadgeClass(actionType) {
  return ACTION_TYPE_BADGE_CLASSES[actionType] || 'text-bg-secondary'
}

// Effective status is computed server-side: a BLOCK past its deadline
// reports EXPIRED even though its stored status stays ACTIVE forever
// (append-only audit trail); LIFTED marks an admin-terminated block;
// CANCEL_EXAM and UFM_CASE rows are COMPLETED at creation.
export const ENFORCEMENT_STATUS_LABELS = {
  ACTIVE: 'Active',
  EXPIRED: 'Expired',
  LIFTED: 'Lifted',
  COMPLETED: 'Completed',
}

export const ENFORCEMENT_STATUS_BADGE_CLASSES = {
  ACTIVE: 'text-bg-warning',
  EXPIRED: 'text-bg-secondary',
  LIFTED: 'text-bg-secondary',
  COMPLETED: 'text-bg-secondary',
}

export function enforcementStatusLabel(status) {
  return ENFORCEMENT_STATUS_LABELS[status] || status || 'Unknown'
}

export function enforcementStatusBadgeClass(status) {
  return ENFORCEMENT_STATUS_BADGE_CLASSES[status] || 'text-bg-secondary'
}
