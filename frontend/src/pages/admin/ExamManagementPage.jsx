import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createExam, deleteExam, listExams, updateExam, updateExamStatus } from '../../api/exams'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'

const EMPTY_FORM = { title: '', description: '', durationMinutes: '' }

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

export default function ExamManagementPage() {
  const navigate = useNavigate()
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState('create')
  const [editingExamId, setEditingExamId] = useState(null)
  const [formValues, setFormValues] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [pendingAction, setPendingAction] = useState(null)
  const [actionError, setActionError] = useState('')
  const [actionSubmitting, setActionSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listExams()
      setExams(data)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load exams right now.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const openCreateForm = () => {
    setFormMode('create')
    setEditingExamId(null)
    setFormValues(EMPTY_FORM)
    setFormError('')
    setFormOpen(true)
  }

  const openEditForm = (exam) => {
    setFormMode('edit')
    setEditingExamId(exam.id)
    setFormValues({
      title: exam.title,
      description: exam.description || '',
      durationMinutes: String(exam.duration_minutes),
    })
    setFormError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    if (formSubmitting) return
    setFormOpen(false)
  }

  const handleFormSubmit = async () => {
    const title = formValues.title.trim()
    const durationMinutes = Number(formValues.durationMinutes)

    if (!title) {
      setFormError('Title is required.')
      return
    }
    if (!Number.isInteger(durationMinutes) || durationMinutes <= 0) {
      setFormError('Duration must be a whole number of minutes greater than zero.')
      return
    }

    setFormSubmitting(true)
    setFormError('')
    try {
      if (formMode === 'create') {
        await createExam({ title, description: formValues.description.trim(), durationMinutes })
        setSuccessMessage('Exam created successfully.')
      } else {
        await updateExam(editingExamId, {
          title,
          description: formValues.description.trim(),
          durationMinutes,
        })
        setSuccessMessage('Exam updated successfully.')
      }
      setFormOpen(false)
      await load()
    } catch (err) {
      setFormError(getErrorMessage(err, 'Unable to save the exam right now.'))
    } finally {
      setFormSubmitting(false)
    }
  }

  const openPendingAction = (type, exam) => {
    setActionError('')
    setPendingAction({ type, exam })
  }

  const closePendingAction = () => {
    if (actionSubmitting) return
    setPendingAction(null)
    setActionError('')
  }

  const handleConfirmAction = async () => {
    if (!pendingAction) return
    setActionSubmitting(true)
    setActionError('')
    try {
      if (pendingAction.type === 'delete') {
        await deleteExam(pendingAction.exam.id)
        setSuccessMessage('Exam deleted successfully.')
      } else if (pendingAction.type === 'activate') {
        await updateExamStatus(pendingAction.exam.id, 'active')
        setSuccessMessage('Exam activated successfully.')
      } else if (pendingAction.type === 'deactivate') {
        await updateExamStatus(pendingAction.exam.id, 'inactive')
        setSuccessMessage('Exam deactivated successfully.')
      }
      setPendingAction(null)
      await load()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Unable to complete this action right now.'))
    } finally {
      setActionSubmitting(false)
    }
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-2">
        <div>
          <h1 className="h4 mb-1">Exam Management</h1>
          <p className="text-muted small mb-0">
            Create, organize, and manage your examinations.
          </p>
        </div>
        <button type="button" className="btn btn-primary btn-sm" onClick={openCreateForm}>
          Create Exam
        </button>
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

      {loading && <LoadingState message="Loading exams..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && exams.length === 0 && (
        <EmptyState title="No exams yet" message="Create your first exam to get started." />
      )}

      {!loading && !error && exams.length > 0 && (
        <div className="card shadow-sm">
          <div className="card-header bg-white d-flex justify-content-between align-items-center">
            <span className="fw-semibold">All Exams</span>
            <span className="text-muted small">
              {exams.length} exam{exams.length === 1 ? '' : 's'}
            </span>
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="ps-3">Title</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Questions</th>
                    <th>Created</th>
                    <th className="pe-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {exams.map((exam) => (
                    <tr key={exam.id}>
                      <td className="ps-3">
                        <div className="fw-semibold">{exam.title}</div>
                        {exam.description && (
                          <div className="text-muted small">{exam.description}</div>
                        )}
                      </td>
                      <td>{exam.duration_minutes} min</td>
                      <td>
                        <span className={`badge ${statusBadgeClass(exam.status)}`}>
                          {statusLabel(exam.status)}
                        </span>
                      </td>
                      <td>
                        <span className="badge text-bg-light text-dark border">
                          {exam.question_count} question{exam.question_count === 1 ? '' : 's'}
                        </span>
                      </td>
                      <td className="text-nowrap text-muted small">
                        {new Date(exam.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td className="pe-3">
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <div className="btn-group btn-group-sm" role="group" aria-label="Exam actions">
                            <button
                              type="button"
                              className="btn btn-outline-secondary"
                              onClick={() => openEditForm(exam)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline-primary"
                              onClick={() => navigate(`/admin/exams/${exam.id}/questions`)}
                            >
                              Questions
                            </button>
                            {exam.status === 'active' ? (
                              <button
                                type="button"
                                className="btn btn-outline-warning"
                                onClick={() => openPendingAction('deactivate', exam)}
                              >
                                Deactivate
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn btn-outline-success"
                                onClick={() => openPendingAction('activate', exam)}
                              >
                                Activate
                              </button>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => openPendingAction('delete', exam)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {formOpen && (
        <ConfirmModal
          title={formMode === 'create' ? 'Create Exam' : 'Edit Exam'}
          confirmLabel={
            formSubmitting ? 'Saving...' : formMode === 'create' ? 'Create Exam' : 'Save Changes'
          }
          confirmDisabled={formSubmitting}
          onConfirm={handleFormSubmit}
          onCancel={closeForm}
          size="lg"
        >
          <div className="row g-3 mb-3">
            <div className="col-md-8">
              <label htmlFor="exam-title" className="form-label fw-semibold">
                Title
              </label>
              <input
                id="exam-title"
                type="text"
                className="form-control"
                value={formValues.title}
                maxLength={150}
                disabled={formSubmitting}
                onChange={(e) => setFormValues((f) => ({ ...f, title: e.target.value }))}
              />
            </div>
            <div className="col-md-4">
              <label htmlFor="exam-duration" className="form-label fw-semibold">
                Duration (minutes)
              </label>
              <input
                id="exam-duration"
                type="number"
                min="1"
                className="form-control"
                value={formValues.durationMinutes}
                disabled={formSubmitting}
                onChange={(e) =>
                  setFormValues((f) => ({ ...f, durationMinutes: e.target.value }))
                }
              />
            </div>
          </div>
          <div className="mb-3">
            <label htmlFor="exam-description" className="form-label fw-semibold">
              Description
            </label>
            <textarea
              id="exam-description"
              className="form-control"
              rows={4}
              value={formValues.description}
              disabled={formSubmitting}
              onChange={(e) => setFormValues((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          {formError && (
            <div className="alert alert-danger py-2 small mb-0" role="alert">
              {formError}
            </div>
          )}
        </ConfirmModal>
      )}

      {pendingAction && (
        <ConfirmModal
          title={
            pendingAction.type === 'delete'
              ? 'Delete Exam?'
              : pendingAction.type === 'activate'
                ? 'Activate Exam?'
                : 'Deactivate Exam?'
          }
          confirmLabel={
            actionSubmitting
              ? 'Working...'
              : pendingAction.type === 'delete'
                ? 'Delete'
                : pendingAction.type === 'activate'
                  ? 'Activate'
                  : 'Deactivate'
          }
          confirmDisabled={actionSubmitting}
          onConfirm={handleConfirmAction}
          onCancel={closePendingAction}
        >
          {pendingAction.type === 'delete' && (
            <p>
              Are you sure you want to permanently delete{' '}
              <strong>{pendingAction.exam.title}</strong>? This cannot be undone.
            </p>
          )}
          {pendingAction.type === 'activate' && (
            <p>
              Activate <strong>{pendingAction.exam.title}</strong>? Students will be able to see
              and attempt it.
            </p>
          )}
          {pendingAction.type === 'deactivate' && (
            <p>
              Deactivate <strong>{pendingAction.exam.title}</strong>? Students will no longer be
              able to start it.
            </p>
          )}
          {actionError && (
            <div className="alert alert-danger py-2 small mb-0" role="alert">
              {actionError}
            </div>
          )}
        </ConfirmModal>
      )}
    </div>
  )
}
