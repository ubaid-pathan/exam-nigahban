import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { startExam } from '../../api/studentExams'
import { checkApiHealth } from '../../api/system'
import { getErrorMessage } from '../../utils/apiError'
import CameraPreview from '../../components/CameraPreview'

const CHECK_LABELS = {
  browser: 'Browser supports camera access',
  connectivity: 'Connected to Exam Nigahban server',
  camera: 'Camera permission granted',
}

function CheckRow({ label, state }) {
  const icon = state === 'pass' ? '✓' : state === 'fail' ? '✕' : '…'
  const textClass = state === 'pass' ? 'text-success' : state === 'fail' ? 'text-danger' : 'text-muted'
  return (
    <li className={`d-flex align-items-center gap-2 ${textClass}`}>
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </li>
  )
}

export default function ReadinessPage() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [connectivity, setConnectivity] = useState('checking') // checking | pass | fail
  const [cameraStatus, setCameraStatus] = useState('idle')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState('')

  const browserSupportsCamera = Boolean(navigator.mediaDevices?.getUserMedia)

  useEffect(() => {
    let cancelled = false
    checkApiHealth()
      .then(() => {
        if (!cancelled) setConnectivity('pass')
      })
      .catch(() => {
        if (!cancelled) setConnectivity('fail')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const cameraCheckState =
    cameraStatus === 'granted' ? 'pass' : cameraStatus === 'idle' || cameraStatus === 'requesting' ? 'pending' : 'fail'

  const allChecksPassed =
    browserSupportsCamera && connectivity === 'pass' && cameraStatus === 'granted'

  const handleBeginExam = async () => {
    setStartError('')
    setStarting(true)
    try {
      await startExam(examId)
      navigate(`/student/exams/${examId}/take`)
    } catch (err) {
      setStartError(getErrorMessage(err, 'Unable to start the exam. Please try again.'))
      setStarting(false)
    }
  }

  return (
    <div className="mx-auto" style={{ maxWidth: '640px' }}>
      <h1 className="h4 mb-3">Pre-Exam System Check</h1>

      <CameraPreview onStatusChange={setCameraStatus} />

      <div className="card exam-card mt-4">
        <div className="card-body">
          <h2 className="h6">Readiness Checklist</h2>
          <ul className="list-unstyled small mb-3">
            <CheckRow
              label={CHECK_LABELS.browser}
              state={browserSupportsCamera ? 'pass' : 'fail'}
            />
            <CheckRow
              label={CHECK_LABELS.connectivity}
              state={connectivity === 'checking' ? 'pending' : connectivity}
            />
            <CheckRow label={CHECK_LABELS.camera} state={cameraCheckState} />
          </ul>

          {!allChecksPassed && (
            <p className="small text-muted mb-3">
              All checks above must pass before you can begin the exam.
            </p>
          )}

          {startError && (
            <div className="alert alert-danger py-2 small" role="alert">
              {startError}
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            disabled={!allChecksPassed || starting}
            onClick={handleBeginExam}
          >
            {starting ? 'Starting Exam...' : 'Begin Exam'}
          </button>
        </div>
      </div>
    </div>
  )
}
