// Milestone 4: main-thread client for yoloxWorker.js. Owns the busy/
// available gating (never queues more than one in-flight DETECT request)
// and the requestId bookkeeping that lets a stale response be safely
// ignored.
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/yoloxWorkerClient.js -- no logic
// change. See ./index.js for the stable production-facing API
// (initialize/detect/dispose/onError) that wraps this factory.
//
// createWorker is injectable purely so this can be unit tested without a
// real Worker/browser environment -- mirroring the exact pattern already
// used by frontend/src/api/adminAlertsSocket.js (`WebSocketImpl`) for the
// same reason. Production callers never pass it.
//
// The `new Worker(new URL('./yoloxWorker.js', import.meta.url), { type:
// 'module' })` call below must stay written literally, inline, exactly
// like this -- Vite's build-time worker detection statically pattern-matches
// this exact shape to know to emit yoloxWorker.js as its own bundled chunk.
// Splitting the URL construction out into a separate variable (as an
// earlier version of this file did) silently defeats that detection: the
// dev server still works either way, but `vite build` then exits
// successfully while quietly never emitting the worker chunk at all --
// confirmed by inspecting dist/assets/ after a build. Keep this function
// as the one and only place that constructs a real Worker.
function createRealWorker() {
  return new Worker(new URL('./yoloxWorker.js', import.meta.url), { type: 'module' })
}

/**
 * @param {object} [options]
 * @param {() => Worker} [options.createWorker]
 */
export function createYoloxWorkerClient({ createWorker = createRealWorker } = {}) {
  let worker = null
  let nextRequestId = 1
  let busy = false
  let loadPromise = null
  let loadResolvers = null
  const pendingDetections = new Map() // requestId -> { resolve, reject }
  let onError = null

  function ensureWorker() {
    if (!worker) {
      worker = createWorker()
      worker.onmessage = handleMessage
      worker.onerror = (event) => {
        const message = event?.message || 'Worker encountered an uncaught error'
        onError?.(message)
        loadResolvers?.reject(new Error(message))
        loadResolvers = null
      }
    }
    return worker
  }

  function handleMessage(event) {
    const msg = event.data
    switch (msg.type) {
      case 'MODEL_READY':
        loadResolvers?.resolve({ loadMs: msg.loadMs, provider: msg.provider })
        loadResolvers = null
        break

      case 'DETECTION_RESULT': {
        busy = false
        // Map-presence is the staleness guard: cancelPending() (called on
        // reset/dispose) clears every entry, so a response that arrives
        // after that point finds nothing to resolve and is safely dropped.
        const pending = pendingDetections.get(msg.requestId)
        if (pending) {
          pendingDetections.delete(msg.requestId)
          pending.resolve(msg)
        }
        break
      }

      case 'ERROR': {
        if (msg.requestId != null) {
          busy = false
          const pending = pendingDetections.get(msg.requestId)
          if (pending) {
            pendingDetections.delete(msg.requestId)
            pending.reject(new Error(msg.message))
            break
          }
        }
        if (loadResolvers) {
          loadResolvers.reject(new Error(msg.message))
          loadResolvers = null
        }
        onError?.(msg.message)
        break
      }

      case 'DISPOSED':
        break

      default:
        onError?.(`Unknown worker message type: ${msg.type}`)
    }
  }

  function loadModel() {
    ensureWorker()
    if (!loadPromise) {
      loadPromise = new Promise((resolve, reject) => {
        loadResolvers = { resolve, reject }
        worker.postMessage({ type: 'LOAD_MODEL' })
      })
    }
    return loadPromise
  }

  function isBusy() {
    return busy
  }

  /**
   * Sends one frame for detection. Per the Milestone 4 frame-scheduling
   * requirement, callers must check isBusy() themselves before calling --
   * this never queues a second in-flight request; calling it while busy
   * closes the bitmap immediately and returns null rather than piling up
   * work.
   *
   * @param {ImageBitmap} imageBitmap - ownership is transferred to the
   *   worker (zero-copy) and it is always closed by the time this resolves.
   * @param {object} [options]
   * @param {number} [options.confidenceThreshold]
   * @param {number} [options.iouThreshold]
   * @returns {Promise<{requestId:number, detections:object[], inferenceMs:number, layout:object}>|null}
   */
  function detect(imageBitmap, options = {}) {
    if (busy || !worker) {
      imageBitmap.close()
      return null
    }
    const requestId = nextRequestId++
    busy = true
    return new Promise((resolve, reject) => {
      pendingDetections.set(requestId, { resolve, reject })
      worker.postMessage(
        {
          type: 'DETECT',
          requestId,
          frame: imageBitmap,
          confidenceThreshold: options.confidenceThreshold,
          iouThreshold: options.iouThreshold,
        },
        [imageBitmap],
      )
    })
  }

  /** Discards any in-flight request bookkeeping without touching the worker/model. */
  function cancelPending() {
    pendingDetections.clear()
    busy = false
  }

  function reset() {
    cancelPending()
    worker?.postMessage({ type: 'RESET' })
  }

  function dispose() {
    cancelPending()
    worker?.terminate()
    worker = null
    loadPromise = null
  }

  function setOnError(handler) {
    onError = handler
  }

  return { loadModel, detect, isBusy, reset, dispose, setOnError }
}
