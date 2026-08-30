// Milestone 6 Phase 2 Step 1: public production entry point for this
// directory. The YOLOX-Nano mobile-phone-detection Worker implementation
// below (yoloxWorker.js, yoloxWorkerClient.js, yoloxModel.js, decode.js,
// preprocess.js, constants.js) was mechanically relocated here, verbatim,
// from frontend/src/spike/objectDetection/ -- no detection logic, model,
// thresholds, or Worker protocol changed. It was validated end-to-end in
// Milestone 5.6 (real visible-browser combined YOLOX + MediaPipe run:
// ~4.63 FPS effective, 75.3ms avg latency, 1/1435 dropped frames, 60.05 FPS
// UI heartbeat) and its accuracy was reconfirmed in Milestone 6 Phase 1
// (class 67, 92.13% confidence on the genuine positive sample; 0
// detections on the negative control).
//
// This file itself contains zero new detection logic. It composes the
// relocated yoloxWorkerClient.js factory (23 passing tests, unchanged)
// behind a stable production-facing API (initialize/detect/dispose/
// onError) so production callers depend on a small, deliberately-named
// surface rather than the underlying factory's own method names.
//
// Worker message protocol (unchanged, see ./yoloxWorker.js):
//   MAIN -> WORKER: LOAD_MODEL | DETECT { requestId, frame, confidenceThreshold?, iouThreshold? } | RESET
//   WORKER -> MAIN: MODEL_READY { loadMs, provider } | DETECTION_RESULT { requestId, detections, inferenceMs, layout } | ERROR { requestId?, message } | DISPOSED

import { createYoloxWorkerClient } from './yoloxWorkerClient'
import {
  CELL_PHONE_CLASS_ID,
  CELL_PHONE_LABEL,
  DEFAULT_CONFIDENCE_THRESHOLD,
  DEFAULT_IOU_THRESHOLD,
} from './constants'

export { CELL_PHONE_CLASS_ID, CELL_PHONE_LABEL, DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_IOU_THRESHOLD }

/**
 * Creates a production YOLOX-Nano phone-detection Worker client. Inference
 * always runs off the main thread in a dedicated Web Worker; the model
 * loads once (lazily, on first `initialize()`/`detect()` call) and is
 * reused for the client's lifetime.
 *
 * Returned client:
 *   initialize()      - loads the ONNX model inside the Worker. Safe to
 *                        call more than once: subsequent calls return the
 *                        same in-flight/completed promise rather than
 *                        reloading. Rejects (never throws synchronously) if
 *                        the Worker fails to start or the model fails to
 *                        load.
 *   detect(bitmap, options?) - sends one already-captured ImageBitmap for
 *                        detection; ownership of the bitmap transfers to
 *                        the Worker (it is always closed by the time this
 *                        settles). Never queues a second in-flight request:
 *                        if a previous detect() has not yet resolved, this
 *                        returns `null` immediately (and still closes the
 *                        given bitmap) rather than piling up stale work --
 *                        callers must check `isBusy()` (or just accept the
 *                        `null`) before calling again, exactly the
 *                        scheduling contract validated by the Milestone
 *                        5.6 combined-mode benchmark. Resolves with
 *                        { requestId, detections, inferenceMs, layout } on
 *                        success; rejects on a detection-scoped Worker
 *                        error. A stale response for a request that was
 *                        cancelled via reset()/dispose() is safely dropped
 *                        and never resolves/rejects a caller's promise.
 *   isBusy()          - true while a detect() call is in flight.
 *   dispose()         - terminates the underlying Worker immediately.
 *                        Idempotent; safe to call from a React effect
 *                        cleanup / component-unmount path.
 *   reset()           - discards in-flight request bookkeeping and asks the
 *                        Worker to drop its cached model session, without
 *                        terminating the Worker itself.
 *   onError(handler)  - registers a handler for uncaught Worker errors
 *                        (e.g. a Worker crash) that are not tied to a
 *                        specific pending detect()/initialize() call. Those
 *                        instead reject that call's own promise directly;
 *                        this handler is for errors with no pending caller
 *                        to reject. Never invoked with a synthetic "success"
 *                        -- a Worker failure always surfaces as either a
 *                        rejected promise or this handler, never as an
 *                        empty detections array standing in for failure.
 *
 * @param {object} [options]
 * @param {() => Worker} [options.createWorker] - test-only injection point
 *   (a real browser Worker is constructed by default).
 */
export function createProductionYoloxWorkerClient(options = {}) {
  const client = createYoloxWorkerClient(options)

  return {
    initialize: client.loadModel,
    detect: client.detect,
    isBusy: client.isBusy,
    dispose: client.dispose,
    reset: client.reset,
    onError: client.setOnError,
  }
}
