import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getAvailableExam, getSession } from '../../api/studentExams'
import { getErrorMessage, getStatusCode } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'

export default function ResultPage() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [examTitle, setExamTitle] = useState('')
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    setNotFound(false)
    try {
      const exam = await getAvailableExam(examId)
      setExamTitle(exam.title)

      if (exam.session_status === 'in_progress') {
        navigate(`/student/exams/${examId}/take`, { replace: true })
        return
      }
      if (!exam.session_id) {
        navigate(`/student/exams/${examId}/instructions`, { replace: true })
        return
      }

      const sessionData = await getSession(exam.session_id)
      setSession(sessionData)
    } catch (err) {
      if (getStatusCode(err) === 404) {
        setNotFound(true)
      } else {
        setError(getErrorMessage(err, 'Unable to load your result right now.'))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId])

  if (loading) return <LoadingState message="Loading your result..." />
  if (notFound) {
    return (
      <ErrorState
        title="Exam Unavailable"
        message="This exam does not exist or is not currently active."
      />
    )
  }
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!session) return null

  const isSubmitted = session.status === 'submitted'

  return (
    <div className="mx-auto" style={{ maxWidth: '520px' }}>
      <div className="card exam-card">
        <div className="card-body text-center">
          {isSubmitted ? (
            <>
              <h1 className="h4 mb-3">Exam Submitted</h1>
              <p className="text-muted mb-1">{examTitle}</p>
              <p className="display-6 fw-bold mb-1">{session.score}%</p>
              <p className="text-muted small mb-4">
                Submitted at {new Date(session.ended_at).toLocaleString()}
              </p>
              <p className="small text-muted">
                Your submission has been recorded and is available for administrator review.
              </p>
            </>
          ) : (
            <>
              <h1 className="h4 mb-3 text-danger">Session Expired</h1>
              <p className="text-muted mb-1">{examTitle}</p>
              <p className="small text-muted mb-4">
                Your exam session expired before it was submitted, so no score was recorded.
              </p>
            </>
          )}
          <Link to="/student/exams" className="btn btn-primary">
            Back to Exams
          </Link>
        </div>
      </div>
    </div>
  )
}
