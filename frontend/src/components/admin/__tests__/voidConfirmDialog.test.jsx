import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import VoidConfirmDialog from '../VoidConfirmDialog'

// renderToStaticMarkup does not run effects or events, so this asserts the
// dialog's initial contract: the two things that must be collected before
// a record can be withdrawn, the consequences the administrator is shown,
// and that the confirm control starts disabled.
function render(props = {}) {
  return renderToStaticMarkup(
    <VoidConfirmDialog
      title="Void This Violation?"
      recordLabel="Face Absent for Ali Khan"
      consequences={['It leaves the review queue.', 'Its evidence is withdrawn with it.']}
      onConfirm={async () => ({})}
      onCancel={() => {}}
      {...props}
    />,
  )
}

describe('VoidConfirmDialog', () => {
  it('asks for the administrator password as a password field', () => {
    const html = render()
    expect(html).toContain('type="password"')
    expect(html).toContain('Confirm your password')
  })

  it('explains why the password is being asked for', () => {
    // Without the reason stated, re-entering a password on a page you are
    // already signed into looks like a bug rather than a safeguard.
    expect(render()).toContain('unattended session')
  })

  it('requires a written reason and states the minimum', () => {
    const html = render()
    expect(html).toContain('Reason (required, at least 10 characters)')
  })

  it('starts with the confirm control disabled', () => {
    // Nothing has been entered yet, so voiding must not be one click away.
    const html = render()
    const confirmIndex = html.indexOf('Void Record')
    const buttonStart = html.lastIndexOf('<button', confirmIndex)
    expect(html.slice(buttonStart, confirmIndex)).toContain('disabled')
  })

  it('lists the consequences it was given', () => {
    const html = render()
    expect(html).toContain('It leaves the review queue.')
    expect(html).toContain('Its evidence is withdrawn with it.')
  })

  it('always states that the record is not deleted', () => {
    // The distinction between voiding and deletion is the whole point; it
    // must not depend on the caller remembering to pass it in.
    const html = render({ consequences: [] })
    expect(html).toContain('not deleted')
    expect(html).toContain('Voided Records')
  })

  it('names the record being voided', () => {
    expect(render()).toContain('Face Absent for Ali Khan')
  })

  it('never uses cheating or guilt wording', () => {
    const html = render().toLowerCase()
    for (const banned of ['cheat', 'guilty', 'culprit']) {
      expect(html).not.toContain(banned)
    }
  })
})
