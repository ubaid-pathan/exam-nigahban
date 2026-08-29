import { useCallback, useEffect, useRef, useState } from 'react'
import CameraPreview from '../components/CameraPreview'
import { detectFrame, getFaceLandmarker } from '../monitoring/faceMonitorService'
import { DETECTION_INTERVAL_MS } from '../monitoring/constants'
import {
  CELL_PHONE_CLASS_ID,
  CELL_PHONE_LABEL,
  DEFAULT_CONFIDENCE_THRESHOLD,
  DEFAULT_IOU_THRESHOLD,
  INPUT_SIZE,
} from './objectDetection/constants'
import { decodeDetections } from './objectDetection/decode'
import { boxToSourcePixels, letterboxImageToTensor } from './objectDetection/preprocess'
import {
  computeDroppedFrames,
  computeEffectiveFps,
  createLatencyTracker,
  summarizeMemory,
} from './objectDetection/performanceStats'
import { describeExecutionProvider, getYoloxSession, runInference } from './objectDetection/yoloxModel'

// Developer-only AI inference spike (Milestone 2) extended with a real-time
// camera performance harness (Milestone 3). NOT linked from any production
// nav, NOT wired into TakeExamPage or the monitoring event pipeline, NOT
// sending anything to the backend. The MediaPipe side reuses
// monitoring/faceMonitorService.js and monitoring/constants.js exactly as
// they already exist in production -- neither file is modified here.

function now() {
  return performance.now()
}

// performance.memory (Chromium-only) exposes usedJSHeapSize/etc. as getters
// on its prototype, not as the object's own enumerable properties -- a
// plain `{ ...performance.memory }` spread silently copies nothing and
// produces NaN downstream. Reading the field explicitly avoids that.
function readMemorySample() {
  const mem = window.performance.memory
  return mem ? { usedJSHeapSize: mem.usedJSHeapSize } : null
}

// Milestone 3 frame-scheduling comparison. "every" intentionally has no
// throttle at all -- it exists only as the worst-case comparison point the
// milestone asked for, not a realistic candidate.
const SCHEDULE_PRESETS = {
  every: { label: 'Every frame (no throttle)', intervalMs: 0 },
  fps5: { label: '~5 FPS', intervalMs: 200 },
  fps8: { label: '~8 FPS', intervalMs: 125 },
  fps10: { label: '~10 FPS', intervalMs: 100 },
}

const PERF_MODES = {
  yolox: 'YOLOX only',
  mediapipe: 'MediaPipe only',
  combined: 'YOLOX + MediaPipe combined',
}

