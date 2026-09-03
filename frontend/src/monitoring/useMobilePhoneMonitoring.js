import { useEffect, useRef, useState } from 'react'
import {
  detectPhoneFrame as defaultDetectPhoneFrame,
  getYoloxWorkerClient,
  resetYoloxWorkerClient,
} from './mobilePhoneMonitorService'
import { buildPhoneActiveConditions } from './phoneObservation'
import { createTemporalRuleEngine } from './temporalRuleEngine'
import { captureFrameAsJpegBase64 } from './evidenceCapture'
import { MOBILE_PHONE_RULE, YOLOX_DETECTION_INTERVAL_MS } from './constants'

// Scoped to exactly one rule -- see the Milestone 6 Phase 2 Step 2 design:
// this is the entire isolation mechanism between this hook's temporal-rule
// engine instance and useFaceMonitoring's. Module-level so its identity is
// stable; it is a plain object handed to createTemporalRuleEngine() fresh
// each time this hook builds its own engine, never shared or mutated.
const PHONE_RULES = { MOBILE_PHONE: MOBILE_PHONE_RULE }

/**
 * Pure gating check for one rAF tick: is this a valid moment to start a
 * new detectPhoneFrame() call? `busy` is the caller's own record of
 * whether a previous tick's detection is still in flight -- this is what
 * prevents overlapping/duplicate YOLOX requests (see
 * startPhoneDetectionLoop below). Exported for direct unit testing.
 *
 * @param {object} args
 * @param {HTMLVideoElement|null} args.video
 * @param {number} args.nowMs
 * @param {number} args.lastRunMs
 * @param {boolean} args.busy
 * @param {number} args.intervalMs
 */
export function shouldRunDetectionTick({ video, nowMs, lastRunMs, busy, intervalMs }) {
  return Boolean(video && video.readyState >= 2 && !busy && nowMs - lastRunMs >= intervalMs)
}

/**
 * Runs one detection attempt against `video` and, if it produced any
 * stabilized temporal-rule events, reports them via `onEvent`.
 *
 * `isCancelled` is checked AFTER the async detectFrame() call resolves --
 * not before -- so a result that only arrives once the caller has already
 * deactivated/unmounted is dropped rather than observed by the engine or
 * handed to onEvent. This is the stale-async-result guard.
 *
 * Collaborators (detectFrame/buildActiveConditions/captureEvidence) are
 * injectable purely for testing, mirroring the createWorker injection
 * pattern already used by monitoring/objectDetection/yoloxWorkerClient.js
 * -- production callers never override them.
 *
 * @param {object} args
 * @param {HTMLVideoElement} args.video
 * @param {number} args.nowMs
 * @param {ReturnType<typeof createTemporalRuleEngine>} args.engine
 * @param {() => boolean} args.isCancelled
 * @param {(event: object) => void} [args.onEvent]
 * @returns {Promise<object[]>} the events emitted this tick (empty if none,
 *   if the tick was cancelled, or if detectFrame reported nothing new)
 */
export async function runPhoneDetectionTick({
  video,
  nowMs,
  engine,
  isCancelled,
  onEvent,
  detectFrame = defaultDetectPhoneFrame,
  buildActiveConditions = buildPhoneActiveConditions,
  captureEvidence = captureFrameAsJpegBase64,
}) {
  const result = await detectFrame(video)
  // isCancelled(): this run deactivated/unmounted while the Worker round
  // trip was in flight. !result: the shared client was busy (see
  // mobilePhoneMonitorService.js) -- not a new observation, not an error.
  if (isCancelled() || !result) return []

  const { phoneDetected, confidence } = result
  const activeConditions = buildActiveConditions({ phoneDetected })
  const events = engine.observe({ activeConditions, confidence: confidence ?? 0 }, nowMs)
  // Evidence is captured only for a frame that already produced a
  // stabilized event -- never captured on a timer/loop, matching
  // useFaceMonitoring.js. `source: 'browser_yolox'` identifies this as a
  // YOLOX-produced event to the backend (see api/monitoring.js and
  // backend/app/schemas/monitoring.py's MonitoringEventCreate.source,
  // Milestone 6 Phase 2 Step 5) -- useFaceMonitoring.js's MediaPipe events
  // deliberately do NOT set this, so they keep relying on the backend's
  // "browser_mediapipe" default exactly as before Step 5.
  events.forEach((event) => {
    const evidenceImageBase64 = captureEvidence(video)
    onEvent?.({ ...event, source: 'browser_yolox', evidenceImageBase64 })
  })
  return events
}

