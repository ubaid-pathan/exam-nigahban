import { describe, expect, it, vi } from 'vitest'
import {
  buildStudentSessionSocketUrl,
  connectStudentSessionSocket,
  isSessionUpdateMessage,
  nextReconnectDelay,
} from '../studentSessionSocket'

// Minimal fake matching the parts of the WebSocket API this client uses,
// injected via WebSocketImpl so no browser or extra test dependency is
// needed -- the same approach api/__tests__/adminAlertsSocket.test.js uses.
class FakeWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = FakeWebSocket.CONNECTING
    this.closed = false
    FakeWebSocket.instances.push(this)
  }

  open() {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.({})
  }

  message(data) {
    this.onmessage?.({ data })
  }

  close() {
    this.closed = true
    this.onclose?.({})
  }
}

function freshSocket() {
  FakeWebSocket.instances = []
  return FakeWebSocket
}

describe('buildStudentSessionSocketUrl', () => {
  it('maps http to ws and https to wss', () => {
    expect(buildStudentSessionSocketUrl('http://localhost:8000', 7, 'tok')).toBe(
      'ws://localhost:8000/ws/student/sessions/7?token=tok',
    )
    expect(buildStudentSessionSocketUrl('https://api.example.com', 7, 'tok')).toBe(
      'wss://api.example.com/ws/student/sessions/7?token=tok',
    )
  })

  it('strips trailing slashes and encodes the token', () => {
    expect(buildStudentSessionSocketUrl('http://localhost:8000//', 3, 'a b/c')).toBe(
      'ws://localhost:8000/ws/student/sessions/3?token=a%20b%2Fc',
    )
  })
})

describe('isSessionUpdateMessage', () => {
  const valid = JSON.stringify({ type: 'session_updated', session_id: 7 })

  it('accepts a session_updated frame for this session', () => {
    expect(isSessionUpdateMessage(valid, 7)).toBe(true)
    // Session ids arriving as strings must still match.
    expect(isSessionUpdateMessage(valid, '7')).toBe(true)
  })

  it('ignores a frame for a different session', () => {
    expect(isSessionUpdateMessage(valid, 8)).toBe(false)
  })

  it('ignores malformed JSON, non-objects and unknown types', () => {
    expect(isSessionUpdateMessage('{not json', 7)).toBe(false)
    expect(isSessionUpdateMessage('"a string"', 7)).toBe(false)
    expect(isSessionUpdateMessage('null', 7)).toBe(false)
    expect(
      isSessionUpdateMessage(JSON.stringify({ type: 'something_new', session_id: 7 }), 7),
    ).toBe(false)
  })
})

describe('nextReconnectDelay', () => {
  it('backs off exponentially and caps at 15s', () => {
    expect(nextReconnectDelay(0)).toBe(1000)
    expect(nextReconnectDelay(1)).toBe(2000)
    expect(nextReconnectDelay(3)).toBe(8000)
    expect(nextReconnectDelay(10)).toBe(15000)
  })
})

describe('connectStudentSessionSocket', () => {
  it('returns null without a token or a session id', () => {
    expect(connectStudentSessionSocket({ sessionId: 7 })).toBeNull()
    expect(connectStudentSessionSocket({ token: 'tok' })).toBeNull()
    expect(connectStudentSessionSocket()).toBeNull()
  })

  it('calls onSessionUpdate for a matching frame', () => {
    const Impl = freshSocket()
    const onSessionUpdate = vi.fn()
    connectStudentSessionSocket({
      sessionId: 7,
      token: 'tok',
      onSessionUpdate,
      WebSocketImpl: Impl,
    })

    const socket = Impl.instances[0]
    socket.open()
    socket.message(JSON.stringify({ type: 'session_updated', session_id: 7 }))

    expect(onSessionUpdate).toHaveBeenCalledTimes(1)
  })

  it('ignores frames for another candidate’s session', () => {
    const Impl = freshSocket()
    const onSessionUpdate = vi.fn()
    connectStudentSessionSocket({
      sessionId: 7,
      token: 'tok',
      onSessionUpdate,
      WebSocketImpl: Impl,
    })

    Impl.instances[0].open()
    Impl.instances[0].message(JSON.stringify({ type: 'session_updated', session_id: 99 }))

    expect(onSessionUpdate).not.toHaveBeenCalled()
  })

  it('stops delivering updates after close()', () => {
    const Impl = freshSocket()
    const onSessionUpdate = vi.fn()
    const controller = connectStudentSessionSocket({
      sessionId: 7,
      token: 'tok',
      onSessionUpdate,
      WebSocketImpl: Impl,
    })

    const socket = Impl.instances[0]
    socket.open()
    controller.close()
    socket.message(JSON.stringify({ type: 'session_updated', session_id: 7 }))

    expect(onSessionUpdate).not.toHaveBeenCalled()
    expect(socket.closed).toBe(true)
  })

  it('defers closing a socket that is still connecting, then closes on open', () => {
    const Impl = freshSocket()
    const onOpen = vi.fn()
    const controller = connectStudentSessionSocket({
      sessionId: 7,
      token: 'tok',
      onOpen,
      WebSocketImpl: Impl,
    })

    const socket = Impl.instances[0]
    // Still CONNECTING: closing now would abort the handshake, which is
    // what produces the browser's "closed before established" warning.
    controller.close()
    expect(socket.closed).toBe(false)

    socket.open()
    expect(socket.closed).toBe(true)
    // The caller had already given up, so onOpen must not fire.
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('does not reconnect after an intentional close', () => {
    vi.useFakeTimers()
    const Impl = freshSocket()
    const controller = connectStudentSessionSocket({
      sessionId: 7,
      token: 'tok',
      WebSocketImpl: Impl,
    })

    Impl.instances[0].open()
    controller.close()
    vi.advanceTimersByTime(60000)

    expect(Impl.instances).toHaveLength(1)
    vi.useRealTimers()
  })

  it('reconnects after an unexpected drop', () => {
    vi.useFakeTimers()
    const Impl = freshSocket()
    connectStudentSessionSocket({ sessionId: 7, token: 'tok', WebSocketImpl: Impl })

    Impl.instances[0].open()
    Impl.instances[0].close() // server-side drop
    vi.advanceTimersByTime(1000)

    expect(Impl.instances.length).toBeGreaterThan(1)
    vi.useRealTimers()
  })
})
