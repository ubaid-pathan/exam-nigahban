import { describe, expect, it } from 'vitest'
import {
  buildGrids,
  decodeDetections,
  nonMaxSuppression,
  validateRawOutput,
} from '../decode'
import { BOX_ATTRS, INPUT_SIZE, STRIDES, TOTAL_ANCHORS } from '../constants'

// Builds a flat [totalAnchors * BOX_ATTRS] Float32Array of all-zero rows,
// then lets the caller poke specific anchor rows -- keeps each test's
// "one row I care about" explicit while the rest of the tensor is inert.
function blankOutput() {
  return new Float32Array(TOTAL_ANCHORS * BOX_ATTRS)
}

function setAnchorRow(output, anchorIndex, { cx = 0, cy = 0, w = 0, h = 0, objectness = 0, classScores = {} } = {}) {
  const base = anchorIndex * BOX_ATTRS
  output[base + 0] = cx
  output[base + 1] = cy
  output[base + 2] = w
  output[base + 3] = h
  output[base + 4] = objectness
  for (const [classId, score] of Object.entries(classScores)) {
    output[base + 5 + Number(classId)] = score
  }
}

describe('buildGrids', () => {
  it('produces exactly TOTAL_ANCHORS entries', () => {
    expect(buildGrids().length).toBe(TOTAL_ANCHORS)
  })

  it('orders anchors stride-8 first, then stride-16, then stride-32', () => {
    const grids = buildGrids()
    const size8 = (INPUT_SIZE / STRIDES[0]) ** 2
    const size16 = (INPUT_SIZE / STRIDES[1]) ** 2
    expect(grids[0].stride).toBe(8)
    expect(grids[size8 - 1].stride).toBe(8)
    expect(grids[size8].stride).toBe(16)
    expect(grids[size8 + size16 - 1].stride).toBe(16)
    expect(grids[size8 + size16].stride).toBe(32)
    expect(grids[grids.length - 1].stride).toBe(32)
  })

  it('orders each stride level row-major (y outer, x inner), matching the verified Python decode', () => {
    const grids = buildGrids(320, [32]) // 10x10 grid, easiest to check by hand
    expect(grids[0]).toEqual({ gx: 0, gy: 0, stride: 32 })
    expect(grids[1]).toEqual({ gx: 1, gy: 0, stride: 32 })
    expect(grids[10]).toEqual({ gx: 0, gy: 1, stride: 32 })
  })
})

describe('validateRawOutput', () => {
  it('accepts a correctly-shaped output', () => {
    expect(validateRawOutput(blankOutput())).toBeNull()
  })

  it('rejects null/undefined', () => {
    expect(validateRawOutput(null)).toMatch(/missing/)
    expect(validateRawOutput(undefined)).toMatch(/missing/)
  })

  it('rejects a wrong-length array (malformed output)', () => {
    expect(validateRawOutput(new Float32Array(10))).toMatch(/does not match expected/)
  })
})

describe('decodeDetections - malformed output handling', () => {
  it('throws a descriptive error for a wrong-shaped output rather than silently misreading it', () => {
    expect(() => decodeDetections(new Float32Array(10))).toThrow(/does not match expected/)
  })

  it('silently excludes NaN-filled anchor rows rather than crashing or misfiring', () => {
    const output = blankOutput()
    setAnchorRow(output, 0, {
      cx: NaN,
      cy: NaN,
      w: NaN,
      h: NaN,
      objectness: NaN,
      classScores: { 67: NaN },
    })
    expect(() => decodeDetections(output, { confidenceThreshold: 0 })).not.toThrow()
    const detections = decodeDetections(output, { confidenceThreshold: 0 })
    expect(detections.find((d) => d.confidence !== d.confidence /* NaN check */)).toBeUndefined()
  })
})

describe('decodeDetections - box decoding', () => {
  it('decodes grid-relative box offsets into absolute letterboxed-space coordinates using (raw+grid)*stride and exp(raw)*stride', () => {
    const output = blankOutput()
    // Anchor 0 is stride-8, grid (0,0) per buildGrids' verified ordering.
    setAnchorRow(output, 0, {
      cx: 0.5,
      cy: 0.25,
      w: 0, // exp(0) = 1
      h: Math.log(2), // exp(ln 2) = 2
      objectness: 1,
      classScores: { 67: 1 },
    })
    const [detection] = decodeDetections(output, { confidenceThreshold: 0.5 })
    expect(detection.cx).toBeCloseTo((0.5 + 0) * 8, 5)
    expect(detection.cy).toBeCloseTo((0.25 + 0) * 8, 5)
    expect(detection.w).toBeCloseTo(1 * 8, 5)
    expect(detection.h).toBeCloseTo(2 * 8, 5)
  })
})

