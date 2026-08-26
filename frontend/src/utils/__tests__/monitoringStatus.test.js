import { describe, expect, it } from 'vitest'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  severityBadgeClass,
  severityLabel,
} from '../monitoringStatus'

describe('eventStatusLabel', () => {
  it('labels PENDING_REVIEW', () => {
    expect(eventStatusLabel('PENDING_REVIEW')).toBe('Pending Review')
  })

  it('labels CONFIRMED', () => {
    expect(eventStatusLabel('CONFIRMED')).toBe('Confirmed')
  })

  it('labels IGNORED', () => {
    expect(eventStatusLabel('IGNORED')).toBe('Ignored')
  })

  it('never renders cheating-related wording for any known status', () => {
    for (const status of ['PENDING_REVIEW', 'CONFIRMED', 'IGNORED']) {
      const label = eventStatusLabel(status).toLowerCase()
      expect(label).not.toContain('cheat')
      expect(label).not.toContain('guilty')
    }
  })

  it('falls back to the raw value for an unknown status', () => {
    expect(eventStatusLabel('SOMETHING_ELSE')).toBe('SOMETHING_ELSE')
  })

  it('falls back to "Unknown" for a falsy status', () => {
    expect(eventStatusLabel(undefined)).toBe('Unknown')
    expect(eventStatusLabel('')).toBe('Unknown')
  })
})

describe('eventStatusBadgeClass', () => {
  it('maps PENDING_REVIEW to a warning badge', () => {
    expect(eventStatusBadgeClass('PENDING_REVIEW')).toBe('text-bg-warning')
  })

  it('maps CONFIRMED to a danger badge', () => {
    expect(eventStatusBadgeClass('CONFIRMED')).toBe('text-bg-danger')
  })

  it('maps IGNORED to a secondary badge', () => {
    expect(eventStatusBadgeClass('IGNORED')).toBe('text-bg-secondary')
  })

  it('falls back to a secondary badge for an unknown status', () => {
    expect(eventStatusBadgeClass('SOMETHING_ELSE')).toBe('text-bg-secondary')
    expect(eventStatusBadgeClass(undefined)).toBe('text-bg-secondary')
  })
})

describe('severityLabel', () => {
  it('labels low', () => {
    expect(severityLabel('low')).toBe('Low')
  })

  it('labels medium', () => {
    expect(severityLabel('medium')).toBe('Medium')
  })

  it('labels high', () => {
    expect(severityLabel('high')).toBe('High')
  })

  it('falls back to the raw value for an unknown severity', () => {
    expect(severityLabel('critical')).toBe('critical')
  })

  it('falls back to "Unknown" for a falsy severity', () => {
    expect(severityLabel(undefined)).toBe('Unknown')
    expect(severityLabel('')).toBe('Unknown')
  })
})

describe('severityBadgeClass', () => {
  it('maps low to a secondary badge', () => {
    expect(severityBadgeClass('low')).toBe('text-bg-secondary')
  })

  it('maps medium to a warning badge', () => {
    expect(severityBadgeClass('medium')).toBe('text-bg-warning')
  })

  it('maps high to a danger badge', () => {
    expect(severityBadgeClass('high')).toBe('text-bg-danger')
  })

  it('falls back to a secondary badge for an unknown severity', () => {
    expect(severityBadgeClass('critical')).toBe('text-bg-secondary')
    expect(severityBadgeClass(undefined)).toBe('text-bg-secondary')
  })
})
