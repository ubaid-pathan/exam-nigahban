import apiClient from './client'

export async function checkApiHealth() {
  const { data } = await apiClient.get('/health')
  return data
}
