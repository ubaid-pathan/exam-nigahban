import { beforeEach, describe, expect, it, vi } from 'vitest'

// mobilePhoneMonitorService.js imports from './objectDetection' -- mocked
// here (relative to this __tests__ file, resolves to the same module) so
// these tests never spin up a real Worker or ONNX Runtime session, mirroring
// how monitoring/objectDetection/__tests__/index.test.js mocks the Worker
// itself rather than the browser APIs around it.
const mockClient = {
  initialize: vi.fn(),
  detect: vi.fn(),
  isBusy: vi.fn(),
  dispose: vi.fn(),
  reset: vi.fn(),
  onError: vi.fn(),
}

vi.mock('../objectDetection', () => ({
  createProductionYoloxWorkerClient: vi.fn(() => mockClient),
  DEFAULT_CONFIDENCE_THRESHOLD: 0.8,
}))

import { createProductionYoloxWorkerClient } from '../objectDetection'
import {
  detectPhoneFrame,
  getYoloxWorkerClient,
  reduceDetections,
  resetYoloxWorkerClient,
} from '../mobilePhoneMonitorService'

function fakeBitmap() {
  return { width: 100, height: 100, close: vi.fn() }
}

beforeEach(() => {
  // Order matters: reset first (which may itself call dispose() on a
  // client left over from the previous test), THEN clear mock call
  // history -- otherwise that reset-triggered dispose() call would count
  // toward this test's own assertions.
  resetYoloxWorkerClient()
  vi.clearAllMocks()
  mockClient.initialize.mockResolvedValue({ loadMs: 100, provider: {} })
  global.createImageBitmap = vi.fn(async () => fakeBitmap())
})

describe('reduceDetections - phone detection reduction', () => {
  it('reports no phone for an empty detections array', () => {
    expect(reduceDetections([])).toEqual({ phoneDetected: false, confidence: null })
  })

  it('reports no phone for null/undefined (malformed/error result handling)', () => {
    expect(reduceDetections(null)).toEqual({ phoneDetected: false, confidence: null })
    expect(reduceDetections(undefined)).toEqual({ phoneDetected: false, confidence: null })
  })

  it('reports a phone detected for a single detection, using its confidence', () => {
    expect(reduceDetections([{ classId: 67, confidence: 0.9213 }])).toEqual({
      phoneDetected: true,
      confidence: 0.9213,
    })
  })

  it('selects the maximum confidence across multiple surviving detections', () => {
    const detections = [
      { classId: 67, confidence: 0.81 },
      { classId: 67, confidence: 0.95 },
      { classId: 67, confidence: 0.88 },
    ]
    expect(reduceDetections(detections)).toEqual({ phoneDetected: true, confidence: 0.95 })
  })

  it('the maximum is order-independent (does not just take the first or last element)', () => {
    const ascending = [{ confidence: 0.81 }, { confidence: 0.99 }]
    const descending = [{ confidence: 0.99 }, { confidence: 0.81 }]
    expect(reduceDetections(ascending).confidence).toBe(0.99)
    expect(reduceDetections(descending).confidence).toBe(0.99)
  })
})

describe('getYoloxWorkerClient - lazy singleton', () => {
  it('creates the client and calls initialize() only once across repeat calls', async () => {
    await getYoloxWorkerClient()
    await getYoloxWorkerClient()
    await getYoloxWorkerClient()

    expect(createProductionYoloxWorkerClient).toHaveBeenCalledTimes(1)
    expect(mockClient.initialize).toHaveBeenCalledTimes(1)
  })

  it('resolves with the client once initialize() completes', async () => {
    const client = await getYoloxWorkerClient()
    expect(client).toBe(mockClient)
  })
})

describe('resetYoloxWorkerClient', () => {
  it('disposes the current client and allows a fresh one to be created next', async () => {
    await getYoloxWorkerClient()
    resetYoloxWorkerClient()

    expect(mockClient.dispose).toHaveBeenCalledOnce()

    await getYoloxWorkerClient()
    expect(createProductionYoloxWorkerClient).toHaveBeenCalledTimes(2)
    expect(mockClient.initialize).toHaveBeenCalledTimes(2)
  })

  it('is safe to call before any client has ever been created', () => {
    expect(() => resetYoloxWorkerClient()).not.toThrow()
  })
})

describe('detectPhoneFrame', () => {
  it('captures a bitmap from the video and detects with the 0.80 confidence threshold', async () => {
    mockClient.detect.mockResolvedValue({ detections: [{ classId: 67, confidence: 0.9 }], inferenceMs: 80, layout: {} })
    const video = {}

    const result = await detectPhoneFrame(video)

    expect(global.createImageBitmap).toHaveBeenCalledWith(video)
    expect(mockClient.detect).toHaveBeenCalledWith(expect.any(Object), { confidenceThreshold: 0.8 })
    expect(result).toEqual({ phoneDetected: true, confidence: 0.9 })
  })

  it('returns { phoneDetected: false, confidence: null } for a no-phone result', async () => {
    mockClient.detect.mockResolvedValue({ detections: [], inferenceMs: 60, layout: {} })
    const result = await detectPhoneFrame({})
    expect(result).toEqual({ phoneDetected: false, confidence: null })
  })

  it('returns null (not an error, not a fabricated no-phone result) when the client is busy', async () => {
    mockClient.detect.mockResolvedValue(null)
    const result = await detectPhoneFrame({})
    expect(result).toBeNull()
  })

  it('propagates a Worker/detection error rather than converting it into a fake result', async () => {
    mockClient.detect.mockRejectedValue(new Error('inference failed'))
    await expect(detectPhoneFrame({})).rejects.toThrow('inference failed')
  })
})
