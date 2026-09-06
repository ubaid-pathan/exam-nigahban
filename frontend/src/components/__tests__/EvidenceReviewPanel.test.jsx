import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import EvidenceReviewPanel from '../EvidenceReviewPanel'

// renderToStaticMarkup does not run effects, so the evidence-image and
// prior-enforcement fetches never fire here -- this asserts the panel's
// initial, pre-fetch markup only. That is exactly the surface that matters
// for the gating rule below, and it needs no DOM/jsdom environment or
// extra test dependency (same approach the admin alert indicator used).
function render(event) {
  return renderToStaticMarkup(
    <EvidenceReviewPanel
      event={event}
      onClose={() => {}}
      onReviewed={() => {}}
      onRefresh={() => {}}
    />,
  )
}

const baseEvent = {
  id: 1,
  evidence_id: 9,
  session_id: 42,
  student_id: '101',
  student_full_name: 'Ali Khan',
  exam_title: 'CS',
  event_type: 'FACE_ABSENT',
  severity: 'high',
  confidence: 1,
  duration_seconds: 5.13,
  detected_at: '2026-09-06T12:28:00',
  status: 'PENDING_REVIEW',
}

describe('EvidenceReviewPanel enforcement gating', () => {
  it('hides the enforcement ladder while the event is pending review', () => {
    const html = render(baseEvent)
    expect(html).not.toContain('Pause Exam')
    expect(html).not.toContain('Cancel Exam')
    expect(html).not.toContain('File UFM Case')
  })

  it('hides the enforcement ladder for an ignored event', () => {
    const html = render({ ...baseEvent, status: 'IGNORED' })
    expect(html).not.toContain('Pause Exam')
    expect(html).not.toContain('File UFM Case')
  })

  it('shows the full enforcement ladder once the event is confirmed', () => {
    const html = render({ ...baseEvent, status: 'CONFIRMED' })
    expect(html).toContain('Pause Exam')
    expect(html).toContain('Cancel Exam')
    expect(html).toContain('File UFM Case')
  })

  it('requires an enforcement reason field alongside the ladder', () => {
    const html = render({ ...baseEvent, status: 'CONFIRMED' })
    expect(html).toContain('Reason (required)')
  })
})

describe('EvidenceReviewPanel review controls', () => {
  it('offers Confirm while the event is still pending', () => {
    const html = render(baseEvent)
    expect(html).toContain('Confirm')
    expect(html).toContain('Mark Ignored')
  })

  it('replaces Confirm with Done for an already-confirmed event', () => {
    const html = render({ ...baseEvent, status: 'CONFIRMED' })
    expect(html).toContain('Done')
  })

  it('offers the optional review reason box before a decision is recorded', () => {
    expect(render(baseEvent)).toContain('Reason (optional)')
  })

  it('renders the event detail the admin reviews against', () => {
    const html = render(baseEvent)
    expect(html).toContain('Ali Khan')
    expect(html).toContain('Face Absent')
    expect(html).toContain('High')
    expect(html).toContain('Pending Review')
    expect(html).toContain('5.13s')
  })

  it('never uses cheating or guilt wording', () => {
    const html = render({ ...baseEvent, status: 'CONFIRMED' }).toLowerCase()
    for (const banned of ['cheat', 'guilty', 'culprit']) {
      expect(html).not.toContain(banned)
    }
  })
})
