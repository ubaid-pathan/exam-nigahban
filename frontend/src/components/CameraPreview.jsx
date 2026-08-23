import { useEffect, useRef, useState } from 'react'

// Reusable camera-permission + live-preview component.
// A future AI-monitoring milestone can mount this inside the exam-taking
// screen and read frames from `videoRef` without any change to this component.
export default function CameraPreview({ onStatusChange }) {
  const videoRef = useRef(null)
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
      if (videoRef.current) {
        videoRef.current.srcObject = stream
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

  return (
    <div className="camera-preview">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video ref={videoRef} autoPlay playsInline muted className="camera-preview__video" />
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
}
