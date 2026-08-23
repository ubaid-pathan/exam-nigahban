import { useEffect, useRef, useState } from 'react'

function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

// The backend is authoritative: `remainingSeconds`/`asOf` are a snapshot from
// the server. This component only ticks a visual countdown between snapshots
// and never itself decides whether the session is still valid.
export default function ExamTimer({ remainingSeconds, asOf, onExpire }) {
  const [now, setNow] = useState(Date.now())
  const hasFiredExpire = useRef(false)

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [])

  const elapsedSinceSnapshot = Math.floor((now - asOf) / 1000)
  const displaySeconds = Math.max(0, remainingSeconds - elapsedSinceSnapshot)

  useEffect(() => {
    if (displaySeconds === 0 && !hasFiredExpire.current) {
      hasFiredExpire.current = true
      onExpire?.()
    }
    if (displaySeconds > 0) {
      hasFiredExpire.current = false
    }
  }, [displaySeconds, onExpire])

  const isWarning = displaySeconds <= 60

  return (
    <div
      className={`exam-timer ${isWarning ? 'exam-timer--warning' : ''}`}
      role="timer"
      aria-live="polite"
      aria-label={`Time remaining: ${formatDuration(displaySeconds)}`}
    >
      {formatDuration(displaySeconds)}
    </div>
  )
}
