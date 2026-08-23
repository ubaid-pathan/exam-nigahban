import { describe, expect, it } from 'vitest'
import { buildActiveConditions } from '../observation'

describe('buildActiveConditions', () => {
  it('reports FACE_ABSENT when no face is detected', () => {
    const conditions = buildActiveConditions({ faceCount: 0, headPose: null })
    expect(conditions.has('FACE_ABSENT')).toBe(true)
    expect(conditions.size).toBe(1)
  })

  it('reports MULTIPLE_FACES when more than one face is detected, ignoring pose', () => {
    const conditions = buildActiveConditions({ faceCount: 2, headPose: 'HEAD_LEFT' })
    expect(conditions.has('MULTIPLE_FACES')).toBe(true)
    expect(conditions.has('HEAD_LEFT')).toBe(false)
    expect(conditions.size).toBe(1)
  })

  it('reports the pose label when exactly one face is detected', () => {
    const conditions = buildActiveConditions({ faceCount: 1, headPose: 'LOOKING_AWAY' })
    expect(conditions.has('LOOKING_AWAY')).toBe(true)
    expect(conditions.size).toBe(1)
  })

  it('reports no active conditions for a single centered face', () => {
    const conditions = buildActiveConditions({ faceCount: 1, headPose: 'CENTER' })
    expect(conditions.size).toBe(0)
  })
})
