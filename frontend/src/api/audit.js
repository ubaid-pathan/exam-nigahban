import apiClient from './client'

export async function listAuditLog({ action, sessionId, page, pageSize } = {}) {
  const { data } = await apiClient.get('/api/audit', {
    params: {
      action: action || undefined,
      // Narrows to one student's exam session so the page can present all
      // decisions for that session together, while the backend keeps
      // returning them as the separate, individually attributable rows an
      // audit trail requires.
      session_id: sessionId || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}
