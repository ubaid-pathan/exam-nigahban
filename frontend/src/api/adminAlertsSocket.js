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

// Exponential backoff, capped at 30s: 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
export function nextReconnectDelay(attempt) {
  return Math.min(1000 * 2 ** attempt, 30000)
}

// Opens the admin alerts WebSocket using the given JWT, wiring the native
// open/message/error/close events to the supplied callbacks, and
// automatically reconnects (with exponential backoff, capped at 30s, no
// retry limit) after any unexpected closure. Returns null when no token
// is supplied; otherwise returns a controller object exposing close(),
// which permanently stops the connection (and any pending reconnect) and
// is safe to call more than once -- this preserves the exact shape
// AdminLayout already calls (`socket?.close()`), so it requires no change.
//
// WebSocketImpl exists only so tests can inject a fake WebSocket without
// adding a testing dependency; production callers never need to pass it.
export function connectAdminAlertsSocket({
  token,
  onOpen,
  onMessage,
  onError,
  onClose,
  WebSocketImpl = WebSocket,
} = {}) {
  if (!token) {
    return null
  }

  let socket = null
  let attempt = 0
  let reconnectTimerId = null
  let stopped = false

  const scheduleReconnect = () => {
    if (stopped) {
      return
    }
    const delay = nextReconnectDelay(attempt)
    attempt += 1
    if (reconnectTimerId) {
      clearTimeout(reconnectTimerId)
    }
    reconnectTimerId = setTimeout(open, delay)
  }

  const open = () => {
    if (stopped) {
      return
    }
    reconnectTimerId = null

    try {
      socket = new WebSocketImpl(buildAdminAlertsSocketUrl(API_BASE_URL, token))
    } catch (error) {
      onError?.(error)
      scheduleReconnect()
      return
    }

    socket.onopen = (event) => {
      attempt = 0
      onOpen?.(event)
    }
    socket.onerror = (event) => onError?.(event)
    socket.onmessage = (event) => {
      const message = parseAdminAlertMessage(event.data)
      if (message) {
        onMessage?.(message)
      }
    }
    // Reconnection is scheduled only from onclose -- a failed connection
    // always proceeds to a close event, so scheduling here too would
    // double-schedule.
    socket.onclose = (event) => {
      onClose?.(event)
      scheduleReconnect()
    }
  }

  open()

  return {
    close() {
      stopped = true
      if (reconnectTimerId) {
        clearTimeout(reconnectTimerId)
      }
      reconnectTimerId = null
      socket?.close()
    },
  }
}
