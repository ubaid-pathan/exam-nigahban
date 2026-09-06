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

// The message types broadcast on the admin alerts channel. Kept as an
// explicit allow-list so a new/unknown backend message type is still
// dropped rather than forwarded to every admin page.
const ADMIN_ALERT_MESSAGE_TYPES = new Set(['monitoring_event', 'enforcement_action'])

// Accepts the raw event.data from a WebSocket "message" event and returns
// the parsed admin-alert payload, or null if the data is not valid JSON,
// not an object, or not a recognized admin-alert message type -- callers
// never need to guard against a malformed/unexpected message themselves.
export function parseAdminAlertMessage(rawData) {
  let parsed
  try {
    parsed = JSON.parse(rawData)
  } catch {
    return null
  }

  if (!parsed || typeof parsed !== 'object' || !ADMIN_ALERT_MESSAGE_TYPES.has(parsed.type)) {
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
  // Set when close() is called while the current socket is still mid
  // handshake (readyState CONNECTING). Calling the native close() in that
  // state aborts the handshake and is what makes the browser log "WebSocket
  // is closed before the connection is established" -- most visible under
  // React StrictMode, which runs an effect, its cleanup, and the effect
  // again, back to back, before the first socket has had a chance to open.
  // Deferring the actual close until onopen avoids the warning entirely
  // instead of merely hiding it.
  let closeRequested = false

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
    closeRequested = false

    try {
      socket = new WebSocketImpl(buildAdminAlertsSocketUrl(API_BASE_URL, token))
    } catch (error) {
      onError?.(error)
      scheduleReconnect()
      return
    }

    socket.onopen = (event) => {
      attempt = 0
      if (closeRequested) {
        // close() was requested while this socket was still connecting;
        // finish the handshake cleanly and close it now instead of having
        // aborted it mid-flight. The caller never asked to be connected to
        // begin with, so onOpen must not fire for it.
        socket.close()
        return
      }
      onOpen?.(event)
    }
    socket.onerror = (event) => {
      if (stopped) {
        return
      }
      onError?.(event)
    }
    socket.onmessage = (event) => {
      if (stopped) {
        return
      }
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
      if (socket && socket.readyState === WebSocketImpl.CONNECTING) {
        closeRequested = true
        return
      }
      socket?.close()
    },
  }
}
