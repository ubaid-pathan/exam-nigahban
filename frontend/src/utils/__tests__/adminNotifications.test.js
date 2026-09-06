import { describe, expect, it } from 'vitest'
import {
  MAX_NOTIFICATIONS,
  NOTIFICATIONS_STORAGE_KEY,
  addNotification,
  clearStoredNotifications,
  formatAge,
  loadStoredNotifications,
  markAllRead,
  removeNotification,
  saveStoredNotifications,
  toNotification,
  unreadCount,
} from '../adminNotifications'

// Minimal in-memory stand-in for window.localStorage, plus a variant that
// throws on every operation (private windows / blocked site data) so the
// helpers' tolerance of unavailable storage is actually exercised.
function fakeStorage(initial = {}) {
  const data = { ...initial }
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v)
    },
    removeItem: (k) => {
      delete data[k]
    },
    _data: data,
  }
}

const throwingStorage = {
  getItem() {
    throw new Error('blocked')
  },
  setItem() {
    throw new Error('blocked')
  },
  removeItem() {
    throw new Error('blocked')
  },
}

const monitoringMessage = {
  type: 'monitoring_event',
  event_id: 1,
  session_id: 42,
  event_type: 'FACE_ABSENT',
  severity: 'high',
  status: 'PENDING_REVIEW',
}

const enforcementMessage = {
  type: 'enforcement_action',
  action_id: 7,
  session_id: 42,
  student_id: 3,
  action_type: 'CANCEL_EXAM',
  status: 'COMPLETED',
}

describe('toNotification', () => {
  it('maps a monitoring event to a labelled notification', () => {
    const n = toNotification(monitoringMessage, 1000)
    expect(n.id).toBe('event:1')
    expect(n.kind).toBe('monitoring_event')
    expect(n.severity).toBe('high')
    expect(n.title).toBe('Face Absent')
    expect(n.to).toBe('/admin/monitoring')
    expect(n.read).toBe(false)
    expect(n.receivedAt).toBe(1000)
  })

  it('includes severity and review status in the monitoring detail line', () => {
    expect(toNotification(monitoringMessage).detail).toBe('High severity · Pending Review')
  })

  it('maps an enforcement action and links to the enforcement log', () => {
    const n = toNotification(enforcementMessage, 2000)
    expect(n.id).toBe('enforcement:7')
    expect(n.kind).toBe('enforcement_action')
    expect(n.title).toBe('Cancel Exam')
    expect(n.detail).toBe('Enforcement · Completed')
    expect(n.to).toBe('/admin/enforcement')
    expect(n.severity).toBeNull()
  })

  it('reports the originating session as context', () => {
    expect(toNotification(monitoringMessage).context).toBe('Session 42')
  })

  it('never uses cheating/guilt wording in any produced label', () => {
    const text = [
      toNotification(monitoringMessage),
      toNotification(enforcementMessage),
    ]
      .flatMap((n) => [n.title, n.detail, n.context])
      .join(' ')
      .toLowerCase()
    for (const banned of ['cheat', 'guilty', 'culprit']) {
      expect(text).not.toContain(banned)
    }
  })

  it('returns null for unknown, malformed or empty messages', () => {
    expect(toNotification(null)).toBeNull()
    expect(toNotification(undefined)).toBeNull()
    expect(toNotification('a string')).toBeNull()
    expect(toNotification({ type: 'something_new', id: 1 })).toBeNull()
  })
})

describe('addNotification', () => {
  it('prepends so the newest alert is first', () => {
    const a = toNotification(monitoringMessage, 1)
    const b = toNotification(enforcementMessage, 2)
    expect(addNotification(addNotification([], a), b).map((n) => n.id)).toEqual([
      'enforcement:7',
      'event:1',
    ])
  })

  it('replaces a repeat of the same id instead of duplicating it', () => {
    const first = toNotification(monitoringMessage, 1)
    const updated = toNotification({ ...monitoringMessage, status: 'CONFIRMED' }, 5)
    const list = addNotification(addNotification([], first), updated)
    expect(list).toHaveLength(1)
    expect(list[0].detail).toContain('Confirmed')
  })

  it('caps the list at MAX_NOTIFICATIONS, dropping the oldest', () => {
    let list = []
    for (let i = 0; i < MAX_NOTIFICATIONS + 8; i += 1) {
      list = addNotification(list, toNotification({ ...monitoringMessage, event_id: i }, i))
    }
    expect(list).toHaveLength(MAX_NOTIFICATIONS)
    expect(list[0].id).toBe(`event:${MAX_NOTIFICATIONS + 7}`)
  })

  it('ignores a null notification and never mutates the input list', () => {
    const original = [toNotification(monitoringMessage, 1)]
    const snapshot = [...original]
    expect(addNotification(original, null)).toBe(original)
    addNotification(original, toNotification(enforcementMessage, 2))
    expect(original).toEqual(snapshot)
  })
})

