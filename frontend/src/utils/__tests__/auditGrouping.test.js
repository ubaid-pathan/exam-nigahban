import { describe, expect, it } from 'vitest'
import { groupAuditEntriesBySession } from '../auditGrouping'

const entry = (id, sessionId, action = 'CONFIRMED', overrides = {}) => ({
  id,
  session_id: sessionId,
  action,
  student_id: `STU-${sessionId}`,
  student_full_name: `Student ${sessionId}`,
  exam_id: sessionId,
  exam_title: `Exam ${sessionId}`,
  admin_username: 'admin1',
  reason: null,
  created_at: '2026-09-06T12:00:00',
  event_type: 'FACE_ABSENT',
  severity: 'high',
  ...overrides,
})

describe('groupAuditEntriesBySession', () => {
  it('returns an empty list for empty or missing input', () => {
    expect(groupAuditEntriesBySession([])).toEqual([])
    expect(groupAuditEntriesBySession(undefined)).toEqual([])
  })

  it('collects every decision for one session into a single group', () => {
    const groups = groupAuditEntriesBySession([
      entry(1, 42),
      entry(2, 42, 'IGNORED'),
      entry(3, 42),
    ])
    expect(groups).toHaveLength(1)
    expect(groups[0].entries).toHaveLength(3)
    expect(groups[0].sessionId).toBe(42)
  })

  it('never merges decisions from different sessions', () => {
    const groups = groupAuditEntriesBySession([entry(1, 42), entry(2, 43)])
    expect(groups).toHaveLength(2)
    expect(groups.map((g) => g.sessionId)).toEqual([42, 43])
  })

  it('keeps every individual decision, losing none', () => {
    const entries = [entry(1, 42), entry(2, 43), entry(3, 42), entry(4, 44)]
    const kept = groupAuditEntriesBySession(entries).flatMap((g) => g.entries)
    expect(kept).toHaveLength(4)
    expect(kept.map((e) => e.id).sort()).toEqual([1, 2, 3, 4])
  })

  it('counts confirmed and ignored decisions per session', () => {
    const groups = groupAuditEntriesBySession([
      entry(1, 42, 'CONFIRMED'),
      entry(2, 42, 'IGNORED'),
      entry(3, 42, 'CONFIRMED'),
    ])
    expect(groups[0].confirmedCount).toBe(2)
    expect(groups[0].ignoredCount).toBe(1)
  })

  it('preserves the API ordering between and within groups', () => {
    const groups = groupAuditEntriesBySession([entry(9, 43), entry(8, 42), entry(7, 43)])
    expect(groups.map((g) => g.sessionId)).toEqual([43, 42])
    expect(groups[0].entries.map((e) => e.id)).toEqual([9, 7])
  })

  it('carries the student and exam context onto the group', () => {
    const [group] = groupAuditEntriesBySession([entry(1, 42)])
    expect(group.studentFullName).toBe('Student 42')
    expect(group.studentId).toBe('STU-42')
    expect(group.examTitle).toBe('Exam 42')
  })

  it('does not mutate the input entries', () => {
    const entries = [entry(1, 42)]
    const snapshot = JSON.parse(JSON.stringify(entries))
    groupAuditEntriesBySession(entries)
    expect(entries).toEqual(snapshot)
  })
})
