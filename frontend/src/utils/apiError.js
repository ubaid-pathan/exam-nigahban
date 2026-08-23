export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (error?.message === 'Network Error' || !error?.response) {
    return 'Unable to reach the server. Please check your connection and try again.'
  }
  return fallback
}

export function getStatusCode(error) {
  return error?.response?.status ?? null
}
