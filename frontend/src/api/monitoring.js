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
    // Optional: omitted entirely (rather than sent as e.g. undefined) when
    // the detector didn't set one, so a MediaPipe event's request body
    // stays byte-identical to before this field existed (Milestone 6 Phase
    // 2 Step 5/6) and the backend's own "browser_mediapipe" default (see
    // backend/app/schemas/monitoring.py) keeps applying exactly as before.
    // useMobilePhoneMonitoring.js sets event.source = 'browser_yolox'.
    ...(event.source ? { source: event.source } : {}),
    // Optional: omitted entirely (rather than sent as null) when capture
    // failed or was unavailable, keeping the request identical to the
    // pre-evidence payload shape in that case.
    ...(event.evidenceImageBase64 ? { evidence_image_base64: event.evidenceImageBase64 } : {}),
  })
  return data
}
