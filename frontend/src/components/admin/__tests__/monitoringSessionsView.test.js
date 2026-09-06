import { describe, expect, it } from 'vitest'
import { fullPageState } from '../MonitoringSessionsView'

// Regression cover for a bug that was invisible from this view's own
// markup: the session rollup renders the Evidence Review dialog, and
// confirming an event triggers a background refetch. While the guard was
// `if (loading) return <LoadingState/>`, that refetch replaced the whole
// subtree -- dialog included -- so the dialog unmounted mid-review and the
// enforcement ladder could never be reached from here, even though the
// identical dialog worked from the flat events list.
const SOME_DATA = { items: [], page: 1, total: 0, total_pages: 0 }

describe('fullPageState', () => {
  it('shows the spinner on a first load, when there is nothing yet', () => {
    expect(fullPageState({ loading: true, error: '', data: null })).toBe('loading')
  })

  it('shows the error state on a first load that failed', () => {
    expect(fullPageState({ loading: false, error: 'boom', data: null })).toBe('error')
  })

  it('does NOT replace the view while refetching with data on screen', () => {
    // The regression itself: this is the state during a post-review
    // refetch, and returning 'loading' here unmounts the open dialog.
    expect(fullPageState({ loading: true, error: '', data: SOME_DATA })).toBeNull()
  })

  it('does NOT replace the view when a refetch fails with data on screen', () => {
    expect(fullPageState({ loading: false, error: 'boom', data: SOME_DATA })).toBeNull()
  })

  it('replaces nothing once loaded successfully', () => {
    expect(fullPageState({ loading: false, error: '', data: SOME_DATA })).toBeNull()
  })

  it('prefers the spinner over the error state on a first load', () => {
    expect(fullPageState({ loading: true, error: 'stale', data: null })).toBe('loading')
  })

  it('treats an empty result as data, not as nothing to show', () => {
    // An empty roster is a real answer and renders its own empty state --
    // it must not be mistaken for "still loading".
    expect(fullPageState({ loading: false, error: '', data: SOME_DATA })).toBeNull()
  })
})
