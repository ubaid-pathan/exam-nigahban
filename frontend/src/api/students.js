import apiClient from './client'

export async function listStudents({ search, page, pageSize } = {}) {
  const { data } = await apiClient.get('/api/users/students', {
    params: {
      search: search || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}

export async function getStudent(studentId) {
  const { data } = await apiClient.get(`/api/users/students/${studentId}`)
  return data
}

export async function createStudent({
  username,
  password,
  studentId,
  fullName,
  email,
  department,
  className,
}) {
  const { data } = await apiClient.post('/api/users/students', {
    username,
    password,
    student_id: studentId,
    full_name: fullName,
    email: email || undefined,
    department: department || undefined,
    class_name: className || undefined,
  })
  return data
}

export async function updateStudent(studentId, { fullName, department, className }) {
  const { data } = await apiClient.put(`/api/users/students/${studentId}`, {
    full_name: fullName,
    department: department || undefined,
    class_name: className || undefined,
  })
  return data
}

export async function updateStudentStatus(studentId, isActive) {
  const { data } = await apiClient.patch(`/api/users/students/${studentId}/status`, {
    is_active: isActive,
  })
  return data
}
