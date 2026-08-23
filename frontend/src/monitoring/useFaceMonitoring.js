import { useEffect, useRef, useState } from 'react'
import { detectFrame, getFaceLandmarker, resetFaceLandmarker } from './faceMonitorService'
import { classifyHeadPose, extractYawPitchDegFromMatrix } from './headPose'
import { buildActiveConditions } from './observation'
import { createTemporalRuleEngine } from './temporalRuleEngine'
import { DETECTION_INTERVAL_MS } from './constants'

// MediaPipe already gates detections below this threshold internally (see
// faceMonitorService.js); a fixed proxy confidence is used here for the
// same reason documented there — the public FaceLandmarker API does not
// expose a per-frame confidence float outside of blendshapes.
const FRAME_CONFIDENCE = 1.0

/**
 * Runs the browser-side face-monitoring pipeline (MediaPipe detection ->
 * head-pose classification -> temporal rule engine) against a live <video>
 * element while `active` is true, and reports both live status and
 * stabilized monitoring events.
 *
 * UI-facing glue only: no monitoring/business logic lives here beyond
 * wiring the pure engine modules to a requestAnimationFrame loop and a
 * video element.
 *
 * @param {React.RefObject<HTMLVideoElement>} videoRef
 * @param {boolean} active - whether monitoring should be running right now
 * @param {(event: object) => void} onEvent - called with each stabilized
 *   monitoring event emitted by the temporal rule engine
 */
export function useFaceMonitoring(videoRef, active, onEvent) {
  const [status, setStatus] = useState('idle') // idle | loading-model | running | error
  const [observationStatus, setObservationStatus] = useState('no-face') // no-face | single-face | multiple-faces
  const [errorMessage, setErrorMessage] = useState('')

  const engineRef = useRef(null)
  const rafRef = useRef(null)
  const lastRunRef = useRef(0)
  const onEventRef = useRef(onEvent)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    if (!engineRef.current) {
      engineRef.current = createTemporalRuleEngine()
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

    getFaceLandmarker()
      .then((landmarker) => {
        if (cancelled) return
        setStatus('running')

        const loop = (nowMs) => {
          if (cancelled) return
          const video = videoRef.current

          if (
            video &&
            video.readyState >= 2 &&
            nowMs - lastRunRef.current >= DETECTION_INTERVAL_MS
          ) {
            lastRunRef.current = nowMs
            try {
              const { faceCount, matrix } = detectFrame(landmarker, video, nowMs)
              const headPose = matrix
                ? classifyHeadPose(extractYawPitchDegFromMatrix(matrix))
                : null

              setObservationStatus(
                faceCount === 0 ? 'no-face' : faceCount > 1 ? 'multiple-faces' : 'single-face',
              )

              const activeConditions = buildActiveConditions({ faceCount, headPose })
              const events = engineRef.current.observe(
                { activeConditions, confidence: FRAME_CONFIDENCE },
                nowMs,
              )
              events.forEach((event) => onEventRef.current?.(event))
            } catch {
              // A single failed detection frame is not fatal; skip it and
              // let the loop continue on the next frame.
            }
          }

          rafRef.current = requestAnimationFrame(loop)
        }

        rafRef.current = requestAnimationFrame(loop)
      })
      .catch((err) => {
        if (cancelled) return
        setStatus('error')
        setErrorMessage(err?.message || 'Unable to initialize AI monitoring.')
        resetFaceLandmarker()
      })

    return () => {
      cancelled = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      engineRef.current?.reset()
    }
  }, [active, videoRef])

  return { status, observationStatus, errorMessage }
}
