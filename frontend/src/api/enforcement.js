import apiClient from './client'

// Creates an enforcement action (BLOCK / CANCEL_EXAM / UFM_CASE) against a
// student's exam session. `payload` is already snake_case and matches the
// backend's EnforcementCreateRequest schema.
export async function createEnforcementAction(payload) {
  const { data } = await apiClient.post('/api/enforcement/actions', payload)
  return data
}

export async function listEnforcementActions({ actionType, status, sessionId, studentId, page, pageSize } = {}) {
  const { data } = await apiClient.get('/api/enforcement/actions', {
    params: {
      action_type: actionType || undefined,
      status: status || undefined,
      session_id: sessionId || undefined,
      student_id: studentId || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}

// Lifts an active BLOCK early, restoring the student's write access.
// Only BLOCK rows are liftable (the backend 409s otherwise).
export async function liftEnforcementAction(actionId) {
  const { data } = await apiClient.post(`/api/enforcement/actions/${actionId}/lift`)
  return data
}
