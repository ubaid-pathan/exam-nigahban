import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getAvailableExam } from '../../api/studentExams'
import { getErrorMessage, getStatusCode } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'

export default function InstructionsPage() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const [exam, setExam] = useState(null)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [accepted, setAccepted] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    setNotFound(false)
    try {
      const data = await getAvailableExam(examId)
      setExam(data)

      if (data.session_status === 'in_progress') {
        navigate(`/student/exams/${examId}/take`, { replace: true })
      } else if (
        data.session_status === 'submitted' ||
        data.session_status === 'expired' ||
        data.session_status === 'cancelled'
      ) {
        navigate(`/student/exams/${examId}/result`, { replace: true })
      }
    } catch (err) {
      if (getStatusCode(err) === 404) {
        setNotFound(true)
      } else {
        setError(getErrorMessage(err, 'Unable to load this exam right now.'))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId])

  if (loading) return <LoadingState message="Loading exam instructions..." />
  if (notFound) {
    return (
      <ErrorState
        title="Exam Unavailable"
        message="This exam does not exist or is not currently active."
      />
    )
  }
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!exam) return null

  return (
    <div className="mx-auto" style={{ maxWidth: '640px' }}>
      <div className="card exam-card">
        <div className="card-body">
          <h1 className="h4 mb-1">{exam.title}</h1>
          <p className="text-muted">{exam.description || 'No description provided.'}</p>

          <dl className="row small mb-4">
            <dt className="col-6">Duration</dt>
            <dd className="col-6">{exam.duration_minutes} minutes</dd>
            <dt className="col-6">Number of Questions</dt>
            <dd className="col-6">{exam.question_count}</dd>
          </dl>

          <h2 className="h6">Important Instructions</h2>
          <ul className="small text-muted">
            <li>Camera access is required for the entire duration of the exam.</li>
            <li>The exam timer is set by the server and cannot be paused.</li>
            <li>Once the exam is submitted, answers cannot be changed.</li>
            <li>If your time runs out before submitting, the exam ends automatically.</li>
            <li>Do not close or refresh this window during the exam.</li>
          </ul>

          <h2 className="h6 mt-4">Terms &amp; Conditions</h2>
          <p className="small text-muted">
            By starting this examination, you confirm that you will complete it independently,
            without assistance from other people or unauthorized materials, and that you consent
            to camera-based monitoring for the duration of the exam as described above.
          </p>

          <div className="form-check my-3">
            <input
              className="form-check-input"
              type="checkbox"
              id="acceptTerms"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
            />
            <label className="form-check-label small" htmlFor="acceptTerms">
              I have read and accept the examination terms and conditions.
            </label>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            disabled={!accepted}
            onClick={() => navigate(`/student/exams/${examId}/readiness`)}
          >
            Continue to Camera Check
          </button>
        </div>
      </div>
    </div>
  )
}