describe('read state', () => {
  it('counts only unread entries', () => {
    const list = [
      toNotification(monitoringMessage, 1),
      { ...toNotification(enforcementMessage, 2), read: true },
    ]
    expect(unreadCount(list)).toBe(1)
  })

  it('markAllRead clears the count without removing entries', () => {
    const list = markAllRead([
      toNotification(monitoringMessage, 1),
      toNotification(enforcementMessage, 2),
    ])
    expect(unreadCount(list)).toBe(0)
    expect(list).toHaveLength(2)
  })

  it('markAllRead does not mutate the input', () => {
    const original = [toNotification(monitoringMessage, 1)]
    markAllRead(original)
    expect(original[0].read).toBe(false)
  })

  it('handles empty and missing lists', () => {
    expect(unreadCount([])).toBe(0)
    expect(unreadCount(undefined)).toBe(0)
    expect(markAllRead(undefined)).toEqual([])
  })
})

describe('removeNotification', () => {
  it('removes only the matching entry', () => {
    const list = [
      toNotification(monitoringMessage, 1),
      toNotification(enforcementMessage, 2),
    ]
    expect(removeNotification(list, 'event:1').map((n) => n.id)).toEqual(['enforcement:7'])
  })

  it('is a no-op for an unknown id', () => {
    const list = [toNotification(monitoringMessage, 1)]
    expect(removeNotification(list, 'event:999')).toHaveLength(1)
  })
})

describe('persistence', () => {
  it('round-trips through storage', () => {
    const storage = fakeStorage()
    const list = [toNotification(monitoringMessage, 1)]
    saveStoredNotifications(storage, list)
    expect(loadStoredNotifications(storage)).toEqual(list)
  })

  it('returns an empty list when nothing is stored', () => {
    expect(loadStoredNotifications(fakeStorage())).toEqual([])
  })

  it('returns an empty list for invalid JSON or a non-array value', () => {
    expect(loadStoredNotifications(fakeStorage({ [NOTIFICATIONS_STORAGE_KEY]: '{oops' }))).toEqual([])
    expect(loadStoredNotifications(fakeStorage({ [NOTIFICATIONS_STORAGE_KEY]: '"a string"' }))).toEqual([])
  })

  it('drops malformed entries rather than rendering blank rows', () => {
    const storage = fakeStorage({
      [NOTIFICATIONS_STORAGE_KEY]: JSON.stringify([
        toNotification(monitoringMessage, 1),
        { nope: true },
        null,
      ]),
    })
    expect(loadStoredNotifications(storage)).toHaveLength(1)
  })

  it('clearStoredNotifications empties the stored queue', () => {
    const storage = fakeStorage()
    saveStoredNotifications(storage, [toNotification(monitoringMessage, 1)])
    clearStoredNotifications(storage)
    expect(loadStoredNotifications(storage)).toEqual([])
  })

  it('never throws when storage is unavailable', () => {
    expect(loadStoredNotifications(throwingStorage)).toEqual([])
    expect(() => saveStoredNotifications(throwingStorage, [])).not.toThrow()
    expect(() => clearStoredNotifications(throwingStorage)).not.toThrow()
    expect(loadStoredNotifications(undefined)).toEqual([])
  })
})

describe('formatAge', () => {
  it('reports very recent alerts as "just now"', () => {
    expect(formatAge(1_000_000, 1_000_000)).toBe('just now')
    expect(formatAge(1_000_000, 1_030_000)).toBe('just now')
  })

  it('reports minutes, hours and days', () => {
    expect(formatAge(0, 5 * 60_000)).toBe('5m')
    expect(formatAge(0, 3 * 3_600_000)).toBe('3h')
    expect(formatAge(0, 2 * 86_400_000)).toBe('2d')
  })

  it('never reports a negative age from a skewed clock', () => {
    expect(formatAge(2_000_000, 1_000_000)).toBe('just now')
  })
})
