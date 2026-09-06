import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import LiveAlertIndicator from '../LiveAlertIndicator'

// react-dom/server's renderToStaticMarkup and react-router-dom's
// MemoryRouter are both already-installed dependencies of this project --
// this lets the component's actual JSX output be asserted on without
// pulling in React Testing Library or a DOM/jsdom test environment.
function renderIndicator(latestAlert) {
  return renderToStaticMarkup(
    <MemoryRouter>
      <LiveAlertIndicator latestAlert={latestAlert} />
    </MemoryRouter>
  )
}

describe('LiveAlertIndicator', () => {
  it('renders nothing when latestAlert is null', () => {
    expect(renderIndicator(null)).toBe('')
  })

  it('renders nothing when latestAlert is undefined', () => {
    expect(renderIndicator(undefined)).toBe('')
  })

  const alert = {
    type: 'monitoring_event',
    event_id: 1,
    session_id: 2,
    event_type: 'FACE_ABSENT',
    severity: 'high',
    status: 'PENDING_REVIEW',
  }

  it('renders the severity label for a valid alert', () => {
    expect(renderIndicator(alert)).toContain('High')
  })

  it('renders the raw event_type for a valid alert', () => {
    expect(renderIndicator(alert)).toContain('FACE_ABSENT')
  })

  it('renders the status label for a valid alert', () => {
    expect(renderIndicator(alert)).toContain('Pending Review')
  })

  it('renders the severity and status badge classes, not just plain text', () => {
    const html = renderIndicator(alert)
    expect(html).toContain('text-bg-danger') // severityBadgeClass('high')
    expect(html).toContain('text-bg-warning') // eventStatusBadgeClass('PENDING_REVIEW')
  })

  it('links to /admin/monitoring', () => {
    expect(renderIndicator(alert)).toContain('href="/admin/monitoring"')
  })

  it('uses role="status", not role="alert"', () => {
    const html = renderIndicator(alert)
    expect(html).toContain('role="status"')
    expect(html).not.toContain('role="alert"')
  })

  const enforcementAction = {
    type: 'enforcement_action',
    action_id: 7,
    session_id: 2,
    student_id: 3,
    action_type: 'BLOCK',
    status: 'ACTIVE',
  }

  it('renders the action type label for an enforcement action alert', () => {
    expect(renderIndicator(enforcementAction)).toContain('Block')
  })

  it('renders the status label for an enforcement action alert', () => {
    expect(renderIndicator(enforcementAction)).toContain('Active')
  })

  it('links an enforcement action alert to /admin/enforcement', () => {
    expect(renderIndicator(enforcementAction)).toContain('href="/admin/enforcement"')
  })

  it('renders an enforcement action alert with role="status"', () => {
    const html = renderIndicator(enforcementAction)
    expect(html).toContain('role="status"')
    expect(html).not.toContain('role="alert"')
  })
})
