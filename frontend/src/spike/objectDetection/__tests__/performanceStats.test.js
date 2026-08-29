import { describe, expect, it } from 'vitest'
import {
  computeDroppedFrames,
  computeEffectiveFps,
  createLatencyTracker,
  summarizeMemory,
} from '../performanceStats'

describe('createLatencyTracker', () => {
  it('reports null min/max/avg with no samples', () => {
    const tracker = createLatencyTracker()
    expect(tracker.count()).toBe(0)
    expect(tracker.min()).toBeNull()
    expect(tracker.max()).toBeNull()
    expect(tracker.avg()).toBeNull()
  })

  it('computes count/min/max/avg correctly', () => {
    const tracker = createLatencyTracker()
    ;[10, 20, 30].forEach((v) => tracker.record(v))
    expect(tracker.count()).toBe(3)
    expect(tracker.min()).toBe(10)
    expect(tracker.max()).toBe(30)
    expect(tracker.avg()).toBeCloseTo(20, 5)
  })

  it('ignores non-finite samples rather than corrupting the stats', () => {
    const tracker = createLatencyTracker()
    tracker.record(10)
    tracker.record(NaN)
    tracker.record(Infinity)
    tracker.record(undefined)
    expect(tracker.count()).toBe(1)
    expect(tracker.avg()).toBe(10)
  })

  it('reset clears all recorded samples', () => {
    const tracker = createLatencyTracker()
    tracker.record(5)
    tracker.reset()
    expect(tracker.count()).toBe(0)
  })
})

describe('computeEffectiveFps', () => {
  it('computes fps from processed frames over elapsed time', () => {
    expect(computeEffectiveFps(10, 1000)).toBeCloseTo(10, 5)
    expect(computeEffectiveFps(5, 1000)).toBeCloseTo(5, 5)
  })

  it('returns 0 for zero elapsed time or zero frames rather than dividing by zero', () => {
    expect(computeEffectiveFps(10, 0)).toBe(0)
    expect(computeEffectiveFps(0, 1000)).toBe(0)
  })
})

describe('computeDroppedFrames', () => {
  it('computes the gap between scheduled and processed frames', () => {
    expect(computeDroppedFrames(100, 80)).toBe(20)
  })

  it('never returns a negative count', () => {
    expect(computeDroppedFrames(50, 80)).toBe(0)
  })
})

describe('summarizeMemory', () => {
  it('reports unavailable when either sample is missing', () => {
    expect(summarizeMemory(null, { usedJSHeapSize: 100 })).toEqual({ available: false })
    expect(summarizeMemory({ usedJSHeapSize: 100 }, null)).toEqual({ available: false })
  })

  it('computes a before/after delta in MB when both samples exist', () => {
    const before = { usedJSHeapSize: 10 * 1024 * 1024 }
    const after = { usedJSHeapSize: 15 * 1024 * 1024 }
    const summary = summarizeMemory(before, after)
    expect(summary.available).toBe(true)
    expect(summary.usedJSHeapSizeBeforeMB).toBeCloseTo(10, 5)
    expect(summary.usedJSHeapSizeAfterMB).toBeCloseTo(15, 5)
    expect(summary.deltaMB).toBeCloseTo(5, 5)
  })
})
