import { describe, expect, it } from 'vitest'
import { classifyHeadPose, extractYawPitchDegFromMatrix } from '../headPose'

const THRESHOLDS = { yawLeft: -15, yawRight: 15, pitchUp: 12, pitchDown: -12 }
const LOOKING_AWAY_THRESHOLDS = { yaw: 30, pitch: 22 }

function identityMatrix() {
  // Row-major 4x4 identity: no rotation.
  // prettier-ignore
  return [
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ]
}

describe('classifyHeadPose', () => {
  it('classifies a centered face as CENTER', () => {
    expect(classifyHeadPose({ yawDeg: 0, pitchDeg: 0 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe('CENTER')
  })

  it('classifies a small turn within tolerance as CENTER', () => {
    expect(classifyHeadPose({ yawDeg: 5, pitchDeg: -3 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe('CENTER')
  })

  it('classifies a moderate left turn as HEAD_LEFT', () => {
    expect(classifyHeadPose({ yawDeg: -20, pitchDeg: 0 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'HEAD_LEFT',
    )
  })

  it('classifies a moderate right turn as HEAD_RIGHT', () => {
    expect(classifyHeadPose({ yawDeg: 20, pitchDeg: 0 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'HEAD_RIGHT',
    )
  })

  it('classifies an upward tilt as HEAD_UP', () => {
    expect(classifyHeadPose({ yawDeg: 0, pitchDeg: 15 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'HEAD_UP',
    )
  })

  it('classifies a downward tilt as HEAD_DOWN', () => {
    expect(classifyHeadPose({ yawDeg: 0, pitchDeg: -15 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'HEAD_DOWN',
    )
  })

  it('classifies an extreme yaw as LOOKING_AWAY rather than HEAD_LEFT/RIGHT', () => {
    expect(classifyHeadPose({ yawDeg: -45, pitchDeg: 0 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'LOOKING_AWAY',
    )
    expect(classifyHeadPose({ yawDeg: 45, pitchDeg: 0 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'LOOKING_AWAY',
    )
  })

  it('classifies an extreme pitch as LOOKING_AWAY', () => {
    expect(classifyHeadPose({ yawDeg: 0, pitchDeg: 30 }, THRESHOLDS, LOOKING_AWAY_THRESHOLDS)).toBe(
      'LOOKING_AWAY',
    )
  })
})

describe('extractYawPitchDegFromMatrix', () => {
  it('returns zero yaw/pitch for an identity (no rotation) matrix', () => {
    const { yawDeg, pitchDeg } = extractYawPitchDegFromMatrix(identityMatrix())
    expect(yawDeg).toBeCloseTo(0, 5)
    expect(pitchDeg).toBeCloseTo(0, 5)
  })

  it('returns a safe default for malformed input', () => {
    expect(extractYawPitchDegFromMatrix(null)).toEqual({ yawDeg: 0, pitchDeg: 0 })
    expect(extractYawPitchDegFromMatrix([1, 2, 3])).toEqual({ yawDeg: 0, pitchDeg: 0 })
  })
})
