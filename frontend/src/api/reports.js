import apiClient from './client'

// The complete record of one student's exam session: flagged activities,
// the decisions taken on them, and any enforcement. Admin-only; the
// backend refuses this to a student (a candidate must never be able to
// read the case built about them).
export async function getSessionCaseReport(sessionId) {
  const { data } = await apiClient.get(`/api/reports/sessions/${sessionId}`)
  return data
}
