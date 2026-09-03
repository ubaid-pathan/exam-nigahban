import apiClient from './client'

export async function listAdmins({ search, page, pageSize } = {}) {
  const { data } = await apiClient.get('/api/users/admins', {
    params: {
      search: search || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}

export async function getAdmin(userId) {
  const { data } = await apiClient.get(`/api/users/admins/${userId}`)
  return data
}

export async function createAdmin({ username, password, fullName, email }) {
  const { data } = await apiClient.post('/api/users/admins', {
    username,
    password,
    full_name: fullName || undefined,
    email: email || undefined,
  })
  return data
}

export async function updateAdminStatus(userId, isActive) {
  const { data } = await apiClient.patch(`/api/users/admins/${userId}/status`, {
    status: isActive,
  })
  return data
}