/**
 * Starts the mobile-phone-detection requestAnimationFrame loop against
 * `videoRef`, driving `engine` and reporting events via `onEvent`. Returns
 * a stop() function that cancels the loop and marks any still-in-flight
 * detection tick as stale (see runPhoneDetectionTick's isCancelled guard).
 *
 * Exported (rather than only existing inline inside the hook below) so its
 * control flow -- scheduling, busy-gating against overlapping requests,
 * and stale-result handling on stop -- can be unit tested by simulating
 * rAF ticks directly, without rendering React (this codebase has no
 * React-hook-rendering test infrastructure; see
 * __tests__/useMobilePhoneMonitoring.test.js).
 *
 * @param {object} deps
 * @param {React.RefObject<HTMLVideoElement>} deps.videoRef
 * @param {ReturnType<typeof createTemporalRuleEngine>} deps.engine
 * @param {(event: object) => void} deps.onEvent
 * @param {() => void} [deps.onRunning] - called once the loop is actually
 *   scheduled (production: flips the hook's status to 'running')
 * @param {typeof requestAnimationFrame} [deps.raf]
 * @param {typeof cancelAnimationFrame} [deps.caf]
 * @param {typeof runPhoneDetectionTick} [deps.runTick]
 * @returns {() => void} stop
 */
export function startPhoneDetectionLoop({
  videoRef,
  engine,
  onEvent,
  onRunning,
  raf = requestAnimationFrame,
  caf = cancelAnimationFrame,
  runTick = runPhoneDetectionTick,
}) {
  let cancelled = false
  let rafId = null
  let lastRunMs = 0
  let busy = false

  const loop = (nowMs) => {
    if (cancelled) return
    const video = videoRef.current

    if (shouldRunDetectionTick({ video, nowMs, lastRunMs, busy, intervalMs: YOLOX_DETECTION_INTERVAL_MS })) {
      lastRunMs = nowMs
      busy = true
      runTick({ video, nowMs, engine, isCancelled: () => cancelled, onEvent })
        .catch(() => {
          // A single failed detection frame (Worker crash, transient
          // inference error) is not fatal; skip it and let the loop
          // continue on the next frame, mirroring useFaceMonitoring.js's
          // identical per-frame catch. The failure was still observable up
          // to this point -- detectPhoneFrame()'s promise rejected rather
          // than being silently converted into a fake empty/no-phone
          // result.
        })
        .finally(() => {
          busy = false
        })
    }

    rafId = raf(loop)
  }

  onRunning?.()
  rafId = raf(loop)

  return function stop() {
    cancelled = true
    if (rafId != null) caf(rafId)
  }
}

/**
 * Runs the browser-side mobile-phone-detection pipeline (YOLOX Worker ->
 * temporal rule engine) against a live <video> element while `active` is
 * true, and reports stabilized monitoring events via `onEvent`.
 *
 * Deliberately structured as a near-mirror of useFaceMonitoring.js (own
 * rAF loop via startPhoneDetectionLoop, own temporal-rule-engine instance,
 * same cancelled-flag/cleanup shape) rather than sharing that hook's loop
 * or engine -- see the Milestone 6 Phase 2 Step 2 design report for why:
 * two independent rAF callbacks per frame is architecturally normal and
 * required no changes to the already-validated useFaceMonitoring.js, and a
 * shared temporal-rule engine instance would mix two orthogonal rule
 * tables into one Map.
 *
 * UI-facing glue only, same as useFaceMonitoring: no monitoring/business
 * logic lives here beyond wiring the pure/DI'd functions above to React
 * state and a video element.
 *
 * @param {React.RefObject<HTMLVideoElement>} videoRef
 * @param {boolean} active - whether monitoring should be running right now
 * @param {(event: object) => void} onEvent - called with each stabilized
 *   monitoring event emitted by this hook's own temporal rule engine
 */
export function useMobilePhoneMonitoring(videoRef, active, onEvent) {
  const [status, setStatus] = useState('idle') // idle | loading-model | running | error
  const [errorMessage, setErrorMessage] = useState('')

  const engineRef = useRef(null)
  const stopRef = useRef(null)
  const onEventRef = useRef(onEvent)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    if (!engineRef.current) {
      engineRef.current = createTemporalRuleEngine(PHONE_RULES)
    }
  }, [])

  useEffect(() => {
    if (!active) {
      setStatus('idle')
      return undefined
    }

    let cancelled = false
    setStatus('loading-model')
    setErrorMessage('')

    getYoloxWorkerClient()
      .then(() => {
        if (cancelled) return
        stopRef.current = startPhoneDetectionLoop({
          videoRef,
          engine: engineRef.current,
          onEvent: (event) => onEventRef.current?.(event),
          onRunning: () => setStatus('running'),
        })
      })
      .catch((err) => {
        if (cancelled) return
        setStatus('error')
        setErrorMessage(err?.message || 'Unable to initialize phone-detection monitoring.')
        // Load failure only -- the shared client may be in a broken state,
        // so discard and terminate it (see resetYoloxWorkerClient's own
        // doc comment) so a future activation retries cleanly. Ordinary
        // deactivation/unmount below does NOT do this.
        resetYoloxWorkerClient()
      })

    return () => {
      cancelled = true
      stopRef.current?.()
      stopRef.current = null
      // Resets only this hook's OWN temporal-rule engine instance -- the
      // module-level Worker singleton is deliberately left running (not
      // disposed) so the next activation (e.g. the student navigates
      // between exam pages) does not pay the ~1s model-load cost again,
      // exactly matching how useFaceMonitoring.js never disposes the
      // cached FaceLandmarker on unmount either.
      engineRef.current?.reset()
    }
  }, [active, videoRef])

  return { status, errorMessage }
}