export default function PhoneDetectionSpikePage() {
  const [modelStatus, setModelStatus] = useState('idle') // idle | loading | ready | error
  const [modelError, setModelError] = useState('')
  const [timings, setTimings] = useState({ loadMs: null, firstInferenceMs: null, lastInferenceMs: null })
  const [providerInfo, setProviderInfo] = useState(null)

  const [imageLabel, setImageLabel] = useState('')
  const [hasImage, setHasImage] = useState(false)
  const [detections, setDetections] = useState([])
  const [inferenceRunning, setInferenceRunning] = useState(false)
  const [inferenceError, setInferenceError] = useState('')
  const [confidenceThreshold, setConfidenceThreshold] = useState(DEFAULT_CONFIDENCE_THRESHOLD)

  // --- Milestone 3: real-time camera performance harness state ---
  const [perfMode, setPerfMode] = useState('yolox')
  const [schedulePreset, setSchedulePreset] = useState('fps8')
  const [perfCameraOn, setPerfCameraOn] = useState(false)
  const [perfCameraStatus, setPerfCameraStatus] = useState('idle')
  const [perfRunning, setPerfRunning] = useState(false)
  const [perfError, setPerfError] = useState('')
  const [perfStats, setPerfStats] = useState(null)
  const [perfFaceCount, setPerfFaceCount] = useState(null)
  const [perfDetections, setPerfDetections] = useState([])
  const [uiHeartbeatFps, setUiHeartbeatFps] = useState(null)
  const [cameraSize, setCameraSize] = useState(null)

  const sessionRef = useRef(null)
  const imgElRef = useRef(null)
  const canvasRef = useRef(null)
  const inferenceCountRef = useRef(0)

  // Milestone 3 refs
  const perfVideoRef = useRef(null)
  const perfCanvasRef = useRef(null)
  const landmarkerRef = useRef(null)
  const perfRafRef = useRef(null)
  const perfLoopRef = useRef(null)
  const statsIntervalRef = useRef(null)
  const longTaskObserverRef = useRef(null)
  const yoloxBusyRef = useRef(false)
  const mediapipeBusyRef = useRef(false)
  const lastYoloxRunRef = useRef(0)
  const lastMediapipeRunRef = useRef(0)
  const yoloxTrackerRef = useRef(createLatencyTracker())
  const mediapipeTrackerRef = useRef(createLatencyTracker())
  const scheduledYoloxRef = useRef(0)
  const processedYoloxRef = useRef(0)
  const scheduledMediapipeRef = useRef(0)
  const processedMediapipeRef = useRef(0)
  const heartbeatCountRef = useRef(0)
  const heartbeatWindowStartRef = useRef(0)
  const longTaskCountRef = useRef(0)
  const longTaskTotalMsRef = useRef(0)
  const testStartRef = useRef(0)
  const memoryBeforeRef = useRef(null)
  const perfModeRef = useRef('yolox')
  const yoloxIntervalMsRef = useRef(0)
  const cameraSizeCapturedRef = useRef(false)

  const handleLoadModel = useCallback(async () => {
    setModelStatus('loading')
    setModelError('')
    const start = now()
    try {
      const session = await getYoloxSession()
      sessionRef.current = session
      const loadMs = now() - start
      setTimings((t) => ({ ...t, loadMs }))
      setProviderInfo(describeExecutionProvider())
      setModelStatus('ready')
    } catch (err) {
      setModelStatus('error')
      setModelError(err?.message || 'Failed to load model')
    }
  }, [])

  const drawResultsOnCanvas = useCallback((canvasEl, sourceEl, sourceWidth, sourceHeight, dets, layout) => {
    if (!canvasEl) return
    canvasEl.width = sourceWidth
    canvasEl.height = sourceHeight
    const ctx = canvasEl.getContext('2d')
    ctx.clearRect(0, 0, sourceWidth, sourceHeight)
    ctx.drawImage(sourceEl, 0, 0, sourceWidth, sourceHeight)
    ctx.lineWidth = Math.max(2, sourceWidth / 250)
    ctx.strokeStyle = '#00e676'
    ctx.font = `${Math.max(14, sourceWidth / 40)}px sans-serif`
    ctx.fillStyle = '#00e676'
    for (const det of dets) {
      const box = boxToSourcePixels(det, layout)
      ctx.strokeRect(box.x, box.y, box.width, box.height)
      const label = `${CELL_PHONE_LABEL} ${(det.confidence * 100).toFixed(1)}%`
      const textY = box.y > 20 ? box.y - 6 : box.y + 16
      ctx.fillText(label, box.x, textY)
    }
  }, [])

  const runOneInference = useCallback(
    async (sourceEl, sourceWidth, sourceHeight) => {
      const session = sessionRef.current
      if (!session) throw new Error('Model not loaded yet')

      const { tensorData, layout } = letterboxImageToTensor(sourceEl, sourceWidth, sourceHeight, INPUT_SIZE)

      const start = now()
      const rawOutput = await runInference(session, tensorData)
      const elapsedMs = now() - start

      inferenceCountRef.current += 1
      setTimings((t) => ({
        ...t,
        firstInferenceMs: t.firstInferenceMs ?? elapsedMs,
        lastInferenceMs: elapsedMs,
      }))

      const dets = decodeDetections(rawOutput, {
        classId: CELL_PHONE_CLASS_ID,
        confidenceThreshold,
        iouThreshold: DEFAULT_IOU_THRESHOLD,
      })

      drawResultsOnCanvas(canvasRef.current, sourceEl, sourceWidth, sourceHeight, dets, layout)
      return dets
    },
    [confidenceThreshold, drawResultsOnCanvas],
  )

  const handleImageChange = useCallback((event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setDetections([])
    setInferenceError('')
    setImageLabel(file.name)
    setHasImage(false)
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      imgElRef.current = img
      const canvas = canvasRef.current
      if (canvas) {
        canvas.width = img.naturalWidth
        canvas.height = img.naturalHeight
        canvas.getContext('2d').drawImage(img, 0, 0)
      }
      setHasImage(true)
      URL.revokeObjectURL(url)
    }
    img.src = url
  }, [])

  const handleRunOnImage = useCallback(async () => {
    if (!imgElRef.current) return
    setInferenceRunning(true)
    setInferenceError('')
    try {
      const dets = await runOneInference(imgElRef.current, imgElRef.current.naturalWidth, imgElRef.current.naturalHeight)
      setDetections(dets)
    } catch (err) {
      setInferenceError(err?.message || 'Inference failed')
    } finally {
      setInferenceRunning(false)
    }
  }, [runOneInference])

  // --- Milestone 3: real-time camera performance harness ---

  const runYoloxOnVideo = useCallback(
    async (video) => {
      try {
        const t0 = now()
        const { tensorData, layout } = letterboxImageToTensor(video, video.videoWidth, video.videoHeight, INPUT_SIZE)
        const rawOutput = await runInference(sessionRef.current, tensorData)
        yoloxTrackerRef.current.record(now() - t0)
        processedYoloxRef.current += 1
        const dets = decodeDetections(rawOutput, {
          classId: CELL_PHONE_CLASS_ID,
          confidenceThreshold,
          iouThreshold: DEFAULT_IOU_THRESHOLD,
        })
        setPerfDetections(dets)
        drawResultsOnCanvas(perfCanvasRef.current, video, video.videoWidth, video.videoHeight, dets, layout)
      } catch (err) {
        setPerfError(err?.message || 'YOLOX inference failed during performance test')
      } finally {
        yoloxBusyRef.current = false
      }
    },
    [confidenceThreshold, drawResultsOnCanvas],
  )

  const runMediapipeOnVideo = useCallback((video, timestampMs) => {
    try {
      const t0 = now()
      const { faceCount } = detectFrame(landmarkerRef.current, video, timestampMs)
      mediapipeTrackerRef.current.record(now() - t0)
      processedMediapipeRef.current += 1
      setPerfFaceCount(faceCount)
    } catch (err) {
      setPerfError(err?.message || 'MediaPipe detection failed during performance test')
    } finally {
      mediapipeBusyRef.current = false
    }
  }, [])

  const updateLiveStatsDisplay = useCallback(() => {
    const elapsed = now() - testStartRef.current
    setPerfStats({
      elapsedMs: elapsed,
      yolox: {
        scheduled: scheduledYoloxRef.current,
        processed: processedYoloxRef.current,
        dropped: computeDroppedFrames(scheduledYoloxRef.current, processedYoloxRef.current),
        min: yoloxTrackerRef.current.min(),
        max: yoloxTrackerRef.current.max(),
        avg: yoloxTrackerRef.current.avg(),
        effectiveFps: computeEffectiveFps(processedYoloxRef.current, elapsed),
      },
      mediapipe: {
        scheduled: scheduledMediapipeRef.current,
        processed: processedMediapipeRef.current,
        dropped: computeDroppedFrames(scheduledMediapipeRef.current, processedMediapipeRef.current),
        min: mediapipeTrackerRef.current.min(),
        max: mediapipeTrackerRef.current.max(),
        avg: mediapipeTrackerRef.current.avg(),
        effectiveFps: computeEffectiveFps(processedMediapipeRef.current, elapsed),
      },
      longTask: { count: longTaskCountRef.current, totalMs: longTaskTotalMsRef.current },
      memory: summarizeMemory(memoryBeforeRef.current, readMemorySample()),
    })
  }, [])

  // perfLoopRef.current is reassigned every render (always sees the latest
  // runYoloxOnVideo/runMediapipeOnVideo closures, e.g. for a live threshold
  // change), while the recursive requestAnimationFrame call goes through
  // the ref indirection rather than a captured `const` -- this avoids the
  // classic stale-closure bug where a self-referencing useCallback keeps
  // calling its own first-render version forever. Loop-behavior inputs
  // that must NOT change mid-run (mode, schedule interval) are read from
  // refs set once in startPerfTest, not from reactive state, so this
  // function's own identity never needs to depend on them.
  // Reassigning perfLoopRef.current in an effect (runs after every render,
  // no dependency array) rather than inline in the component body keeps
  // this out of React's render phase, where writing to a ref is
  // discouraged, while still guaranteeing the ref always holds the latest
  // closure.
  useEffect(() => {
    perfLoopRef.current = (nowMs) => {
      heartbeatCountRef.current += 1
      const hbElapsed = nowMs - heartbeatWindowStartRef.current
      if (hbElapsed >= 1000) {
        setUiHeartbeatFps((heartbeatCountRef.current * 1000) / hbElapsed)
        heartbeatCountRef.current = 0
        heartbeatWindowStartRef.current = nowMs
      }

      const video = perfVideoRef.current
      if (video && video.readyState >= 2) {
        if (!cameraSizeCapturedRef.current) {
          cameraSizeCapturedRef.current = true
          setCameraSize({ width: video.videoWidth, height: video.videoHeight })
        }

        const mode = perfModeRef.current
        if ((mode === 'mediapipe' || mode === 'combined') && landmarkerRef.current) {
          if (nowMs - lastMediapipeRunRef.current >= DETECTION_INTERVAL_MS) {
            scheduledMediapipeRef.current += 1
            lastMediapipeRunRef.current = nowMs
            if (!mediapipeBusyRef.current) {
              mediapipeBusyRef.current = true
              runMediapipeOnVideo(video, nowMs)
            }
          }
        }

        if ((mode === 'yolox' || mode === 'combined') && sessionRef.current) {
          if (nowMs - lastYoloxRunRef.current >= yoloxIntervalMsRef.current) {
            scheduledYoloxRef.current += 1
            lastYoloxRunRef.current = nowMs
            if (!yoloxBusyRef.current) {
              yoloxBusyRef.current = true
              runYoloxOnVideo(video)
            }
          }
        }
      }

      perfRafRef.current = requestAnimationFrame((t) => perfLoopRef.current(t))
    }
  })

  const stopPerfTest = useCallback(() => {
    if (perfRafRef.current) {
      cancelAnimationFrame(perfRafRef.current)
      perfRafRef.current = null
    }
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current)
      statsIntervalRef.current = null
    }
    if (longTaskObserverRef.current) {
      longTaskObserverRef.current.disconnect()
      longTaskObserverRef.current = null
    }
    updateLiveStatsDisplay()
    setPerfRunning(false)
  }, [updateLiveStatsDisplay])

  const startPerfTest = useCallback(async () => {
    setPerfError('')
    yoloxTrackerRef.current.reset()
    mediapipeTrackerRef.current.reset()
    scheduledYoloxRef.current = 0
    processedYoloxRef.current = 0
    scheduledMediapipeRef.current = 0
    processedMediapipeRef.current = 0
    longTaskCountRef.current = 0
    longTaskTotalMsRef.current = 0
    lastYoloxRunRef.current = 0
    lastMediapipeRunRef.current = 0
    heartbeatCountRef.current = 0
    heartbeatWindowStartRef.current = now()
    testStartRef.current = now()
    memoryBeforeRef.current = readMemorySample()
    setPerfStats(null)
    setCameraSize(null)
    cameraSizeCapturedRef.current = false
    perfModeRef.current = perfMode
    yoloxIntervalMsRef.current = SCHEDULE_PRESETS[schedulePreset].intervalMs

    try {
      if (perfMode === 'mediapipe' || perfMode === 'combined') {
        landmarkerRef.current = await getFaceLandmarker()
      }
      if (perfMode === 'yolox' || perfMode === 'combined') {
        if (!sessionRef.current) {
          sessionRef.current = await getYoloxSession()
        }
      }
    } catch (err) {
      setPerfError(err?.message || 'Failed to initialize model(s) for performance test')
      return
    }

    if (window.PerformanceObserver) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            longTaskCountRef.current += 1
            longTaskTotalMsRef.current += entry.duration
          }
        })
        observer.observe({ entryTypes: ['longtask'] })
        longTaskObserverRef.current = observer
      } catch {
        // longtask entry type not supported in this browser -- non-fatal,
        // the rest of the measurement still runs.
      }
    }

    setPerfRunning(true)
    perfRafRef.current = requestAnimationFrame((t) => perfLoopRef.current(t))
    statsIntervalRef.current = setInterval(updateLiveStatsDisplay, 500)
  }, [perfMode, schedulePreset, updateLiveStatsDisplay])

  const handleTogglePerfCamera = useCallback(() => {
    setPerfCameraOn((prev) => {
      const next = !prev
      if (!next && perfRunning) stopPerfTest()
      return next
    })
  }, [perfRunning, stopPerfTest])

  // Cleanup on unmount: never leave a rAF loop, interval, or
  // PerformanceObserver running past this dev-only page's lifetime.
  useEffect(() => {
    return () => {
      if (perfRafRef.current) cancelAnimationFrame(perfRafRef.current)
      if (statsIntervalRef.current) clearInterval(statsIntervalRef.current)
      if (longTaskObserverRef.current) longTaskObserverRef.current.disconnect()
    }
  }, [])

  const formatMs = (v) => (v == null ? '—' : `${v.toFixed(1)} ms`)
  const formatFps = (v) => (v == null ? '—' : v.toFixed(2))

  return (
    <div className="container py-4">
      <div className="alert alert-warning">
        <strong>Developer-only AI inference spike (Milestones 2-3).</strong> Not part of the production
        exam or monitoring workflow. Nothing here is sent to the backend.
      </div>

      <h1 className="h4 mb-3">YOLOX-Nano Phone Detection Spike</h1>

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6">1. Model</h2>
          <button type="button" className="btn btn-primary btn-sm" onClick={handleLoadModel} disabled={modelStatus === 'loading'}>
            {modelStatus === 'ready' ? 'Reload Model' : 'Load Model'}
          </button>
          <span className="ms-3">
            Status: <strong>{modelStatus}</strong>
          </span>
          {modelError && <div className="text-danger small mt-2">{modelError}</div>}
          {providerInfo && (
            <pre className="small bg-light p-2 mt-2 mb-0">{JSON.stringify(providerInfo, null, 2)}</pre>
          )}
          {timings.loadMs != null && (
            <p className="small text-muted mb-0 mt-2">Model load time: {timings.loadMs.toFixed(1)} ms</p>
          )}
        </div>
      </div>

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6">2. Confidence Threshold</h2>
          <input
            type="range"
            min="0.05"
            max="0.95"
            step="0.05"
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
          />
          <span className="ms-2">{confidenceThreshold.toFixed(2)}</span>
        </div>
      </div>

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6">3. Static Image Test</h2>
          <input type="file" accept="image/*" onChange={handleImageChange} className="form-control mb-2" style={{ maxWidth: 400 }} />
          {imageLabel && <p className="small text-muted">{imageLabel}</p>}
          <button
            type="button"
            className="btn btn-success btn-sm"
            onClick={handleRunOnImage}
            disabled={!hasImage || modelStatus !== 'ready' || inferenceRunning}
          >
            {inferenceRunning ? 'Running...' : 'Run Inference'}
          </button>
          {inferenceError && <div className="text-danger small mt-2">{inferenceError}</div>}
          <p className="mb-1 mt-2">
            Detections above threshold: <strong>{detections.length}</strong>
          </p>
          {detections.map((det, i) => (
            <div key={i} className="small">
              {CELL_PHONE_LABEL} (class {det.classId}) - confidence {(det.confidence * 100).toFixed(2)}%
            </div>
          ))}
          {timings.lastInferenceMs != null && (
            <p className="small text-muted mb-0 mt-2">Last static-image inference: {timings.lastInferenceMs.toFixed(1)} ms</p>
          )}
          <canvas ref={canvasRef} className="mt-3 border" style={{ maxWidth: '100%' }} />
        </div>
      </div>

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6">4. Real-Time Camera Performance Test (Milestone 3)</h2>
          <p className="small text-muted">
            MediaPipe here calls the exact same <code>faceMonitorService.getFaceLandmarker</code>/
            <code>detectFrame</code> functions the production exam page uses, at the same production
            interval ({DETECTION_INTERVAL_MS} ms) -- unmodified, just reused. YOLOX's interval is the
            variable being compared below.
          </p>

          <div className="row g-3 mb-3">
            <div className="col-auto">
              <label className="form-label small d-block">Mode</label>
              <select className="form-select form-select-sm" value={perfMode} onChange={(e) => setPerfMode(e.target.value)} disabled={perfRunning}>
                {Object.entries(PERF_MODES).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-auto">
              <label className="form-label small d-block">YOLOX schedule</label>
              <select
                className="form-select form-select-sm"
                value={schedulePreset}
                onChange={(e) => setSchedulePreset(e.target.value)}
                disabled={perfRunning}
              >
                {Object.entries(SCHEDULE_PRESETS).map(([key, preset]) => (
                  <option key={key} value={key}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="button" className="btn btn-outline-secondary btn-sm mb-2" onClick={handleTogglePerfCamera}>
            {perfCameraOn ? 'Stop Camera' : 'Start Camera'}
          </button>

          {perfCameraOn && (
            <>
              <CameraPreview ref={perfVideoRef} onStatusChange={setPerfCameraStatus} autoStart />
              <p className="small text-muted mt-2">Camera status: {perfCameraStatus}</p>
            </>
          )}

          <div className="mt-2">
            <button
              type="button"
              className={`btn btn-sm ${perfRunning ? 'btn-danger' : 'btn-primary'}`}
              onClick={perfRunning ? stopPerfTest : startPerfTest}
              disabled={perfCameraStatus !== 'granted' || modelStatus !== 'ready'}
            >
              {perfRunning ? 'Stop Test' : 'Start Test'}
            </button>
            {perfCameraStatus !== 'granted' && <span className="small text-muted ms-2">Camera must be granted first.</span>}
          </div>

          {perfError && <div className="text-danger small mt-2">{perfError}</div>}
        </div>
      </div>

      <div className="card mb-3">
        <div className="card-body">
          <h2 className="h6">5. Performance Test Live Stats</h2>
          {uiHeartbeatFps != null && (
            <p className="small mb-1">
              UI heartbeat (independent of detection loop): <strong>{formatFps(uiHeartbeatFps)}</strong> fps
              <span className="text-muted"> -- a sustained drop from ~60 indicates main-thread blocking</span>
            </p>
          )}
          {cameraSize && (
            <p className="small mb-1">
              Camera resolution: {cameraSize.width}x{cameraSize.height}
            </p>
          )}
          {perfFaceCount != null && (perfMode === 'mediapipe' || perfMode === 'combined') && (
            <p className="small mb-1">MediaPipe face count (latest frame): {perfFaceCount}</p>
          )}
          {perfDetections.length > 0 && (
            <p className="small mb-1">
              YOLOX latest: {CELL_PHONE_LABEL} at {(perfDetections[0].confidence * 100).toFixed(1)}%
            </p>
          )}

          {perfStats && (
            <div className="table-responsive mt-2">
              <table className="table table-sm">
                <thead>
                  <tr>
                    <th>Pipeline</th>
                    <th>Scheduled</th>
                    <th>Processed</th>
                    <th>Dropped</th>
                    <th>Min</th>
                    <th>Avg</th>
                    <th>Max</th>
                    <th>Effective FPS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>YOLOX</td>
                    <td>{perfStats.yolox.scheduled}</td>
                    <td>{perfStats.yolox.processed}</td>
                    <td>{perfStats.yolox.dropped}</td>
                    <td>{formatMs(perfStats.yolox.min)}</td>
                    <td>{formatMs(perfStats.yolox.avg)}</td>
                    <td>{formatMs(perfStats.yolox.max)}</td>
                    <td>{formatFps(perfStats.yolox.effectiveFps)}</td>
                  </tr>
                  <tr>
                    <td>MediaPipe</td>
                    <td>{perfStats.mediapipe.scheduled}</td>
                    <td>{perfStats.mediapipe.processed}</td>
                    <td>{perfStats.mediapipe.dropped}</td>
                    <td>{formatMs(perfStats.mediapipe.min)}</td>
                    <td>{formatMs(perfStats.mediapipe.avg)}</td>
                    <td>{formatMs(perfStats.mediapipe.max)}</td>
                    <td>{formatFps(perfStats.mediapipe.effectiveFps)}</td>
                  </tr>
                </tbody>
              </table>
              <p className="small mb-1">
                Elapsed: {(perfStats.elapsedMs / 1000).toFixed(1)}s | Long tasks (&gt;50ms main-thread
                blocks): {perfStats.longTask.count} totaling {perfStats.longTask.totalMs.toFixed(1)} ms
              </p>
              <p className="small mb-0">
                {perfStats.memory.available
                  ? `Heap: ${perfStats.memory.usedJSHeapSizeBeforeMB.toFixed(1)} MB -> ${perfStats.memory.usedJSHeapSizeAfterMB.toFixed(1)} MB (delta ${perfStats.memory.deltaMB.toFixed(1)} MB)`
                  : 'performance.memory not available in this browser'}
              </p>
            </div>
          )}

          <canvas ref={perfCanvasRef} className="mt-3 border" style={{ maxWidth: '100%' }} />
        </div>
      </div>
    </div>
  )
}
