import apiClient from './client'

export async function fetchDashboardSummary() {
  const { data } = await apiClient.get('/api/admin/dashboard/summary')
  return data
}
