// Thin production glue for mobile-phone (YOLOX) detection, mirroring the
// role faceMonitorService.js plays for MediaPipe: isolates the detector's
// own API surface and reduces its raw output to the small, plain shape the
// monitoring engine needs.
//
// Milestone 6 Phase 2 Step 3: uses the relocated, production-located
// monitoring/objectDetection/ Worker client (validated end-to-end in
// Milestone 5.6's real combined-mode browser benchmark and Milestone 6
// Phase 1's accuracy regression: class 67, 92.13% confidence on the
// genuine positive sample; 0 detections on the negative control). No
// detection logic lives in this file -- only lazy singleton lifecycle and
// a pure reduction of the Worker's response.

import { createProductionYoloxWorkerClient, DEFAULT_CONFIDENCE_THRESHOLD } from './objectDetection'

let clientInstance = null
let initPromise = null

/**
 * Lazily creates (on first call) and initializes a single shared
 * production YOLOX Worker client, matching the getFaceLandmarker() caching
 * pattern in faceMonitorService.js: subsequent calls -- including from a
 * later activation of useMobilePhoneMonitoring after the student
 * deactivates and reactivates monitoring -- reuse the same
 * in-flight/completed initialize() promise rather than reloading the
 * model or spawning a second Worker.
 *
 * @returns {Promise<ReturnType<typeof createProductionYoloxWorkerClient>>}
 */
export function getYoloxWorkerClient() {
  if (!clientInstance) {
    clientInstance = createProductionYoloxWorkerClient()
  }
  if (!initPromise) {
    initPromise = clientInstance.initialize().then(() => clientInstance)
  }
  return initPromise
}

/**
 * Discards the cached client/init-promise so a future getYoloxWorkerClient()
 * call starts fresh with a brand new Worker. Unlike resetFaceLandmarker()
 * (which only forgets a promise reference -- FaceLandmarker exposes no
 * dispose call), this also terminates the underlying Worker: a Worker is a
 * real OS-level resource, and a client whose initialize() just failed may
 * be in a broken state, so leaving it running unreferenced would leak it.
 * Intended only for the load-failure retry path -- never called on
 * ordinary hook deactivation/unmount (see useMobilePhoneMonitoring.js).
 */
export function resetYoloxWorkerClient() {
  clientInstance?.dispose()
  clientInstance = null
  initPromise = null
}

/**
 * Reduces a raw YOLOX detections array (already confidence-thresholded and
 * NMS-suppressed by decode.js -- see monitoring/objectDetection/decode.js)
 * to the small shape the temporal rule engine needs. Pure function,
 * independently testable without a Worker or DOM.
 *
 * @param {{confidence:number}[]|null|undefined} detections
 * @returns {{phoneDetected: boolean, confidence: number|null}}
 */
export function reduceDetections(detections) {
  if (!detections || detections.length === 0) {
    return { phoneDetected: false, confidence: null }
  }
  const confidence = detections.reduce((max, d) => Math.max(max, d.confidence), 0)
  return { phoneDetected: true, confidence }
}

/**
 * Captures the current video frame and runs it through the shared YOLOX
 * Worker client, using the same confidence threshold already
 * validated for this model (DEFAULT_CONFIDENCE_THRESHOLD).
 *
 * ImageBitmap cleanup is deliberately NOT done here: ownership of the
 * bitmap transfers to client.detect() (which either closes it immediately
 * if the client is busy, or hands it to the Worker via a structured-clone
 * transfer list, where yoloxWorker.js's handleDetect() always closes it in
 * a finally block once inference completes) -- both paths are already
 * covered by the existing, unmodified, validated client/Worker protocol.
 * Touching the bitmap again here would be redundant at best and a
 * double-close error at worst.
 *
 * @param {HTMLVideoElement} video
 * @returns {Promise<{phoneDetected: boolean, confidence: number|null}|null>}
 *   null means the shared client was still busy with a previous request --
 *   the caller should treat this tick as skipped, not as an error or a
 *   "no phone" observation.
 */
export async function detectPhoneFrame(video) {
  const client = await getYoloxWorkerClient()
  const bitmap = await createImageBitmap(video)
  const result = await client.detect(bitmap, { confidenceThreshold: DEFAULT_CONFIDENCE_THRESHOLD })
  if (!result) {
    return null
  }
  return reduceDetections(result.detections)
}
