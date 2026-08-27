import apiClient from './client'

export async function listAuditLog({ action, page, pageSize } = {}) {
  const { data } = await apiClient.get('/api/audit', {
    params: {
      action: action || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}
