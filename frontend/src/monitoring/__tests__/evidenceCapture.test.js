import { describe, expect, it } from 'vitest'
import { computeCaptureDimensions, extractBase64FromDataUrl } from '../evidenceCapture'

describe('computeCaptureDimensions', () => {
  it('returns null for missing/zero dimensions', () => {
    expect(computeCaptureDimensions(0, 0)).toBeNull()
    expect(computeCaptureDimensions(undefined, undefined)).toBeNull()
    expect(computeCaptureDimensions(640, 0)).toBeNull()
  })

  it('leaves dimensions unchanged when already at or below maxWidth', () => {
    expect(computeCaptureDimensions(480, 360, 480)).toEqual({ width: 480, height: 360 })
    expect(computeCaptureDimensions(320, 240, 480)).toEqual({ width: 320, height: 240 })
  })

  it('downscales proportionally when wider than maxWidth', () => {
    // 1280x720 at maxWidth 480 -> scale 0.375 -> 480x270
    expect(computeCaptureDimensions(1280, 720, 480)).toEqual({ width: 480, height: 270 })
  })

  it('never scales up', () => {
    expect(computeCaptureDimensions(240, 180, 480)).toEqual({ width: 240, height: 180 })
  })
})

describe('extractBase64FromDataUrl', () => {
  it('extracts the base64 payload from a data URL', () => {
    expect(extractBase64FromDataUrl('data:image/jpeg;base64,ABCD1234==')).toBe('ABCD1234==')
  })

  it('returns null for a non-data-URL string', () => {
    expect(extractBase64FromDataUrl('not-a-data-url')).toBeNull()
  })

  it('returns null for a data URL with an empty payload', () => {
    expect(extractBase64FromDataUrl('data:image/jpeg;base64,')).toBeNull()
  })

  it('returns null for non-string input', () => {
    expect(extractBase64FromDataUrl(null)).toBeNull()
    expect(extractBase64FromDataUrl(undefined)).toBeNull()
  })
})
