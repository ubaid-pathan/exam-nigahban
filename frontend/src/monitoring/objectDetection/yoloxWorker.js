// Milestone 4: dedicated Web Worker for YOLOX-Nano inference. Runs entirely
// off the main thread -- this module's whole purpose is that YOLOX
// inference never blocks the exam UI/camera/MediaPipe thread.
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/yoloxWorker.js -- no logic change.
//
// Deliberately reuses the exact same, already-verified modules the
// main-thread spike path used, rather than a second implementation:
//   - yoloxModel.js: ONNX Runtime Web session creation + session.run().
//     This file has zero DOM dependency (confirmed by inspection), so it
//     works unmodified in a Worker global scope. The worker gets its own
//     independent module-level session cache -- entirely separate from
//     the main thread's own getYoloxSession() cache in the non-worker
//     spike UI, which is intentional (two isolated execution contexts).
//   - decode.js: pure, already framework/DOM-free, reused unmodified.
//   - preprocess.js: letterboxImageToTensor uses OffscreenCanvas instead of
//     `document`, so it also works unmodified here.
//
// Message protocol (see yoloxWorkerClient.js for the main-thread side):
//   MAIN -> WORKER: LOAD_MODEL | DETECT { requestId, frame, confidenceThreshold?, iouThreshold? } | RESET
//   WORKER -> MAIN: MODEL_READY { loadMs, provider } | DETECTION_RESULT { requestId, detections, inferenceMs, layout } | ERROR { requestId?, message } | DISPOSED

import { getYoloxSession, runInference, describeExecutionProvider, resetYoloxSession } from './yoloxModel'
import { decodeDetections } from './decode'
import { letterboxImageToTensor } from './preprocess'
import { CELL_PHONE_CLASS_ID, DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_IOU_THRESHOLD, INPUT_SIZE } from './constants'

async function handleLoadModel() {
  const start = performance.now()
  await getYoloxSession()
  const loadMs = performance.now() - start
  self.postMessage({ type: 'MODEL_READY', loadMs, provider: describeExecutionProvider() })
}

async function handleDetect(msg) {
  const { requestId, frame, confidenceThreshold, iouThreshold } = msg
  try {
    const session = await getYoloxSession()
    const start = performance.now()
    const { tensorData, layout } = letterboxImageToTensor(frame, frame.width, frame.height, INPUT_SIZE)
    const rawOutput = await runInference(session, tensorData)
    const inferenceMs = performance.now() - start

    const detections = decodeDetections(rawOutput, {
      classId: CELL_PHONE_CLASS_ID,
      confidenceThreshold: confidenceThreshold ?? DEFAULT_CONFIDENCE_THRESHOLD,
      iouThreshold: iouThreshold ?? DEFAULT_IOU_THRESHOLD,
    })

    self.postMessage({ type: 'DETECTION_RESULT', requestId, detections, inferenceMs, layout })
  } finally {
    // Release the transferred bitmap's backing memory promptly rather than
    // waiting for GC -- important under a sustained camera loop.
    frame.close()
  }
}

function handleReset() {
  resetYoloxSession()
  self.postMessage({ type: 'DISPOSED' })
}

self.onmessage = async (event) => {
  const msg = event.data
  try {
    switch (msg.type) {
      case 'LOAD_MODEL':
        await handleLoadModel()
        break
      case 'DETECT':
        await handleDetect(msg)
        break
      case 'RESET':
      case 'DISPOSE':
        handleReset()
        break
      default:
        self.postMessage({ type: 'ERROR', message: `Unknown message type: ${msg.type}` })
    }
  } catch (err) {
    self.postMessage({ type: 'ERROR', requestId: msg?.requestId, message: err?.message || String(err) })
  }
}
