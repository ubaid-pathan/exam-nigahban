import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAvailableExams } from '../../api/studentExams'
import { getErrorMessage } from '../../utils/apiError'
import { sessionStatusBadgeClass, sessionStatusLabel } from '../../utils/sessionStatus'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'

export default function ExamListPage() {
  const [exams, setExams] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listAvailableExams()
      setExams(data)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load exams right now.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) return <LoadingState message="Loading your exams..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!exams || exams.length === 0) {
    return (
      <EmptyState
        title="No exams available"
        message="There are currently no active exams assigned to you."
      />
    )
  }

  return (
    <div>
      <h1 className="h4 mb-4">Your Exams</h1>
      <div className="row g-3">
        {exams.map((exam) => (
          <div className="col-12 col-md-6 col-lg-4" key={exam.id}>
            <div className="card exam-card h-100">
              <div className="card-body d-flex flex-column">
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <h2 className="h6 mb-0">{exam.title}</h2>
                  <span className={`badge ${sessionStatusBadgeClass(exam.session_status)}`}>
                    {sessionStatusLabel(exam.session_status)}
                  </span>
                </div>
                <p className="text-muted small flex-grow-1">
                  {exam.description || 'No description provided.'}
                </p>
                <p className="small mb-3">Duration: {exam.duration_minutes} minutes</p>
                <Link to={`/student/exams/${exam.id}`} className="btn btn-primary btn-sm mt-auto">
                  View Exam
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
