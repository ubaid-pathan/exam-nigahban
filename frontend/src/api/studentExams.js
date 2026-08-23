import apiClient from './client'

export async function listAvailableExams() {
  const { data } = await apiClient.get('/api/student/exams')
  return data
}

export async function getAvailableExam(examId) {
  const { data } = await apiClient.get(`/api/student/exams/${examId}`)
  return data
}

export async function startExam(examId) {
  const { data } = await apiClient.post(`/api/student/exams/${examId}/start`)
  return data
}

export async function getSession(sessionId) {
  const { data } = await apiClient.get(`/api/student/sessions/${sessionId}`)
  return data
}

export async function getSessionQuestions(sessionId) {
  const { data } = await apiClient.get(`/api/student/sessions/${sessionId}/questions`)
  return data
}

export async function getSessionAnswers(sessionId) {
  const { data } = await apiClient.get(`/api/student/sessions/${sessionId}/answers`)
  return data
}

export async function saveAnswer(sessionId, questionId, selectedAnswer) {
  const { data } = await apiClient.put(
    `/api/student/sessions/${sessionId}/answers/${questionId}`,
    { selected_answer: selectedAnswer },
  )
  return data
}

export async function submitExam(sessionId) {
  const { data } = await apiClient.post(`/api/student/sessions/${sessionId}/submit`)
  return data
}
