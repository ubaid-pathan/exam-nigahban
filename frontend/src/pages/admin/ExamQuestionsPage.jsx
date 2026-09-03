import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getExam } from '../../api/exams'
import { createQuestion, deleteQuestion, listQuestions, updateQuestion } from '../../api/questions'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'
import QuestionFormModal from '../../components/QuestionFormModal'
import { EditIcon, TrashIcon } from '../../components/admin/icons'

const STATUS_BADGE_CLASS = {
  draft: 'text-bg-secondary',
  active: 'text-bg-success',
  inactive: 'text-bg-warning',
}

function statusBadgeClass(examStatus) {
  return STATUS_BADGE_CLASS[examStatus] || 'text-bg-secondary'
}

function statusLabel(examStatus) {
  if (!examStatus) return 'Unknown'
  return examStatus.charAt(0).toUpperCase() + examStatus.slice(1)
}

export default function ExamQuestionsPage() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [exam, setExam] = useState(null)
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState('create')
  const [editingQuestion, setEditingQuestion] = useState(null)
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleteError, setDeleteError] = useState('')
  const [deleteSubmitting, setDeleteSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [examData, questionsData] = await Promise.all([
        getExam(examId),
        listQuestions(examId),
      ])
      setExam(examData)
      setQuestions(questionsData)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load this exam right now.'))
    } finally {
      setLoading(false)
    }
  }, [examId])

  useEffect(() => {
    load()
  }, [load])

  const openCreateForm = () => {
    setFormMode('create')
    setEditingQuestion(null)
    setFormError('')
    setFormOpen(true)
  }

  const openEditForm = (question) => {
    setFormMode('edit')
    setEditingQuestion(question)
    setFormError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    if (formSubmitting) return
    setFormOpen(false)
  }

  const handleFormSubmit = async (values) => {
    setFormSubmitting(true)
    setFormError('')
    try {
      if (formMode === 'create') {
        await createQuestion(examId, values)
        setSuccessMessage('Question added successfully.')
      } else {
        await updateQuestion(editingQuestion.id, values)
        setSuccessMessage('Question updated successfully.')
      }
      setFormOpen(false)
      await load()
    } catch (err) {
      setFormError(getErrorMessage(err, 'Unable to save this question right now.'))
    } finally {
      setFormSubmitting(false)
    }
  }

  const openDeleteConfirm = (question) => {
    setDeleteError('')
    setPendingDelete(question)
  }

  const closeDeleteConfirm = () => {
    if (deleteSubmitting) return
    setPendingDelete(null)
    setDeleteError('')
  }

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return
    setDeleteSubmitting(true)
    setDeleteError('')
    try {
      await deleteQuestion(pendingDelete.id)
      setSuccessMessage('Question deleted successfully.')
      setPendingDelete(null)
      await load()
    } catch (err) {
      setDeleteError(getErrorMessage(err, 'Unable to delete this question right now.'))
    } finally {
      setDeleteSubmitting(false)
    }
  }

  const editingInitialValues = editingQuestion
    ? {
        question_text: editingQuestion.question_text,
        option_a: editingQuestion.option_a,
        option_b: editingQuestion.option_b,
        option_c: editingQuestion.option_c,
        option_d: editingQuestion.option_d,
        correct_answer: editingQuestion.correct_answer,
      }
    : null

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-2">
        <div>
          <button
            type="button"
            className="btn btn-link p-0 mb-2"
            onClick={() => navigate('/admin/exams')}
          >
            &larr; Back to Exams
          </button>
          <h1 className="h4 mb-2">{exam ? `Questions — ${exam.title}` : 'Exam Questions'}</h1>
          {exam && (
            <div className="d-flex align-items-center gap-2 flex-wrap">
              <span className="badge text-bg-light text-dark border">
                {exam.duration_minutes} min
              </span>
              <span className={`badge ${statusBadgeClass(exam.status)}`}>
                {statusLabel(exam.status)}
              </span>
              <span className="badge text-bg-light text-dark border">
                {questions.length} question{questions.length === 1 ? '' : 's'}
              </span>
            </div>
          )}
        </div>
        {!loading && !error && (
          <button type="button" className="btn btn-primary btn-sm" onClick={openCreateForm}>
            Add Question
          </button>
        )}
      </div>

      {successMessage && (
        <div
          className="alert alert-success d-flex justify-content-between align-items-start"
          role="alert"
        >
          <span>{successMessage}</span>
          <button
            type="button"
            className="btn-close"
            aria-label="Dismiss"
            onClick={() => setSuccessMessage('')}
          />
        </div>
      )}

      {loading && <LoadingState message="Loading exam questions..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && questions.length === 0 && (
        <EmptyState title="No questions yet" message="Add the first question for this exam." />
      )}

      {!loading && !error && questions.length > 0 && (
        <>
          <div className="d-flex justify-content-end mb-2">
            <p className="text-muted small mb-0">
              {questions.length} question{questions.length === 1 ? '' : 's'}
            </p>
          </div>
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Option A</th>
                  <th>Option B</th>
                  <th>Option C</th>
                  <th>Option D</th>
                  <th>Correct</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((question) => (
                  <tr key={question.id}>
                    <td className="text-wrap-cell">{question.question_text}</td>
                    <td className="text-wrap-cell">{question.option_a}</td>
                    <td className="text-wrap-cell">{question.option_b}</td>
                    <td className="text-wrap-cell">{question.option_c}</td>
                    <td className="text-wrap-cell">{question.option_d}</td>
                    <td>
                      <span className="badge text-bg-success">
                        {question.correct_answer}
                      </span>
                    </td>
                    <td>
                      <div
                        className="d-flex flex-wrap align-items-center gap-2"
                        role="group"
                        aria-label="Question actions"
                      >
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
                          onClick={() => openEditForm(question)}
                        >
                          <EditIcon width={14} height={14} />
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger d-inline-flex align-items-center gap-1"
                          onClick={() => openDeleteConfirm(question)}
                        >
                          <TrashIcon width={14} height={14} />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {formOpen && (
        <QuestionFormModal
          mode={formMode}
          initialValues={editingInitialValues}
          submitting={formSubmitting}
          error={formError}
          onSubmit={handleFormSubmit}
          onCancel={closeForm}
        />
      )}

      {pendingDelete && (
        <ConfirmModal
          title="Delete Question?"
          confirmLabel={deleteSubmitting ? 'Deleting...' : 'Delete Question'}
          confirmVariant="danger"
          confirmDisabled={deleteSubmitting}
          onConfirm={handleConfirmDelete}
          onCancel={closeDeleteConfirm}
        >
          <p>Are you sure you want to permanently delete this question? This cannot be undone.</p>
          {deleteError && (
            <div className="alert alert-danger py-2 small mb-0" role="alert">
              {deleteError}
            </div>
          )}
        </ConfirmModal>
      )}
    </div>
  )
}
