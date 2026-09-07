import apiClient from './client'

// Voiding withdraws a record from every queue, count and report without
// destroying it. System-administrator only, and each call carries the
// acting administrator's own password -- an admin session alone is not
// enough (see backend/app/api/routes/void.py).
//
// The password is passed straight through to the request body and is never
// stored, logged, or held in component state beyond the dialog that
// collected it.

export async function voidMonitoringEvent(eventId, { password, reason }) {
  const { data } = await apiClient.post(`/api/admin/void/events/${eventId}`, {
    password,
    reason,
  })
  return data
}

export async function voidExam(examId, { password, reason }) {
  const { data } = await apiClient.post(`/api/admin/void/exams/${examId}`, {
    password,
    reason,
  })
  return data
}

// Everything currently withdrawn from the visible record. The counterpart
// to voiding: without this, voiding would be indistinguishable from
// deletion to anyone auditing the system.
export async function listVoidedRecords() {
  const { data } = await apiClient.get('/api/admin/void')
  return data
}
