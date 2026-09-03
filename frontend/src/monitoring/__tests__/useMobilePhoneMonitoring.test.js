// This codebase has no React-hook-rendering test infrastructure (no
// @testing-library/react, no jsdom -- see monitoring/useFaceMonitoring.js,
// which also has no dedicated test file for the same reason). These tests
// instead exercise the hook's exported, DI'd control-flow core
// (shouldRunDetectionTick / runPhoneDetectionTick / startPhoneDetectionLoop)
// directly -- the same logic useMobilePhoneMonitoring() wires to React
// state, with 100% identical behavior, just callable without a live React
// tree. Collaborators are injected the same way
// yoloxWorkerClient.js's createWorker is, rather than via vi.mock.

import { describe, expect, it, vi } from 'vitest'
import {
  runPhoneDetectionTick,
  shouldRunDetectionTick,
  startPhoneDetectionLoop,
} from '../useMobilePhoneMonitoring'

function readyVideo() {
  return { readyState: 2 }
}

describe('shouldRunDetectionTick - duplicate/overlapping detection prevention', () => {
  it('allows a tick when the video is ready, the interval elapsed, and nothing is in flight', () => {
    expect(
      shouldRunDetectionTick({ video: readyVideo(), nowMs: 1000, lastRunMs: 0, busy: false, intervalMs: 200 }),
    ).toBe(true)
  })

  it('refuses a tick while a previous detection is still busy (the overlap guard)', () => {
    expect(
      shouldRunDetectionTick({ video: readyVideo(), nowMs: 1000, lastRunMs: 0, busy: true, intervalMs: 200 }),
    ).toBe(false)
  })

  it('refuses a tick before the scheduling interval has elapsed', () => {
    expect(
      shouldRunDetectionTick({ video: readyVideo(), nowMs: 100, lastRunMs: 0, busy: false, intervalMs: 200 }),
    ).toBe(false)
  })

  it('refuses a tick when there is no video element yet', () => {
    expect(
      shouldRunDetectionTick({ video: null, nowMs: 1000, lastRunMs: 0, busy: false, intervalMs: 200 }),
    ).toBe(false)
  })

  it('refuses a tick when the video is not yet ready (readyState < 2)', () => {
    expect(
      shouldRunDetectionTick({ video: { readyState: 0 }, nowMs: 1000, lastRunMs: 0, busy: false, intervalMs: 200 }),
    ).toBe(false)
  })
})

