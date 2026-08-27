import { API_BASE_URL } from './client'

const ADMIN_ALERTS_PATH = '/ws/admin/alerts'

// http:// -> ws://, https:// -> wss://. Anything else is returned
// unchanged rather than guessed at.
function toWebSocketOrigin(httpOrigin) {
  if (httpOrigin.startsWith('https://')) {
    return `wss://${httpOrigin.slice('https://'.length)}`
  }
  if (httpOrigin.startsWith('http://')) {
    return `ws://${httpOrigin.slice('http://'.length)}`
  }
  return httpOrigin
}

export function buildAdminAlertsSocketUrl(baseUrl, token) {
  const origin = toWebSocketOrigin(baseUrl).replace(/\/+$/, '')
  return `${origin}${ADMIN_ALERTS_PATH}?token=${encodeURIComponent(token)}`
}

// Accepts the raw event.data from a WebSocket "message" event and returns
// the parsed monitoring_event payload, or null if the data is not valid
// JSON, not an object, or not a monitoring_event -- callers never need to
// guard against a malformed/unexpected message themselves.
export function parseAdminAlertMessage(rawData) {
  let parsed
  try {
    parsed = JSON.parse(rawData)
  } catch {
    return null
  }

  if (!parsed || typeof parsed !== 'object' || parsed.type !== 'monitoring_event') {
    return null
  }

  return parsed
}

// Opens the admin alerts WebSocket using the given JWT, wiring the native
// open/message/error/close events to the supplied callbacks. Returns null
// (and never throws) when no token is supplied or the socket can't be
// constructed, so callers can always call `.close()` on the result via
// optional chaining without an extra null check.
export function connectAdminAlertsSocket({ token, onOpen, onMessage, onError, onClose } = {}) {
  if (!token) {
    return null
  }

  let socket
  try {
    socket = new WebSocket(buildAdminAlertsSocketUrl(API_BASE_URL, token))
  } catch (error) {
    onError?.(error)
    return null
  }

  socket.onopen = (event) => onOpen?.(event)
  socket.onerror = (event) => onError?.(event)
  socket.onclose = (event) => onClose?.(event)
  socket.onmessage = (event) => {
    const message = parseAdminAlertMessage(event.data)
    if (message) {
      onMessage?.(message)
    }
  }

  return socket
}
