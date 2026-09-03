// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/__tests__/yoloxWorkerClient.test.js --
// no test change. See __tests__/index.test.js for the production adapter's
// own (much smaller) test suite.

import { describe, expect, it, vi } from 'vitest'
import { createYoloxWorkerClient } from '../yoloxWorkerClient'

// A minimal fake Worker so this suite never needs a real browser Worker or
// jsdom -- mirrors the WebSocketImpl injectable pattern already used by
// frontend/src/api/adminAlertsSocket.js for the same reason. Captures every
// postMessage call and lets the test manually fire onmessage/onerror to
// simulate the real yoloxWorker.js's responses.
function createFakeWorkerClass() {
  const instances = []

  class FakeWorker {
    constructor(url, options) {
      this.url = url
      this.options = options
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

    // Test helper: simulate a message arriving from the worker thread.
    emit(data) {
      this.onmessage?.({ data })
    }
  }

  return { FakeWorker, instances }
}

function fakeBitmap() {
  return { width: 100, height: 100, close: vi.fn() }
}

describe('createYoloxWorkerClient - model loading', () => {
  it('sends LOAD_MODEL once and resolves loadModel() on MODEL_READY', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    const promise = client.loadModel()
    const worker = instances[0]
    expect(worker.posted).toEqual([{ type: 'LOAD_MODEL' }])

    worker.emit({ type: 'MODEL_READY', loadMs: 123.4, provider: { requested: ['wasm'] } })
    await expect(promise).resolves.toEqual({ loadMs: 123.4, provider: { requested: ['wasm'] } })
  })

  it('does not send a second LOAD_MODEL for a repeat loadModel() call', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    client.loadModel()
    client.loadModel()
    expect(instances[0].posted).toHaveLength(1)
  })

  it('rejects loadModel() on an ERROR message with no requestId', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })

    const promise = client.loadModel()
    instances[0].emit({ type: 'ERROR', message: 'model file not found' })
    await expect(promise).rejects.toThrow('model file not found')
  })
})

describe('createYoloxWorkerClient - busy/available frame scheduling', () => {
  it('is not busy before any detect() call', () => {
    const { FakeWorker } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    expect(client.isBusy()).toBe(false)
  })

  it('becomes busy immediately after detect() is called, and stays busy until a result arrives', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.detect(fakeBitmap())
    expect(client.isBusy()).toBe(true)

    instances[0].emit({ type: 'DETECTION_RESULT', requestId: 1, detections: [], inferenceMs: 50, layout: {} })
    expect(client.isBusy()).toBe(false)
  })

  it('skips (does not queue) a detect() call while busy, closing the bitmap and sending nothing', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.detect(fakeBitmap())
    const postedBeforeSecondCall = instances[0].posted.length

    const secondBitmap = fakeBitmap()
    const result = client.detect(secondBitmap)

    expect(result).toBeNull()
    expect(secondBitmap.close).toHaveBeenCalledOnce()
    expect(instances[0].posted).toHaveLength(postedBeforeSecondCall)
  })

  it('never queues more than one in-flight DETECT message, however many frames are offered', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    for (let i = 0; i < 10; i++) {
      client.detect(fakeBitmap())
    }
    const detectMessages = instances[0].posted.filter((m) => m.type === 'DETECT')
    expect(detectMessages).toHaveLength(1)
  })
})

describe('createYoloxWorkerClient - requestId and stale-response handling', () => {
  it('assigns monotonically increasing requestIds across separate detect() calls', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.detect(fakeBitmap())
    const firstId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    instances[0].emit({ type: 'DETECTION_RESULT', requestId: firstId, detections: [], inferenceMs: 1, layout: {} })

    client.detect(fakeBitmap())
    const secondId = instances[0].posted.filter((m) => m.type === 'DETECT')[1].requestId

    expect(secondId).toBeGreaterThan(firstId)
  })

  it('resolves the correct pending promise by requestId', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    const promise = client.detect(fakeBitmap())
    const requestId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    const detections = [{ classId: 67, confidence: 0.92 }]
    instances[0].emit({ type: 'DETECTION_RESULT', requestId, detections, inferenceMs: 88, layout: { ratio: 0.25 } })

    await expect(promise).resolves.toEqual({
      type: 'DETECTION_RESULT',
      requestId,
      detections,
      inferenceMs: 88,
      layout: { ratio: 0.25 },
    })
  })

  it('safely ignores a DETECTION_RESULT for a requestId that was already cancelled (reset), without throwing', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.detect(fakeBitmap())
    const staleId = instances[0].posted.find((m) => m.type === 'DETECT').requestId

    client.reset() // clears pending bookkeeping (e.g. page navigated away / mode switched)

    expect(() =>
      instances[0].emit({ type: 'DETECTION_RESULT', requestId: staleId, detections: [], inferenceMs: 1, layout: {} }),
    ).not.toThrow()
    // Busy must not get stuck true just because a stale response arrived.
    expect(client.isBusy()).toBe(false)
  })

  it('rejects only the matching pending detect() promise on a DETECT-scoped ERROR, and clears busy', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    const promise = client.detect(fakeBitmap())
    const requestId = instances[0].posted.find((m) => m.type === 'DETECT').requestId
    instances[0].emit({ type: 'ERROR', requestId, message: 'inference failed' })

    await expect(promise).rejects.toThrow('inference failed')
    expect(client.isBusy()).toBe(false)
  })
})

describe('createYoloxWorkerClient - lifecycle', () => {
  it('reset() sends a RESET message to the worker', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.reset()
    expect(instances[0].posted.some((m) => m.type === 'RESET')).toBe(true)
  })

  it('dispose() terminates the worker', () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    client.loadModel()

    client.dispose()
    expect(instances[0].terminated).toBe(true)
  })

  it('an unrecognized/uncaught worker error surfaces via setOnError', async () => {
    const { FakeWorker, instances } = createFakeWorkerClass()
    const client = createYoloxWorkerClient({ createWorker: () => new FakeWorker() })
    const onError = vi.fn()
    client.setOnError(onError)
    // A pending loadModel() also gets rejected by an onerror -- catch it
    // here so the test isn't the thing left with an unhandled rejection.
    const loadPromise = client.loadModel().catch(() => {})

    instances[0].onerror({ message: 'worker crashed' })
    expect(onError).toHaveBeenCalledWith('worker crashed')
    await loadPromise
  })
})
