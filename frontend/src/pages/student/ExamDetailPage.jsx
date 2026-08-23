import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getAvailableExam } from '../../api/studentExams'
import { getErrorMessage, getStatusCode } from '../../utils/apiError'
import { sessionStatusBadgeClass, sessionStatusLabel } from '../../utils/sessionStatus'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'

export default function ExamDetailPage() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const [exam, setExam] = useState(null)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    setNotFound(false)
    try {
      const data = await getAvailableExam(examId)
      setExam(data)
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

  if (loading) return <LoadingState message="Loading exam details..." />
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

  const goToNextStep = () => {
    if (exam.session_status === 'in_progress') {
      navigate(`/student/exams/${examId}/take`)
    } else if (exam.session_status === 'submitted' || exam.session_status === 'expired') {
      navigate(`/student/exams/${examId}/result`)
    } else {
      navigate(`/student/exams/${examId}/instructions`)
    }
  }

  const actionLabel =
    exam.session_status === 'in_progress'
      ? 'Resume Exam'
      : exam.session_status === 'submitted' || exam.session_status === 'expired'
        ? 'View Result'
        : 'Start Exam'

  return (
    <div>
      <Link to="/student/exams" className="d-inline-block mb-3 small">
        &larr; Back to exams
      </Link>
      <div className="card exam-card">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <h1 className="h4 mb-0">{exam.title}</h1>
            <span className={`badge ${sessionStatusBadgeClass(exam.session_status)}`}>
              {sessionStatusLabel(exam.session_status)}
            </span>
          </div>
          <p className="text-muted">{exam.description || 'No description provided.'}</p>
          <p className="mb-4">
            <strong>Duration:</strong> {exam.duration_minutes} minutes
          </p>
          <button type="button" className="btn btn-primary" onClick={goToNextStep}>
            {actionLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
