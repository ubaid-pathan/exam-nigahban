import apiClient from './client'

export async function postMonitoringEvent(sessionId, event) {
  const { data } = await apiClient.post('/api/monitoring/events', {
    session_id: sessionId,
    event_type: event.eventType,
    severity: event.severity,
    confidence: event.confidence,
    duration_seconds: event.durationSeconds,
    occurrences: event.occurrences,
  })
  return data
}
