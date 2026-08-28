import apiClient from './client'

export async function listQuestions(examId) {
  const { data } = await apiClient.get(`/api/exams/${examId}/questions`)
  return data
}

export async function getQuestion(questionId) {
  const { data } = await apiClient.get(`/api/questions/${questionId}`)
  return data
}

export async function createQuestion(examId, payload) {
  const { data } = await apiClient.post(`/api/exams/${examId}/questions`, payload)
  return data
}

export async function updateQuestion(questionId, payload) {
  const { data } = await apiClient.put(`/api/questions/${questionId}`, payload)
  return data
}

export async function deleteQuestion(questionId) {
  await apiClient.delete(`/api/questions/${questionId}`)
}