describe('runPhoneDetectionTick', () => {
  it('observes MOBILE_PHONE with the real YOLOX confidence and emits evidence/source-attached events', async () => {
    const engine = { observe: vi.fn(() => [{ eventType: 'MOBILE_PHONE', severity: 'high' }]) }
    const onEvent = vi.fn()
    const detectFrame = vi.fn(async () => ({ phoneDetected: true, confidence: 0.9213 }))
    const captureEvidence = vi.fn(() => 'base64-evidence')

    const events = await runPhoneDetectionTick({
      video: {},
      nowMs: 5000,
      engine,
      isCancelled: () => false,
      onEvent,
      detectFrame,
      captureEvidence,
    })

    expect(engine.observe).toHaveBeenCalledWith(
      { activeConditions: new Set(['MOBILE_PHONE']), confidence: 0.9213 },
      5000,
    )
    expect(onEvent).toHaveBeenCalledWith({
      eventType: 'MOBILE_PHONE',
      severity: 'high',
      source: 'browser_yolox',
      evidenceImageBase64: 'base64-evidence',
    })
    expect(events).toHaveLength(1)
  })

  it('observes an empty active-condition set and confidence 0 for a no-phone frame', async () => {
    const engine = { observe: vi.fn(() => []) }
    const detectFrame = vi.fn(async () => ({ phoneDetected: false, confidence: null }))

    await runPhoneDetectionTick({ video: {}, nowMs: 1, engine, isCancelled: () => false, detectFrame })

    expect(engine.observe).toHaveBeenCalledWith({ activeConditions: new Set(), confidence: 0 }, 1)
  })

  it('malformed/error result handling: a null detectFrame result (Worker busy) is skipped, engine never touched', async () => {
    const engine = { observe: vi.fn() }
    const detectFrame = vi.fn(async () => null)

    const events = await runPhoneDetectionTick({ video: {}, nowMs: 1, engine, isCancelled: () => false, detectFrame })

    expect(events).toEqual([])
    expect(engine.observe).not.toHaveBeenCalled()
  })

  it('stale async result handling: a result arriving after cancellation is dropped, engine never touched', async () => {
    const engine = { observe: vi.fn(() => [{ eventType: 'MOBILE_PHONE' }]) }
    const onEvent = vi.fn()
    const detectFrame = vi.fn(async () => ({ phoneDetected: true, confidence: 0.95 }))

    const events = await runPhoneDetectionTick({
      video: {},
      nowMs: 1,
      engine,
      isCancelled: () => true, // deactivated while the Worker round trip was in flight
      onEvent,
      detectFrame,
    })

    expect(events).toEqual([])
    expect(engine.observe).not.toHaveBeenCalled()
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('a rejected detectFrame() propagates rather than being converted into a fake result', async () => {
    const engine = { observe: vi.fn() }
    const detectFrame = vi.fn(async () => {
      throw new Error('worker crashed')
    })

    await expect(
      runPhoneDetectionTick({ video: {}, nowMs: 1, engine, isCancelled: () => false, detectFrame }),
    ).rejects.toThrow('worker crashed')
    expect(engine.observe).not.toHaveBeenCalled()
  })
})

describe('startPhoneDetectionLoop - activation/deactivation lifecycle', () => {
  function fakeScheduler() {
    let nextId = 1
    const scheduled = [] // [{ id, cb }]
    return {
      raf: vi.fn((cb) => {
        const id = nextId++
        scheduled.push({ id, cb })
        return id
      }),
      caf: vi.fn((id) => {
        const i = scheduled.findIndex((s) => s.id === id)
        if (i !== -1) scheduled.splice(i, 1)
      }),
      // Simulates the browser firing the most recently scheduled frame.
      fireNextFrame(nowMs) {
        const next = scheduled.shift()
        next?.cb(nowMs)
      },
      pendingCount: () => scheduled.length,
    }
  }

  it('schedules its first frame and calls onRunning as soon as it starts', () => {
    const { raf, caf } = fakeScheduler()
    const onRunning = vi.fn()
    const videoRef = { current: readyVideo() }

    startPhoneDetectionLoop({ videoRef, engine: {}, onEvent: vi.fn(), onRunning, raf, caf })

    expect(onRunning).toHaveBeenCalledOnce()
    expect(raf).toHaveBeenCalledOnce()
  })

  it('runs a detection tick and reschedules itself for the next frame', () => {
    const { raf, caf, fireNextFrame } = fakeScheduler()
    const videoRef = { current: readyVideo() }
    const runTick = vi.fn(() => new Promise(() => {})) // never resolves in this test

    startPhoneDetectionLoop({ videoRef, engine: {}, onEvent: vi.fn(), raf, caf, runTick })
    fireNextFrame(1000)

    expect(runTick).toHaveBeenCalledOnce()
    expect(raf).toHaveBeenCalledTimes(2) // initial schedule + reschedule after this tick
  })

  it('duplicate/overlapping detection prevention: does not start a second tick while one is still in flight', () => {
    const { raf, caf, fireNextFrame } = fakeScheduler()
    const videoRef = { current: readyVideo() }
    const runTick = vi.fn(() => new Promise(() => {})) // stays pending

    startPhoneDetectionLoop({ videoRef, engine: {}, onEvent: vi.fn(), raf, caf, runTick })
    fireNextFrame(1000) // starts the first (never-resolving) tick, busy=true
    fireNextFrame(1200) // interval satisfied, but busy is still true

    expect(runTick).toHaveBeenCalledOnce()
  })

  it('starts a new tick once the previous one settles and the interval has elapsed', async () => {
    const { raf, caf, fireNextFrame } = fakeScheduler()
    const videoRef = { current: readyVideo() }
    let resolveFirst
    const runTick = vi
      .fn()
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockImplementationOnce(() => Promise.resolve([]))

    startPhoneDetectionLoop({ videoRef, engine: {}, onEvent: vi.fn(), raf, caf, runTick })
    fireNextFrame(1000)
    resolveFirst([])
    // Two microtask hops: the settled promise -> .catch()'s pass-through
    // -> .finally()'s handler, which is what actually clears `busy`.
    await Promise.resolve()
    await Promise.resolve()
    fireNextFrame(1400)

    expect(runTick).toHaveBeenCalledTimes(2)
  })

  it('stop() cancels the scheduled frame and prevents any further ticks', () => {
    const { raf, caf, fireNextFrame, pendingCount } = fakeScheduler()
    const videoRef = { current: readyVideo() }
    const runTick = vi.fn(() => Promise.resolve([]))

    const stop = startPhoneDetectionLoop({ videoRef, engine: {}, onEvent: vi.fn(), raf, caf, runTick })
    stop()

    expect(caf).toHaveBeenCalledOnce()
    expect(pendingCount()).toBe(0)

    // Even if a straggling frame still fired (browser edge case), the
    // cancelled flag must stop it from doing any work or rescheduling.
    fireNextFrame(2000)
    expect(runTick).not.toHaveBeenCalled()
  })

  it('stale async result handling: a tick already in flight when stop() is called does not touch the engine', async () => {
    const { raf, caf, fireNextFrame } = fakeScheduler()
    const videoRef = { current: readyVideo() }
    const engine = { observe: vi.fn() }
    let resolveDetect
    const detectFrame = vi.fn(() => new Promise((resolve) => (resolveDetect = resolve)))

    const stop = startPhoneDetectionLoop({
      videoRef,
      engine,
      onEvent: vi.fn(),
      raf,
      caf,
      runTick: (args) => runPhoneDetectionTick({ ...args, detectFrame }),
    })
    fireNextFrame(1000) // kicks off runPhoneDetectionTick -> detectFrame(), still pending

    stop() // deactivate/unmount while the Worker round trip is in flight

    resolveDetect({ phoneDetected: true, confidence: 0.99 }) // the stale result finally arrives
    await Promise.resolve()
    await Promise.resolve()

    expect(engine.observe).not.toHaveBeenCalled()
  })
})
