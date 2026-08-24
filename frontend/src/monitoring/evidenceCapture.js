// Single-frame evidence capture for an already-emitted monitoring event.
// Never called on a timer/loop -- only from the temporal rule engine's
// event callback, so at most one capture happens per stabilized event.
//
// The dimension/base64-extraction math is kept as pure functions so it is
// independently testable without a real <canvas>/<video> element; only
// captureFrameAsJpegBase64 itself touches the DOM.

import { EVIDENCE_CAPTURE_MAX_WIDTH_PX, EVIDENCE_JPEG_QUALITY } from './constants'

/**
 * Scales videoWidth/videoHeight down to at most maxWidth, preserving
 * aspect ratio. Never scales up. Pure function.
 */
export function computeCaptureDimensions(videoWidth, videoHeight, maxWidth = EVIDENCE_CAPTURE_MAX_WIDTH_PX) {
  if (!videoWidth || !videoHeight || videoWidth <= 0 || videoHeight <= 0) {
    return null
  }
  const scale = Math.min(1, maxWidth / videoWidth)
  return {
    width: Math.max(1, Math.round(videoWidth * scale)),
    height: Math.max(1, Math.round(videoHeight * scale)),
  }
}

/**
 * Extracts the base64 payload from a `data:image/jpeg;base64,...` URL.
 * Returns null if the input isn't a base64 data URL. Pure function.
 */
export function extractBase64FromDataUrl(dataUrl) {
  const marker = ";base64,"
  const markerIndex = typeof dataUrl === "string" ? dataUrl.indexOf(marker) : -1
  if (markerIndex === -1) return null
  const base64 = dataUrl.slice(markerIndex + marker.length)
  return base64.length > 0 ? base64 : null
}

/**
 * Captures the current frame of a live <video> element as a downsized
 * JPEG, base64-encoded. Returns null (never throws) if the video isn't
 * ready or the browser can't produce a 2D canvas context -- evidence
 * capture must always be safe to call speculatively.
 */
export function captureFrameAsJpegBase64(videoElement) {
  try {
    const dimensions = computeCaptureDimensions(videoElement?.videoWidth, videoElement?.videoHeight)
    if (!dimensions) return null

    const canvas = document.createElement('canvas')
    canvas.width = dimensions.width
    canvas.height = dimensions.height

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.drawImage(videoElement, 0, 0, dimensions.width, dimensions.height)
    return extractBase64FromDataUrl(canvas.toDataURL('image/jpeg', EVIDENCE_JPEG_QUALITY))
  } catch {
    return null
  }
}
