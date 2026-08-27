import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildAdminAlertsSocketUrl,
  connectAdminAlertsSocket,
  nextReconnectDelay,
  parseAdminAlertMessage,
} from '../adminAlertsSocket'

describe('buildAdminAlertsSocketUrl', () => {
  it('derives ws:// from an http:// base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('derives wss:// from an https:// base URL', () => {
    const url = buildAdminAlertsSocketUrl('https://api.example.com', 'abc123')
    expect(url).toBe('wss://api.example.com/ws/admin/alerts?token=abc123')
  })

  it('strips a trailing slash from the base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000/', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('strips multiple trailing slashes from the base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000//', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('URL-encodes the token', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000', 'a b+c/d')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=a%20b%2Bc%2Fd')
  })
})

describe('parseAdminAlertMessage', () => {
  it('accepts a well-formed monitoring_event payload', () => {
    const raw = JSON.stringify({
      type: 'monitoring_event',
      event_id: 1,
      session_id: 2,
      event_type: 'FACE_ABSENT',
      severity: 'high',
      status: 'PENDING_REVIEW',
    })

    expect(parseAdminAlertMessage(raw)).toEqual({
      type: 'monitoring_event',
      event_id: 1,
      session_id: 2,
      event_type: 'FACE_ABSENT',
      severity: 'high',
      status: 'PENDING_REVIEW',
    })
  })

  it('returns null for malformed JSON without throwing', () => {
    expect(() => parseAdminAlertMessage('{not valid json')).not.toThrow()
    expect(parseAdminAlertMessage('{not valid json')).toBeNull()
  })

  it('returns null for a non-object JSON value', () => {
    expect(parseAdminAlertMessage('"just a string"')).toBeNull()
    expect(parseAdminAlertMessage('42')).toBeNull()
    expect(parseAdminAlertMessage('null')).toBeNull()
  })

  it('ignores an unrelated message type', () => {
    const raw = JSON.stringify({ type: 'something_else', foo: 'bar' })
    expect(parseAdminAlertMessage(raw)).toBeNull()
  })
})

describe('nextReconnectDelay', () => {
  it.each([
    [0, 1000],
    [1, 2000],
    [2, 4000],
    [3, 8000],
    [4, 16000],
    [5, 30000],
    [6, 30000],
  ])('attempt %i -> %ims', (attempt, expected) => {
    expect(nextReconnectDelay(attempt)).toBe(expected)
  })
})

// A minimal hand-written fake -- no new dependency. Mirrors the native
// WebSocket surface the module under test actually touches (constructor
// taking a URL, .close(), and the four on* handler slots), and tracks
// every instance constructed so tests can assert how many sockets a
// controller created over time.
class FakeWebSocket {
  static instances = []

  constructor(url) {
    this.url = url
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    this.onclose = null
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.onclose?.({ type: 'close' })
  }
}

