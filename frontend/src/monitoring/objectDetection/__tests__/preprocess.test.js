// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/__tests__/preprocess.test.js -- no
// test change.

import { describe, expect, it } from 'vitest'
import { boxToSourcePixels, computeLetterboxLayout } from '../preprocess'

// Only the pure, DOM-free functions are tested here (matching this
// project's existing convention of not introducing jsdom/RTL for a canvas-
// dependent function -- see evidenceCapture.test.js for the same pattern).

describe('computeLetterboxLayout', () => {
  it('returns null for invalid dimensions', () => {
    expect(computeLetterboxLayout(0, 100)).toBeNull()
    expect(computeLetterboxLayout(100, 0)).toBeNull()
    expect(computeLetterboxLayout(null, 100)).toBeNull()
  })

  it('scales a square image to exactly fill 320x320', () => {
    const layout = computeLetterboxLayout(1000, 1000, 320)
    expect(layout.ratio).toBeCloseTo(0.32, 5)
    expect(layout.resizedWidth).toBe(320)
    expect(layout.resizedHeight).toBe(320)
  })

  it('uses min(scaleX, scaleY) so a wide image is height-fit, not width-fit', () => {
    // 1280x853, matching the genuine Milestone 1 positive sample's dimensions.
    const layout = computeLetterboxLayout(1280, 853, 320)
    expect(layout.ratio).toBeCloseTo(320 / 1280, 5)
    expect(layout.resizedWidth).toBe(320)
    expect(layout.resizedHeight).toBeLessThan(320)
  })

  it('is top-left aligned (zero offset), matching YOLOX preproc, not centered', () => {
    const layout = computeLetterboxLayout(1280, 853, 320)
    expect(layout.offsetX).toBe(0)
    expect(layout.offsetY).toBe(0)
  })

  it('never scales up a small image beyond its own resolution needs', () => {
    const layout = computeLetterboxLayout(100, 50, 320)
    expect(layout.ratio).toBeCloseTo(3.2, 5)
    expect(layout.resizedWidth).toBe(320)
    expect(layout.resizedHeight).toBe(160)
  })
})

describe('boxToSourcePixels', () => {
  it('maps a letterboxed-space box back to original-image pixels by dividing by ratio', () => {
    const layout = { ratio: 0.25, offsetX: 0, offsetY: 0 }
    const box = { cx: 100, cy: 100, w: 40, h: 40 }
    const mapped = boxToSourcePixels(box, layout)
    expect(mapped.x).toBeCloseTo((100 - 20) / 0.25, 5)
    expect(mapped.y).toBeCloseTo((100 - 20) / 0.25, 5)
    expect(mapped.width).toBeCloseTo(40 / 0.25, 5)
    expect(mapped.height).toBeCloseTo(40 / 0.25, 5)
  })
})
