import apiClient from './client'

export async function listMonitoringEvents({
  status,
  severity,
  eventType,
  sessionId,
  page,
  pageSize,
} = {}) {
  const { data } = await apiClient.get('/api/monitoring/events', {
    params: {
      status: status || undefined,
      severity: severity || undefined,
      event_type: eventType || undefined,
      session_id: sessionId || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}

export async function postMonitoringEvent(sessionId, event) {
  const { data } = await apiClient.post('/api/monitoring/events', {
    session_id: sessionId,
    event_type: event.eventType,
    severity: event.severity,
    confidence: event.confidence,
    duration_seconds: event.durationSeconds,
    occurrences: event.occurrences,
    // Optional: omitted entirely (rather than sent as null) when capture
    // failed or was unavailable, keeping the request identical to the
    // pre-evidence payload shape in that case.
    ...(event.evidenceImageBase64 ? { evidence_image_base64: event.evidenceImageBase64 } : {}),
  })
  return data
}
