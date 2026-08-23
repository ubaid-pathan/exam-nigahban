import { describe, expect, it } from 'vitest'
import { createTemporalRuleEngine } from '../temporalRuleEngine'

const TEST_RULES = {
  HEAD_LEFT: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  FACE_ABSENT: { minDurationSec: 5, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
  MULTIPLE_FACES: { minDurationSec: 2, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
}

function frame(activeConditions, confidence = 1.0) {
  return { activeConditions, confidence }
}

describe('temporalRuleEngine', () => {
  it('does not emit an event from a single noisy frame', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const events = engine.observe(frame(['HEAD_LEFT']), 0)
    expect(events).toEqual([])
  })

  it('does not emit while the condition duration is below the threshold', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    let events = []
    events = events.concat(engine.observe(frame(['HEAD_LEFT']), 0))
    events = events.concat(engine.observe(frame(['HEAD_LEFT']), 1000))
    events = events.concat(engine.observe(frame(['HEAD_LEFT']), 2000))
    expect(events).toEqual([])
  })

  it('does not emit a single-occurrence event when required occurrences is 3', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    let events = []
    for (let t = 0; t <= 3500; t += 500) {
      events = events.concat(engine.observe(frame(['HEAD_LEFT']), t))
    }
    // One continuous >3s episode only satisfies 1 of the 3 required occurrences.
    expect(events).toEqual([])
  })

  it('emits HEAD_LEFT only after 3 separate qualifying episodes', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const emitted = []
    let t = 0

    for (let episode = 0; episode < 3; episode += 1) {
      // 3.5s of continuous HEAD_LEFT (satisfies min duration).
      for (let i = 0; i <= 3500; i += 500) {
        emitted.push(...engine.observe(frame(['HEAD_LEFT']), t + i))
      }
      t += 3500
      // Break the condition (head returns to center) before the next episode.
      emitted.push(...engine.observe(frame([]), t))
      t += 1000
    }

    expect(emitted).toHaveLength(1)
    expect(emitted[0]).toMatchObject({ eventType: 'HEAD_LEFT', occurrences: 3, severity: 'medium' })
    expect(emitted[0].durationSeconds).toBeGreaterThanOrEqual(3)
  })

  it('does not emit again while the same episode continues past the threshold', () => {
    const engine = createTemporalRuleEngine({
      HEAD_LEFT: { minDurationSec: 3, requiredOccurrences: 1, confidenceThreshold: 0.75, severity: 'medium' },
    })
    const emitted = []
    for (let t = 0; t <= 6000; t += 500) {
      emitted.push(...engine.observe(frame(['HEAD_LEFT']), t))
    }
    expect(emitted).toHaveLength(1)
  })

  it('does not emit when confidence is below the configured threshold', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const emitted = []
    for (let t = 0; t <= 6000; t += 500) {
      emitted.push(...engine.observe(frame(['FACE_ABSENT'], 0.2), t))
    }
    expect(emitted).toEqual([])
  })

  it('emits FACE_ABSENT after a single 5s+ episode (requiredOccurrences=1)', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const emitted = []
    for (let t = 0; t <= 5200; t += 200) {
      emitted.push(...engine.observe(frame(['FACE_ABSENT']), t))
    }
    expect(emitted).toHaveLength(1)
    expect(emitted[0].eventType).toBe('FACE_ABSENT')
    expect(emitted[0].severity).toBe('high')
  })

  it('emits MULTIPLE_FACES after a 2s+ episode', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const emitted = []
    for (let t = 0; t <= 2200; t += 200) {
      emitted.push(...engine.observe(frame(['MULTIPLE_FACES']), t))
    }
    expect(emitted).toHaveLength(1)
    expect(emitted[0].eventType).toBe('MULTIPLE_FACES')
  })

  it('tracks independent rule types without interference', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    const emitted = []
    for (let t = 0; t <= 5200; t += 200) {
      emitted.push(...engine.observe(frame(['FACE_ABSENT']), t))
    }
    for (let t = 6000; t <= 8200; t += 200) {
      emitted.push(...engine.observe(frame(['MULTIPLE_FACES']), t))
    }
    const types = emitted.map((e) => e.eventType)
    expect(types).toEqual(['FACE_ABSENT', 'MULTIPLE_FACES'])
  })

  it('reset() clears accumulated episode/occurrence state', () => {
    const engine = createTemporalRuleEngine(TEST_RULES)
    for (let t = 0; t <= 5200; t += 200) {
      engine.observe(frame(['FACE_ABSENT']), t)
    }
    engine.reset()
    const events = engine.observe(frame(['FACE_ABSENT']), 100000)
    expect(events).toEqual([])
  })
})
