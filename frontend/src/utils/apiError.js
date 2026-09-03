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

/** True when the backend returned 403 Forbidden -- the user is authenticated
 *  (has a valid token) but lacks the required role/permission.  Distinct from
 *  a 401 which the apiClient interceptor already handles (clears session). */
export function isForbiddenError(error) {
  return getStatusCode(error) === 403
}
