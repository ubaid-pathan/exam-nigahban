import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getAvailableExam,
  getSession,
  getSessionAnswers,
  getSessionQuestions,
  saveAnswer,
  submitExam,
} from '../../api/studentExams'
import { getErrorMessage, getStatusCode } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import ExamTimer from '../../components/ExamTimer'
import QuestionPalette from '../../components/QuestionPalette'
import ConfirmModal from '../../components/ConfirmModal'

const RESYNC_INTERVAL_MS = 20000
const OPTIONS = [
  { key: 'A', field: 'option_a' },
  { key: 'B', field: 'option_b' },
  { key: 'C', field: 'option_c' },
  { key: 'D', field: 'option_d' },
]

export default function TakeExamPage() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [examTitle, setExamTitle] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [snapshot, setSnapshot] = useState(null) // { remainingSeconds, asOf, status }
  const [questions, setQuestions] = useState([])
  const [answersMap, setAnswersMap] = useState({})
  const [currentIndex, setCurrentIndex] = useState(0)

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [savingQuestionId, setSavingQuestionId] = useState(null)
  const [saveError, setSaveError] = useState('')

  const [locked, setLocked] = useState(false)
  const [lockReason, setLockReason] = useState('')

  const [showSubmitModal, setShowSubmitModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const lockedRef = useRef(false)
  useEffect(() => {
    lockedRef.current = locked
  }, [locked])

  const lockSession = useCallback(
    (reason) => {
      lockedRef.current = true
      setLocked(true)
      setLockReason(reason)
    },
    [],
  )

  const bootstrap = useCallback(async () => {
    setLoading(true)
    setLoadError('')
    try {
      const exam = await getAvailableExam(examId)
      setExamTitle(exam.title)

      if (exam.session_status === 'submitted' || exam.session_status === 'expired') {
        navigate(`/student/exams/${examId}/result`, { replace: true })
        return
      }
      if (exam.session_status !== 'in_progress' || !exam.session_id) {
        navigate(`/student/exams/${examId}/instructions`, { replace: true })
        return
      }

      const session = await getSession(exam.session_id)
      if (session.status !== 'in_progress') {
        navigate(`/student/exams/${examId}/result`, { replace: true })
        return
      }

      const [questionList, existingAnswers] = await Promise.all([
        getSessionQuestions(exam.session_id),
        getSessionAnswers(exam.session_id),
      ])

      const map = {}
      existingAnswers.forEach((answer) => {
        if (answer.selected_answer) {
          map[answer.question_id] = answer.selected_answer
        }
      })

      setSessionId(exam.session_id)
      setSnapshot({
        remainingSeconds: session.remaining_seconds,
        asOf: Date.now(),
        status: session.status,
      })
      setQuestions(questionList)
      setAnswersMap(map)
    } catch (err) {
      if (getStatusCode(err) === 409) {
        navigate(`/student/exams/${examId}/result`, { replace: true })
        return
      }
      setLoadError(getErrorMessage(err, 'Unable to load the exam.'))
    } finally {
      setLoading(false)
    }
  }, [examId, navigate])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  const resync = useCallback(async () => {
    if (!sessionId || lockedRef.current) return
    try {
      const session = await getSession(sessionId)
      setSnapshot({
        remainingSeconds: session.remaining_seconds,
        asOf: Date.now(),
        status: session.status,
      })
      if (session.status !== 'in_progress') {
        lockSession(
          session.status === 'expired'
            ? 'Your exam session has expired.'
            : 'This exam has already been submitted.',
        )
      }
    } catch {
      // A transient resync failure is not fatal; the next interval will retry.
    }
  }, [sessionId, lockSession])

  useEffect(() => {
    if (!sessionId) return undefined
    const interval = setInterval(resync, RESYNC_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [sessionId, resync])

  const handleTimerExpire = useCallback(() => {
    resync()
  }, [resync])

  const handleSelectAnswer = async (questionId, letter) => {
    if (locked) return
    const previous = answersMap[questionId]
    setAnswersMap((prev) => ({ ...prev, [questionId]: letter }))
    setSavingQuestionId(questionId)
    setSaveError('')
    try {
      await saveAnswer(sessionId, questionId, letter)
    } catch (err) {
      setAnswersMap((prev) => ({ ...prev, [questionId]: previous }))
      if (getStatusCode(err) === 409) {
        lockSession('Your exam session is no longer active. Your remaining answers were not saved.')
      } else {
        setSaveError(getErrorMessage(err, 'Failed to save your answer. Please try again.'))
      }
    } finally {
      setSavingQuestionId(null)
    }
  }

  const handleSubmit = async () => {
    setSubmitError('')
    setSubmitting(true)
    try {
      await submitExam(sessionId)
      navigate(`/student/exams/${examId}/result`, { replace: true })
    } catch (err) {
      if (getStatusCode(err) === 409) {
        navigate(`/student/exams/${examId}/result`, { replace: true })
        return
      }
      setSubmitError(getErrorMessage(err, 'Unable to submit the exam. Please try again.'))
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingState message="Loading your exam..." />
  if (loadError) return <ErrorState message={loadError} onRetry={bootstrap} />
  if (questions.length === 0) {
    return <ErrorState title="No Questions" message="This exam has no questions configured." />
  }

  const currentQuestion = questions[currentIndex]
  const answeredIds = new Set(Object.keys(answersMap).filter((k) => answersMap[k]).map(Number))
  const answeredCount = answeredIds.size

  return (
    <div className="no-select">
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h1 className="h5 mb-0">{examTitle}</h1>
        {snapshot && (
          <ExamTimer
            remainingSeconds={snapshot.remainingSeconds}
            asOf={snapshot.asOf}
            onExpire={handleTimerExpire}
          />
        )}
      </div>

      {locked && (
        <div className="alert alert-warning" role="alert">
          {lockReason}{' '}
          <button
            type="button"
            className="btn btn-sm btn-warning ms-2"
            onClick={() => navigate(`/student/exams/${examId}/result`, { replace: true })}
          >
            Continue
          </button>
        </div>
      )}

      <div className="row g-4">
        <div className="col-12 col-lg-8">
          <div className="card exam-card">
            <div className="card-body">
              <p className="text-muted small mb-1">
                Question {currentIndex + 1} of {questions.length}
              </p>
              <h2 className="h6 mb-3">{currentQuestion.question_text}</h2>

              <div className="d-flex flex-column gap-2 mb-3">
                {OPTIONS.map(({ key, field }) => (
                  <label
                    key={key}
                    className={`form-check border rounded p-2 ${
                      answersMap[currentQuestion.id] === key ? 'border-primary bg-light' : ''
                    }`}
                  >
                    <input
                      type="radio"
                      className="form-check-input me-2"
                      name={`question-${currentQuestion.id}`}
                      value={key}
                      checked={answersMap[currentQuestion.id] === key}
                      disabled={locked || savingQuestionId === currentQuestion.id}
                      onChange={() => handleSelectAnswer(currentQuestion.id, key)}
                    />
                    <span className="form-check-label">
                      <strong>{key}.</strong> {currentQuestion[field]}
                    </span>
                  </label>
                ))}
              </div>

              {savingQuestionId === currentQuestion.id && (
                <p className="small text-muted mb-2">Saving answer...</p>
              )}
              {saveError && (
                <div className="alert alert-danger py-2 small" role="alert">
                  {saveError}
                </div>
              )}

              <div className="d-flex justify-content-between mt-3">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
                >
                  Previous
                </button>
                {currentIndex < questions.length - 1 ? (
                  <button
                    type="button"
                    className="btn btn-outline-secondary"
                    onClick={() => setCurrentIndex((i) => Math.min(questions.length - 1, i + 1))}
                  >
                    Next
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-success"
                    disabled={locked}
                    onClick={() => setShowSubmitModal(true)}
                  >
                    Submit Exam
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-4">
          <div className="card exam-card">
            <div className="card-body">
              <h2 className="h6">Question Navigator</h2>
              <p className="small text-muted">
                {answeredCount} of {questions.length} answered
              </p>
              <QuestionPalette
                questions={questions}
                currentIndex={currentIndex}
                answeredIds={answeredIds}
                onSelect={setCurrentIndex}
              />
              <button
                type="button"
                className="btn btn-success w-100 mt-3"
                disabled={locked}
                onClick={() => setShowSubmitModal(true)}
              >
                Submit Exam
              </button>
            </div>
          </div>
        </div>
      </div>

      {showSubmitModal && (
        <ConfirmModal
          title="Submit Exam?"
          confirmLabel={submitting ? 'Submitting...' : 'Submit Exam'}
          confirmDisabled={submitting}
          onConfirm={handleSubmit}
          onCancel={() => !submitting && setShowSubmitModal(false)}
        >
          <p>
            You have answered <strong>{answeredCount}</strong> of{' '}
            <strong>{questions.length}</strong> questions.
          </p>
          <p className="mb-0 text-danger">
            Once submitted, you will not be able to change your answers. This action cannot be
            undone.
          </p>
          {submitError && (
            <div className="alert alert-danger py-2 small mt-2" role="alert">
              {submitError}
            </div>
          )}
        </ConfirmModal>
      )}
    </div>
  )
}
