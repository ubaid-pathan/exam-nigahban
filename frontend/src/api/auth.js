import apiClient from './client'

export async function login(username, password) {
  const { data } = await apiClient.post('/api/auth/login', { username, password })
  return data
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get('/api/auth/me')
  return data
}

export async function logout() {
  const { data } = await apiClient.post('/api/auth/logout')
  return data
}
