// Thin wrapper around onnxruntime-web. Isolates the third-party API surface
// so the rest of this module (and decode.js) never imports ORT types
// directly -- mirrors the isolation pattern already used by
// frontend/src/monitoring/faceMonitorService.js for MediaPipe.
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/yoloxModel.js -- no logic change.
//
// wasm (CPU) execution provider only, per the Phase 10 architecture
// decision: MediaPipe's FaceLandmarker already runs with delegate:'GPU'
// (see faceMonitorService.js), so a GPU-backed EP here risks resource
// contention. Milestone 5.6 validated combined YOLOX + MediaPipe operation
// with this EP choice (see the Milestone 5.6/5.7 reports).

import * as ort from 'onnxruntime-web'
import { INPUT_SIZE, MODEL_INPUT_NAME, MODEL_OUTPUT_NAME, MODEL_URL } from './constants'

ort.env.wasm.numThreads = 1 // conservative default; revisit after perf measurement

let sessionPromise = null

/**
 * Lazily creates (and caches) a single shared InferenceSession, matching
 * the getFaceLandmarker() caching pattern in faceMonitorService.js.
 */
export function getYoloxSession() {
  if (!sessionPromise) {
    sessionPromise = ort.InferenceSession.create(MODEL_URL, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    })
  }
  return sessionPromise
}

export function resetYoloxSession() {
  sessionPromise = null
}

/**
 * Runs one inference pass. tensorData must already be a Float32Array of
 * length 3*INPUT_SIZE*INPUT_SIZE in NCHW/BGR/[0,255] layout (see
 * preprocess.js). Returns the raw, flat Float32Array output exactly as the
 * model produces it -- no decoding here, that is decode.js's job.
 *
 * @param {InstanceType<typeof ort.InferenceSession>} session
 * @param {Float32Array} tensorData
 * @returns {Promise<Float32Array>}
 */
export async function runInference(session, tensorData) {
  const inputTensor = new ort.Tensor('float32', tensorData, [1, 3, INPUT_SIZE, INPUT_SIZE])
  const feeds = { [MODEL_INPUT_NAME]: inputTensor }
  const results = await session.run(feeds)
  const output = results[MODEL_OUTPUT_NAME]
  if (!output) {
    throw new Error(
      `runInference: expected output tensor named "${MODEL_OUTPUT_NAME}", got: ${Object.keys(results).join(', ')}`,
    )
  }
  return output.data
}

/** Reports which execution provider onnxruntime-web actually ended up using, where introspectable. */
export function describeExecutionProvider() {
  return {
    requested: ['wasm'],
    wasmNumThreads: ort.env.wasm.numThreads,
    wasmSimd: ort.env.wasm.simd,
    ortVersion: ort.env.versions?.web ?? 'unknown',
  }
}