describe('decodeDetections - objectness x class score confidence', () => {
  it('multiplies objectness by the class-67 score, not either value alone', () => {
    const output = blankOutput()
    setAnchorRow(output, 5, { objectness: 0.9, classScores: { 67: 0.8 } })
    const [detection] = decodeDetections(output, { confidenceThreshold: 0.1 })
    expect(detection.confidence).toBeCloseTo(0.9 * 0.8, 6)
  })

  it('does not apply a second sigmoid: a raw value already in [0,1] is used as-is', () => {
    const output = blankOutput()
    setAnchorRow(output, 5, { objectness: 0.5, classScores: { 67: 0.5 } })
    const [detection] = decodeDetections(output, { confidenceThreshold: 0.2 })
    // If a second sigmoid were wrongly applied, 0.5 would become ~0.6225,
    // giving confidence ~0.3874 instead of the correct 0.25.
    expect(detection.confidence).toBeCloseTo(0.25, 6)
  })
})

describe('decodeDetections - class-67 filtering', () => {
  it('ignores a high score on a different class and only reads the requested classId column', () => {
    const output = blankOutput()
    // Strong "person" (class 0) score, weak class-67 score.
    setAnchorRow(output, 0, { objectness: 0.99, classScores: { 0: 0.99, 67: 0.01 } })
    const detections = decodeDetections(output, { classId: 67, confidenceThreshold: 0.5 })
    expect(detections).toHaveLength(0)
  })

  it('respects a different requested classId', () => {
    const output = blankOutput()
    setAnchorRow(output, 0, { objectness: 0.99, classScores: { 0: 0.99, 67: 0.01 } })
    const detections = decodeDetections(output, { classId: 0, confidenceThreshold: 0.5 })
    expect(detections).toHaveLength(1)
  })
})

describe('decodeDetections - confidence threshold', () => {
  it('excludes detections below the threshold', () => {
    const output = blankOutput()
    setAnchorRow(output, 0, { objectness: 0.5, classScores: { 67: 0.5 } }) // confidence 0.25
    expect(decodeDetections(output, { confidenceThreshold: 0.8 })).toHaveLength(0)
  })

  it('includes detections at or above the threshold', () => {
    const output = blankOutput()
    setAnchorRow(output, 0, { objectness: 0.9, classScores: { 67: 0.9 } }) // confidence 0.81
    expect(decodeDetections(output, { confidenceThreshold: 0.8 })).toHaveLength(1)
  })
})

describe('nonMaxSuppression', () => {
  it('keeps only the highest-confidence box among heavily overlapping candidates', () => {
    const boxes = [
      { cx: 100, cy: 100, w: 50, h: 50, confidence: 0.9 },
      { cx: 102, cy: 101, w: 50, h: 50, confidence: 0.6 }, // near-identical box, lower confidence
    ]
    const kept = nonMaxSuppression(boxes, 0.45)
    expect(kept).toHaveLength(1)
    expect(kept[0].confidence).toBe(0.9)
  })

  it('keeps both boxes when they do not meaningfully overlap', () => {
    const boxes = [
      { cx: 10, cy: 10, w: 10, h: 10, confidence: 0.9 },
      { cx: 200, cy: 200, w: 10, h: 10, confidence: 0.6 },
    ]
    expect(nonMaxSuppression(boxes, 0.45)).toHaveLength(2)
  })

  it('returns an empty array for an empty input without throwing', () => {
    expect(nonMaxSuppression([], 0.45)).toEqual([])
  })
})

describe('decodeDetections - integration: full pipeline on a realistic single strong anchor', () => {
  it('produces exactly one detection end-to-end for one clearly-above-threshold anchor', () => {
    const output = blankOutput()
    setAnchorRow(output, 1750, {
      cx: 0.5,
      cy: 0.5,
      w: 1,
      h: 1,
      objectness: 0.95,
      classScores: { 67: 0.97 },
    })
    const detections = decodeDetections(output, { confidenceThreshold: 0.8 })
    expect(detections).toHaveLength(1)
    expect(detections[0].classId).toBe(67)
    expect(detections[0].confidence).toBeCloseTo(0.95 * 0.97, 6)
  })
})
