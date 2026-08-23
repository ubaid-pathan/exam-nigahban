import { forwardRef, useEffect, useRef, useState } from 'react'

// Reusable camera-permission + live-preview component.
// `ref` (optional) is forwarded directly to the underlying <video> element
// so the AI-monitoring engine can read live frames from it without this
// component needing to know anything about monitoring.
const CameraPreview = forwardRef(function CameraPreview(
  { onStatusChange, autoStart = false },
  forwardedVideoRef,
) {
  const internalVideoRef = useRef(null)
  const streamRef = useRef(null)
  const [status, setStatus] = useState('idle') // idle | requesting | granted | denied | unavailable | error

  const updateStatus = (next) => {
    setStatus(next)
    onStatusChange?.(next)
  }

  const requestCamera = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      updateStatus('unavailable')
      return
    }
    updateStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      if (internalVideoRef.current) {
        internalVideoRef.current.srcObject = stream
      }
      updateStatus('granted')
    } catch (err) {
      if (err?.name === 'NotFoundError' || err?.name === 'OverconstrainedError') {
        updateStatus('unavailable')
      } else if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
        updateStatus('denied')
      } else {
        updateStatus('error')
      }
    }
  }

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  useEffect(() => {
    if (autoStart) {
      requestCamera()
    }
    // Intentionally mount-only: re-requesting on every re-render would
    // repeatedly prompt/reset the stream.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setVideoRef = (node) => {
    internalVideoRef.current = node
    if (typeof forwardedVideoRef === 'function') {
      forwardedVideoRef(node)
    } else if (forwardedVideoRef) {
      forwardedVideoRef.current = node
    }
  }

  return (
    <div className="camera-preview">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video ref={setVideoRef} autoPlay playsInline muted className="camera-preview__video" />
      {status !== 'granted' && (
        <div className="camera-preview__overlay">
          {status === 'idle' && (
            <button type="button" className="btn btn-primary" onClick={requestCamera}>
              Enable Camera
            </button>
          )}
          {status === 'requesting' && <span>Requesting camera access…</span>}
          {status === 'denied' && (
            <div>
              <p className="text-danger mb-2">
                Camera access was denied. Please allow camera access in your browser settings.
              </p>
              <button type="button" className="btn btn-outline-light btn-sm" onClick={requestCamera}>
                Try Again
              </button>
            </div>
          )}
          {status === 'unavailable' && (
            <p className="text-danger mb-0">No camera was found on this device.</p>
          )}
          {status === 'error' && (
            <div>
              <p className="text-danger mb-2">Unable to access the camera.</p>
              <button type="button" className="btn btn-outline-light btn-sm" onClick={requestCamera}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
})

export default CameraPreview