describe('connectAdminAlertsSocket', () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
  })

  afterEach(() => {
    // Fake timers are only enabled by the tests that need them, but this
    // must run unconditionally so no fake-timer state ever leaks into a
    // later test.
    vi.useRealTimers()
  })

  it('does not open a connection when no token is supplied', () => {
    expect(connectAdminAlertsSocket({ token: '', WebSocketImpl: FakeWebSocket })).toBeNull()
    expect(connectAdminAlertsSocket({ WebSocketImpl: FakeWebSocket })).toBeNull()
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('creates exactly one WebSocket immediately for the initial connection', () => {
    connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('forwards onopen and resets the retry attempt', () => {
    const onOpen = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onOpen, WebSocketImpl: FakeWebSocket })
    const event = { type: 'open' }

    FakeWebSocket.instances[0].onopen(event)

    expect(onOpen).toHaveBeenCalledWith(event)
  })

  it('parses and forwards a valid monitoring_event message', () => {
    const onMessage = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onMessage, WebSocketImpl: FakeWebSocket })
    const payload = {
      type: 'monitoring_event',
      event_id: 1,
      session_id: 2,
      event_type: 'FACE_ABSENT',
      severity: 'high',
      status: 'PENDING_REVIEW',
    }

    FakeWebSocket.instances[0].onmessage({ data: JSON.stringify(payload) })

    expect(onMessage).toHaveBeenCalledWith(payload)
  })

  it('does not throw and does not forward malformed JSON', () => {
    const onMessage = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onMessage, WebSocketImpl: FakeWebSocket })

    expect(() =>
      FakeWebSocket.instances[0].onmessage({ data: '{not valid json' })
    ).not.toThrow()
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('ignores an unrelated message type', () => {
    const onMessage = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onMessage, WebSocketImpl: FakeWebSocket })

    FakeWebSocket.instances[0].onmessage({ data: JSON.stringify({ type: 'something_else' }) })

    expect(onMessage).not.toHaveBeenCalled()
  })

  it('forwards onerror to the caller without scheduling a reconnect itself', () => {
    vi.useFakeTimers()
    const onError = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onError, WebSocketImpl: FakeWebSocket })
    const error = { type: 'error' }

    FakeWebSocket.instances[0].onerror(error)
    expect(onError).toHaveBeenCalledWith(error)

    // Only onclose schedules a reconnect -- an error alone, with no
    // accompanying close, must never create a new socket.
    vi.advanceTimersByTime(60000)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('forwards onclose to the caller', () => {
    vi.useFakeTimers()
    const onClose = vi.fn()
    connectAdminAlertsSocket({ token: 'abc', onClose, WebSocketImpl: FakeWebSocket })
    const event = { type: 'close' }

    FakeWebSocket.instances[0].onclose(event)

    expect(onClose).toHaveBeenCalledWith(event)
  })

  it('schedules a reconnect exactly 1 second after an unexpected close', () => {
    vi.useFakeTimers()
    connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })

    FakeWebSocket.instances[0].onclose({ type: 'close' })

    vi.advanceTimersByTime(999)
    expect(FakeWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('follows the full exponential backoff sequence: 1s, 2s, 4s, 8s, 16s, 30s, 30s', () => {
    vi.useFakeTimers()
    connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })

    const expectedDelays = [1000, 2000, 4000, 8000, 16000, 30000, 30000]
    expectedDelays.forEach((delay, index) => {
      expect(FakeWebSocket.instances).toHaveLength(index + 1)
      FakeWebSocket.instances[index].onclose({ type: 'close' })
      vi.advanceTimersByTime(delay)
    })

    expect(FakeWebSocket.instances).toHaveLength(expectedDelays.length + 1)
  })

  it('resets the backoff to 1s after a successful reconnect', () => {
    vi.useFakeTimers()
    connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })

    // First failure -> 1s -> reconnect.
    FakeWebSocket.instances[0].onclose({ type: 'close' })
    vi.advanceTimersByTime(1000)
    expect(FakeWebSocket.instances).toHaveLength(2)

    // That reconnect succeeds.
    FakeWebSocket.instances[1].onopen({ type: 'open' })

    // A later failure must wait 1s again, not 2s.
    FakeWebSocket.instances[1].onclose({ type: 'close' })
    vi.advanceTimersByTime(999)
    expect(FakeWebSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(3)
  })

  it('cancels a pending reconnect when close() is called', () => {
    vi.useFakeTimers()
    const controller = connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })
    FakeWebSocket.instances[0].onclose({ type: 'close' })

    controller.close()
    vi.advanceTimersByTime(60000)

    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('does not schedule a reconnect for an intentional close', () => {
    vi.useFakeTimers()
    const controller = connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })

    controller.close() // closes the underlying fake socket, firing its onclose

    vi.advanceTimersByTime(60000)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('is safe to call close() more than once', () => {
    const controller = connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })

    expect(() => {
      controller.close()
      controller.close()
    }).not.toThrow()
  })

  it('never has more than one active socket in flight from a single controller', () => {
    vi.useFakeTimers()
    connectAdminAlertsSocket({ token: 'abc', WebSocketImpl: FakeWebSocket })
    expect(FakeWebSocket.instances).toHaveLength(1)

    FakeWebSocket.instances[0].onclose({ type: 'close' })
    // Not enough time has passed for the reconnect timer to fire yet, so
    // no second socket should exist during the wait.
    vi.advanceTimersByTime(500)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })
})
