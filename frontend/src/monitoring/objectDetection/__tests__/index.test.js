// Production adapter tests. This module is a thin, zero-new-logic wrapper
// around the relocated yoloxWorkerClient.js factory (see that file's own
// 23-case test suite in this same __tests__ directory for busy-gating,
// stale-requestId handling, monotonic requestIds, etc., which this suite
// deliberately does not re-derive). These tests instead cover:
//   (a) the production API surface (initialize/detect/dispose/onError)
//       correctly maps onto the underlying client's methods, and
//   (b) a full initialize -> detect -> detect -> dispose lifecycle works
//       end-to-end through that production surface, standing in for
//       "integration with the existing production consumer" (Milestone 6
//       Phase 6 item 10) since no such consumer exists yet -- see the
//       Milestone 6 Phase 1 report, which confirms this is a deliberately
//       infrastructure-only milestone.
//
// Same FakeWorker injection pattern as yoloxWorkerClient.test.js and
// frontend/src/api/adminAlertsSocket.js, so this suite never needs a real
// browser Worker or jsdom.

import { describe, expect, it, vi } from 'vitest'
import {
  CELL_PHONE_CLASS_ID,
  CELL_PHONE_LABEL,
  createProductionYoloxWorkerClient,
  DEFAULT_CONFIDENCE_THRESHOLD,
  DEFAULT_IOU_THRESHOLD,
} from '../index'

function createFakeWorkerClass() {
  const instances = []

  class FakeWorker {
    constructor() {
      this.posted = []
      this.terminated = false
      this.onmessage = null
      this.onerror = null
      instances.push(this)
    }

    postMessage(msg) {
      this.posted.push(msg)
    }

    terminate() {
      this.terminated = true
    }

    emit(data) {
      this.onmessage?.({ data })
    }
  }

  return { FakeWorker, instances }
}

function fakeBitmap() {
  return { width: 100, height: 100, close: vi.fn() }
}

describe('createProductionYoloxWorkerClient - public API surface', () => {
  it('exposes exactly initialize/detect/isBusy/dispose/reset/onError', () => {
    const { FakeWorker } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    expect(Object.keys(client).sort()).toEqual(
      ['detect', 'dispose', 'initialize', 'isBusy', 'onError', 'reset'].sort(),
    )
  })

  it('re-exports the same detection constants the Worker protocol uses', () => {
    expect(CELL_PHONE_CLASS_ID).toBe(67)
    expect(CELL_PHONE_LABEL).toBe('Cell Phone')
    expect(DEFAULT_CONFIDENCE_THRESHOLD).toBe(0.8)
    expect(DEFAULT_IOU_THRESHOLD).toBe(0.45)
  })
})

describe('createProductionYoloxWorkerClient - initialize()', () => {
  it('sends LOAD_MODEL once and resolves on MODEL_READY', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    const promise = client.initialize()
    expect(instances[0].posted).toEqual([{ type: 'LOAD_MODEL' }])

    instances[0].emit({ type: 'MODEL_READY', loadMs: 200, provider: { requested: ['wasm'] } })
    await expect(promise).resolves.toEqual({ loadMs: 200, provider: { requested: ['wasm'] } })
  })

  it('does not reload the model on a repeat initialize() call', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    client.initialize()
    client.initialize()
    expect(instances[0].posted).toHaveLength(1)
  })

  it('rejects (never throws synchronously) on a Worker/model load failure', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    const promise = client.initialize()
    instances[0].emit({ type: 'ERROR', message: 'model file not found' })
    await expect(promise).rejects.toThrow('model file not found')
  })
})

describe('createProductionYoloxWorkerClient - full lifecycle (stand-in production consumer)', () => {
  it('runs initialize -> detect -> detect -> dispose through the production API only', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    const onError = vi.fn()
    client.onError(onError)

    await (async () => {
      const initPromise = client.initialize()
      instances[0].emit({ type: 'MODEL_READY', loadMs: 150, provider: {} })
      await initPromise
    })()

    expect(client.isBusy()).toBe(false)

    // First detection: a real phone in frame.
    const firstDetectPromise = client.detect(fakeBitmap(), { confidenceThreshold: 0.8 })
    expect(client.isBusy()).toBe(true)
    const firstRequestId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    const firstDetections = [{ classId: CELL_PHONE_CLASS_ID, confidence: 0.9213, cx: 10, cy: 10, w: 5, h: 5 }]
    instances[0].emit({
      type: 'DETECTION_RESULT',
      requestId: firstRequestId,
      detections: firstDetections,
      inferenceMs: 75.3,
      layout: { ratio: 0.5, dx: 0, dy: 0 },
    })
    await expect(firstDetectPromise).resolves.toEqual({
      type: 'DETECTION_RESULT',
      requestId: firstRequestId,
      detections: firstDetections,
      inferenceMs: 75.3,
      layout: { ratio: 0.5, dx: 0, dy: 0 },
    })
    expect(client.isBusy()).toBe(false)

    // A second frame, later: no phone in frame this time.
    const secondDetectPromise = client.detect(fakeBitmap())
    const secondRequestId = instances[0].posted.filter((m) => m.type === 'DETECT')[1].requestId
    expect(secondRequestId).toBeGreaterThan(firstRequestId)
    instances[0].emit({
      type: 'DETECTION_RESULT',
      requestId: secondRequestId,
      detections: [],
      inferenceMs: 60.1,
      layout: { ratio: 0.5, dx: 0, dy: 0 },
    })
    await expect(secondDetectPromise).resolves.toMatchObject({ detections: [] })

    client.dispose()
    expect(instances[0].terminated).toBe(true)
    expect(onError).not.toHaveBeenCalled()
  })

  it('never queues a second in-flight request; the caller gets null and the bitmap is closed', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.initialize()

    client.detect(fakeBitmap())
    const secondBitmap = fakeBitmap()
    const result = client.detect(secondBitmap)

    expect(result).toBeNull()
    expect(secondBitmap.close).toHaveBeenCalledOnce()
    expect(instances[0].posted.filter((m) => m.type === 'DETECT')).toHaveLength(1)
  })

  it('a stale detection response after reset() does not resolve/reject and leaves isBusy() false', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.initialize()

    client.detect(fakeBitmap())
    const staleId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    client.reset()

    expect(() =>
      instances[0].emit({ type: 'DETECTION_RESULT', requestId: staleId, detections: [], inferenceMs: 1, layout: {} }),
    ).not.toThrow()
    expect(client.isBusy()).toBe(false)
  })

  it('a detection-scoped Worker error rejects only that detect() call and clears isBusy()', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.initialize()

    const promise = client.detect(fakeBitmap())
    const requestId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    instances[0].emit({ type: 'ERROR', requestId, message: 'inference failed' })

    await expect(promise).rejects.toThrow('inference failed')
    expect(client.isBusy()).toBe(false)
  })

  it('an uncaught Worker crash surfaces via onError(), not as a fabricated successful detection', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    const onError = vi.fn()
    client.onError(onError)
    const initPromise = client.initialize().catch(() => {})

    instances[0].onerror({ message: 'worker crashed' })

    expect(onError).toHaveBeenCalledWith('worker crashed')
    await initPromise
  })

  it('dispose() terminates the Worker and is safe to call from an unmount path', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createProductionYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.initialize()

    client.dispose()
    expect(instances[0].terminated).toBe(true)
  })
})
