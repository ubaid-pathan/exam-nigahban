// Thin wrapper around @mediapipe/tasks-vision FaceLandmarker. Isolates the
// third-party API surface so the rest of the monitoring engine (temporal
// rule engine, head-pose math) never imports MediaPipe types directly and
// stays independently testable.
//
// All inference runs locally in the browser via WASM — no video frame or
// image is ever sent to a server for AI processing. The WASM runtime and
// model file are fetched once (from MediaPipe's public, unauthenticated
// CDN/model store) and cached by the browser; this is a static-asset
// download, not a per-frame cloud inference call.

import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'
import { MONITORING_RULES } from './constants'

const WASM_BASE_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm'
const MODEL_ASSET_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'

// MediaPipe applies this confidence gate internally before a face is ever
// returned to us, so we reuse the same MVP threshold configured for the
// face-count-based rules rather than duplicating a second magic number.
const MIN_FACE_DETECTION_CONFIDENCE = MONITORING_RULES.FACE_ABSENT.confidenceThreshold

let landmarkerPromise = null

/**
 * Lazily creates (and caches) a single shared FaceLandmarker instance in
 * VIDEO running mode. Safe to call multiple times — subsequent calls reuse
 * the in-flight/completed initialization.
 */
export function getFaceLandmarker() {
  if (!landmarkerPromise) {
    landmarkerPromise = FilesetResolver.forVisionTasks(WASM_BASE_URL).then((filesetResolver) =>
      FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: {
          modelAssetPath: MODEL_ASSET_URL,
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        numFaces: 3,
        outputFacialTransformationMatrixes: true,
        outputFaceBlendshapes: false,
        minFaceDetectionConfidence: MIN_FACE_DETECTION_CONFIDENCE,
        minFacePresenceConfidence: MIN_FACE_DETECTION_CONFIDENCE,
      }),
    )
  }
  return landmarkerPromise
}

/**
 * Resets the cached instance so a future call to getFaceLandmarker() starts
 * a fresh load (e.g. after a load failure the caller wants to retry).
 */
export function resetFaceLandmarker() {
  landmarkerPromise = null
}

/**
 * Runs detection on a single video frame and reduces the raw MediaPipe
 * result down to the small, plain-object shape the monitoring engine
 * needs: face count and (for a single detected face) its transformation
 * matrix.
 */
export function detectFrame(landmarker, videoElement, timestampMs) {
  const result = landmarker.detectForVideo(videoElement, timestampMs)
  const faceCount = result.faceLandmarks?.length ?? 0
  const matrix =
    faceCount === 1 ? result.facialTransformationMatrixes?.[0]?.data ?? null : null
  return { faceCount, matrix }
}
