import { API_BASE_URL } from './client'

// Live channel telling a candidate their exam session changed, so an
// invigilator's pause, lift, or cancellation reaches them at once instead
// of on their next poll.
//
// The server sends only a nudge -- never the enforcement state itself (see
// backend/app/websocket/session_manager.py). The page responds by
// re-fetching the session, so enforcement is always applied from the
// authoritative API response through the same code path the polling
// fallback uses, and a replayed frame can never fake a pause.
//
// Structured to mirror api/adminAlertsSocket.js: same ws/wss derivation,
// same capped exponential backoff, same injectable WebSocketImpl for
// tests, and the same deferred-close handling for a socket that is still
// mid-handshake when the caller unmounts (React StrictMode's double-invoke
// in development makes that the common case, not an edge case).

const SESSION_UPDATED = 'session_updated'

function toWebSocketOrigin(httpOrigin) {
  if (httpOrigin.startsWith('https://')) {
    return `wss://${httpOrigin.slice('https://'.length)}`
  }
  if (httpOrigin.startsWith('http://')) {
    return `ws://${httpOrigin.slice('http://'.length)}`
  }
  return httpOrigin
}

export function buildStudentSessionSocketUrl(baseUrl, sessionId, token) {
  const origin = toWebSocketOrigin(baseUrl).replace(/\/+$/, '')
  return `${origin}/ws/student/sessions/${sessionId}?token=${encodeURIComponent(token)}`
}

// Returns true only for the one recognised message type. Anything else --
// malformed JSON, a non-object, a future message type, or a frame for a
// different session -- is ignored rather than triggering a resync.
export function isSessionUpdateMessage(rawData, sessionId) {
  let parsed
  try {
    parsed = JSON.parse(rawData)
  } catch {
    return false
  }
  if (!parsed || typeof parsed !== 'object' || parsed.type !== SESSION_UPDATED) {
    return false
  }
  return Number(parsed.session_id) === Number(sessionId)
}

// Exponential backoff capped at 15s. Shorter cap than the admin channel's
// 30s: a candidate mid-exam needs their connection back quickly, since it
// is what makes a pause visible without waiting for the poll.
export function nextReconnectDelay(attempt) {
  return Math.min(1000 * 2 ** attempt, 15000)
}

/**
 * Opens the session channel and calls `onSessionUpdate` whenever the
 * server says this session changed. Returns null without a token or
 * session id; otherwise a controller exposing close().
 */
export function connectStudentSessionSocket({
  sessionId,
  token,
  onSessionUpdate,
  onOpen,
  onClose,
  WebSocketImpl = WebSocket,
} = {}) {
  if (!token || !sessionId) {
    return null
  }

  let socket = null
  let attempt = 0
  let reconnectTimerId = null
  let stopped = false
  let closeRequested = false

  const scheduleReconnect = () => {
    if (stopped) return
    const delay = nextReconnectDelay(attempt)
    attempt += 1
    if (reconnectTimerId) clearTimeout(reconnectTimerId)
    reconnectTimerId = setTimeout(open, delay)
  }

  function open() {
    if (stopped) return
    reconnectTimerId = null
    closeRequested = false

    try {
      socket = new WebSocketImpl(
        buildStudentSessionSocketUrl(API_BASE_URL, sessionId, token),
      )
    } catch {
      scheduleReconnect()
      return
    }

    socket.onopen = (event) => {
      attempt = 0
      if (closeRequested) {
        socket.close()
        return
      }
      onOpen?.(event)
    }
    socket.onmessage = (event) => {
      if (stopped) return
      if (isSessionUpdateMessage(event.data, sessionId)) {
        onSessionUpdate?.()
      }
    }
    socket.onclose = (event) => {
      onClose?.(event)
      scheduleReconnect()
    }
    socket.onerror = () => {
      // A transient socket error must never disturb the exam. The close
      // handler above schedules the retry; polling covers the gap.
    }
  }

  open()

  return {
    close() {
      stopped = true
      if (reconnectTimerId) clearTimeout(reconnectTimerId)
      reconnectTimerId = null
      if (socket && socket.readyState === WebSocketImpl.CONNECTING) {
        closeRequested = true
        return
      }
      socket?.close()
    },
  }
}
