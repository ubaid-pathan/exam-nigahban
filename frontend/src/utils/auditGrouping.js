// Pure grouping helper for the Audit History page.
//
// The audit log is deliberately stored and returned as one row per admin
// decision: each is a separate act by a named person at a named moment,
// and collapsing those rows would destroy the attribution that makes the
// log defensible if a student contests a UFM case. This groups them for
// DISPLAY only -- every decision survives intact inside its group.

/**
 * Groups audit entries by exam session, preserving the order the API
 * returned them in (newest first) both between groups and within each
 * group. Never mutates the input.
 */
export function groupAuditEntriesBySession(entries) {
  const order = []
  const bySession = new Map()

  for (const entry of entries || []) {
    if (!bySession.has(entry.session_id)) {
      order.push(entry.session_id)
      bySession.set(entry.session_id, {
        sessionId: entry.session_id,
        studentId: entry.student_id,
        studentFullName: entry.student_full_name,
        examId: entry.exam_id,
        examTitle: entry.exam_title,
        entries: [],
        confirmedCount: 0,
        ignoredCount: 0,
      })
    }
    const group = bySession.get(entry.session_id)
    group.entries.push(entry)
    if (entry.action === 'CONFIRMED') group.confirmedCount += 1
    if (entry.action === 'IGNORED') group.ignoredCount += 1
  }

  return order.map((sessionId) => bySession.get(sessionId))
}
