import { describe, expect, it } from 'vitest'
import {
  sessionAlertLevel,
  sortEventTypeCounts,
  studentInitials,
} from '../monitoringStatus'

describe('sortEventTypeCounts', () => {
  it('orders the busiest activity first', () => {
    const result = sortEventTypeCounts({
      LOOKING_AWAY: 1,
      FACE_ABSENT: 3,
      MOBILE_PHONE: 2,
    })
    expect(result.map((r) => r.type)).toEqual([
      'FACE_ABSENT',
      'MOBILE_PHONE',
      'LOOKING_AWAY',
    ])
  })

  it('breaks ties alphabetically so the order is stable across refetches', () => {
    const result = sortEventTypeCounts({ MOBILE_PHONE: 2, FACE_ABSENT: 2, HEAD_UP: 2 })
    expect(result.map((r) => r.type)).toEqual(['FACE_ABSENT', 'HEAD_UP', 'MOBILE_PHONE'])
  })

  it('attaches the human-readable label for each activity', () => {
    const [first] = sortEventTypeCounts({ FACE_ABSENT: 1 })
    expect(first).toEqual({ type: 'FACE_ABSENT', label: 'Face Absent', count: 1 })
  })

  it('drops zero counts and handles empty or missing input', () => {
    expect(sortEventTypeCounts({ FACE_ABSENT: 0, MOBILE_PHONE: 1 })).toHaveLength(1)
    expect(sortEventTypeCounts({})).toEqual([])
    expect(sortEventTypeCounts(undefined)).toEqual([])
  })
})

describe('sessionAlertLevel', () => {
  it('is critical when high-severity violations still await review', () => {
    expect(sessionAlertLevel({ pending_events: 2, high_severity_events: 1 })).toBe(
      'critical',
    )
  })

  it('is pending when review is outstanding but nothing is high severity', () => {
    expect(sessionAlertLevel({ pending_events: 3, high_severity_events: 0 })).toBe(
      'pending',
    )
  })

  it('is clear once every violation has been reviewed', () => {
    expect(sessionAlertLevel({ pending_events: 0, high_severity_events: 4 })).toBe(
      'clear',
    )
  })

  it('does not treat already-reviewed high-severity activity as critical', () => {
    // The whole point: a session can contain high-severity violations that
    // an admin has already dealt with -- that must not keep shouting.
    expect(sessionAlertLevel({ pending_events: 0, high_severity_events: 10 })).toBe(
      'clear',
    )
  })

  it('handles missing fields and missing input', () => {
    expect(sessionAlertLevel({})).toBe('clear')
    expect(sessionAlertLevel(undefined)).toBe('clear')
  })
})

describe('studentInitials', () => {
  it('uses first and last name initials', () => {
    expect(studentInitials('Ali Khan')).toBe('AK')
    expect(studentInitials('Muhammad Bilal Ahmed')).toBe('MA')
  })

  it('uses the first two letters of a single name', () => {
    expect(studentInitials('Zara')).toBe('ZA')
  })

  it('tolerates extra whitespace', () => {
    expect(studentInitials('  Ali   Khan  ')).toBe('AK')
  })

  it('falls back for empty or missing names', () => {
    expect(studentInitials('')).toBe('?')
    expect(studentInitials('   ')).toBe('?')
    expect(studentInitials(undefined)).toBe('?')
  })
})
