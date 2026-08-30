import { describe, expect, it } from 'vitest'
import { buildPhoneActiveConditions } from '../phoneObservation'

describe('buildPhoneActiveConditions - active-condition mapping', () => {
  it('returns a set containing MOBILE_PHONE when a phone was detected', () => {
    const conditions = buildPhoneActiveConditions({ phoneDetected: true })
    expect(conditions).toEqual(new Set(['MOBILE_PHONE']))
  })

  it('returns an empty set when no phone was detected', () => {
    const conditions = buildPhoneActiveConditions({ phoneDetected: false })
    expect(conditions).toEqual(new Set())
  })

  it('always returns a Set instance', () => {
    expect(buildPhoneActiveConditions({ phoneDetected: true })).toBeInstanceOf(Set)
    expect(buildPhoneActiveConditions({ phoneDetected: false })).toBeInstanceOf(Set)
  })
})
