import apiClient from './client'

// The complete record of one student's exam session: flagged activities,
// the decisions taken on them, and any enforcement. Admin-only; the
// backend refuses this to a student (a candidate must never be able to
// read the case built about them).
export async function getSessionCaseReport(sessionId) {
  const { data } = await apiClient.get(`/api/reports/sessions/${sessionId}`)
  return data
}

// The program and section values that actually exist in the roster, so
// the report's filters offer real values rather than free text.
export async function getRosterFilterOptions() {
  const { data } = await apiClient.get('/api/reports/roster/filters')
  return data
}

function rosterParams({ department, className, examId, sessionStatus } = {}) {
  return {
    department: department || undefined,
    class_name: className || undefined,
    exam_id: examId || undefined,
    session_status: sessionStatus || undefined,
  }
}

// Monitoring outcomes across a cohort. Includes attempts that produced no
// flagged activity -- "monitored, nothing found" is a result the report
// has to be able to state.
export async function getRosterReport({ page, pageSize, ...filters } = {}) {
  const { data } = await apiClient.get('/api/reports/roster', {
    params: { ...rosterParams(filters), page, page_size: pageSize },
  })
  return data
}

// Downloads the roster as CSV.
//
// Fetched through apiClient as a blob rather than linked with a plain
// <a href>: the endpoint requires the same bearer auth as every other
// admin call, and a browser navigation cannot attach that header -- a
// direct link would simply 401. The object URL is revoked immediately
// after the click, since the browser has taken its own copy by then.
export async function downloadRosterCsv(filters = {}) {
  const { data, headers } = await apiClient.get('/api/reports/roster.csv', {
    params: rosterParams(filters),
    responseType: 'blob',
  })

  const disposition = headers?.['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : 'exam-nigahban-roster.csv'

  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
