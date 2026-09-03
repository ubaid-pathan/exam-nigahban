import { useCallback, useEffect, useState } from 'react'
import {
  createStudent,
  listStudents,
  updateStudent,
  updateStudentStatus,
} from '../../api/students'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'

const PAGE_SIZE = 10

const EMPTY_CREATE_FORM = {
  username: '',
  password: '',
  studentId: '',
  fullName: '',
  department: '',
  className: '',
}

function statusBadgeClass(isActiveAccount) {
  return isActiveAccount ? 'text-bg-success' : 'text-bg-warning'
}

function statusLabel(isActiveAccount) {
  return isActiveAccount ? 'Active' : 'Inactive'
}

export default function StudentManagementPage() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ total: 0, total_pages: 0 })

  const [formOpen, setFormOpen] = useState(false)
  const [formMode, setFormMode] = useState('create')
  const [editingStudent, setEditingStudent] = useState(null)
  const [formValues, setFormValues] = useState(EMPTY_CREATE_FORM)
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)

  const [pendingAction, setPendingAction] = useState(null)
  const [actionError, setActionError] = useState('')
  const [actionSubmitting, setActionSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listStudents({ search, page, pageSize: PAGE_SIZE })
      setStudents(data.items)
      setPagination({ total: data.total, total_pages: data.total_pages })
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load students right now.'))
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => {
    load()
  }, [load])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setSearch(searchInput.trim())
    setPage(1)
  }

  const handleClearSearch = () => {
    setSearchInput('')
    setSearch('')
    setPage(1)
  }

  const handlePrevious = () => setPage((current) => Math.max(1, current - 1))
  const handleNext = () =>
    setPage((current) => (current < pagination.total_pages ? current + 1 : current))

  const openCreateForm = () => {
    setFormMode('create')
    setEditingStudent(null)
    setFormValues(EMPTY_CREATE_FORM)
    setFormError('')
    setFormOpen(true)
  }

  const openEditForm = (student) => {
    setFormMode('edit')
    setEditingStudent(student)
    setFormValues({
      fullName: student.full_name,
      department: student.department || '',
      className: student.class_name || '',
    })
    setFormError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    if (formSubmitting) return
    setFormOpen(false)
  }

  const handleFormSubmit = async () => {
    const fullName = formValues.fullName.trim()
    if (!fullName) {
      setFormError('Full name is required.')
      return
    }

    if (formMode === 'create') {
      const username = formValues.username.trim()
      const studentId = formValues.studentId.trim()
      const password = formValues.password

      if (!username) {
        setFormError('Username is required.')
        return
      }
      if (!studentId) {
        setFormError('Student ID is required.')
        return
      }
      if (!password || password.length < 8) {
        setFormError('Password must be at least 8 characters.')
        return
      }

      setFormSubmitting(true)
      setFormError('')
      try {
        await createStudent({
          username,
          password,
          studentId,
          fullName,
          department: formValues.department.trim(),
          className: formValues.className.trim(),
        })
        setSuccessMessage('Student created successfully.')
        setFormOpen(false)
        setPage(1)
        await load()
      } catch (err) {
        setFormError(getErrorMessage(err, 'Unable to create the student right now.'))
      } finally {
        setFormSubmitting(false)
      }
      return
    }

    setFormSubmitting(true)
    setFormError('')
    try {
      await updateStudent(editingStudent.id, {
        fullName,
        department: formValues.department.trim(),
        className: formValues.className.trim(),
      })
      setSuccessMessage('Student updated successfully.')
      setFormOpen(false)
      await load()
    } catch (err) {
      setFormError(getErrorMessage(err, 'Unable to update the student right now.'))
    } finally {
      setFormSubmitting(false)
    }
  }

  const openPendingAction = (type, student) => {
    setActionError('')
    setPendingAction({ type, student })
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
      const activate = pendingAction.type === 'activate'
      await updateStudentStatus(pendingAction.student.id, activate)
      setSuccessMessage(
        activate ? 'Student activated successfully.' : 'Student deactivated successfully.',
      )
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
          <h1 className="h4 mb-1">Student Management</h1>
          <p className="text-muted small mb-0">View, update, and manage student accounts.</p>
        </div>
        <button type="button" className="btn btn-primary btn-sm" onClick={openCreateForm}>
          Create Student
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

      <form className="row g-2 align-items-end mb-4" onSubmit={handleSearchSubmit}>
        <div className="col-12 col-md-4">
          <label htmlFor="student-search" className="form-label small">
            Search
          </label>
          <input
            id="student-search"
            type="text"
            className="form-control form-control-sm"
            placeholder="Name, student ID, or username"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        <div className="col-auto d-flex gap-2">
          <button type="submit" className="btn btn-outline-primary btn-sm">
            Search
          </button>
          {search && (
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={handleClearSearch}
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {loading && <LoadingState message="Loading students..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && students.length === 0 && (
        <EmptyState
          title="No students found"
          message={
            search
              ? 'No students match your search.'
              : 'Create your first student account to get started.'
          }
        />
      )}

      {!loading && !error && students.length > 0 && (
        <>
          <div className="card shadow-sm">
            <div className="card-header bg-white d-flex justify-content-between align-items-center">
              <span className="fw-semibold">Students</span>
              <span className="text-muted small">{pagination.total} total</span>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th className="ps-3">Student ID</th>
                      <th>Full Name</th>
                      <th>Username</th>
                      <th>Department</th>
                      <th>Class</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th className="pe-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((student) => (
                      <tr key={student.id}>
                        <td className="ps-3">{student.student_id}</td>
                        <td className="fw-semibold">{student.full_name}</td>
                        <td>{student.username}</td>
                        <td>{student.department || <span className="text-muted">&mdash;</span>}</td>
                        <td>{student.class_name || <span className="text-muted">&mdash;</span>}</td>
                        <td>
                          <span className={`badge ${statusBadgeClass(student.account_status)}`}>
                            {statusLabel(student.account_status)}
                          </span>
                        </td>
                        <td className="text-nowrap text-muted small">
                          {new Date(student.created_at).toLocaleDateString(undefined, {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>
                        <td className="pe-3">
                          <div className="btn-group btn-group-sm" role="group" aria-label="Student actions">
                            <button
                              type="button"
                              className="btn btn-outline-secondary"
                              onClick={() => openEditForm(student)}
                            >
                              Edit
                            </button>
                            {student.account_status ? (
                              <button
                                type="button"
                                className="btn btn-outline-warning"
                                onClick={() => openPendingAction('deactivate', student)}
                              >
                                Deactivate
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="btn btn-outline-success"
                                onClick={() => openPendingAction('activate', student)}
                              >
                                Activate
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="d-flex justify-content-between align-items-center mt-3">
            <p className="text-muted small mb-0">
              Page {page} of {pagination.total_pages} (Total: {pagination.total})
            </p>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={handlePrevious}
                disabled={page <= 1}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={handleNext}
                disabled={page >= pagination.total_pages}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {formOpen && (
        <ConfirmModal
          title={formMode === 'create' ? 'Create Student' : `Edit ${editingStudent?.full_name}`}
          confirmLabel={
            formSubmitting ? 'Saving...' : formMode === 'create' ? 'Create Student' : 'Save Changes'
          }
          confirmDisabled={formSubmitting}
          onConfirm={handleFormSubmit}
          onCancel={closeForm}
          size="lg"
        >
          {formMode === 'create' && (
            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <label htmlFor="student-username" className="form-label fw-semibold">
                  Username
                </label>
                <input
                  id="student-username"
                  type="text"
                  className="form-control"
                  value={formValues.username}
                  disabled={formSubmitting}
                  onChange={(e) => setFormValues((f) => ({ ...f, username: e.target.value }))}
                />
              </div>
              <div className="col-md-6">
                <label htmlFor="student-password" className="form-label fw-semibold">
                  Password
                </label>
                <input
                  id="student-password"
                  type="password"
                  className="form-control"
                  value={formValues.password}
                  disabled={formSubmitting}
                  onChange={(e) => setFormValues((f) => ({ ...f, password: e.target.value }))}
                />
              </div>
              <div className="col-md-6">
                <label htmlFor="student-code" className="form-label fw-semibold">
                  Student ID
                </label>
                <input
                  id="student-code"
                  type="text"
                  className="form-control"
                  value={formValues.studentId}
                  disabled={formSubmitting}
                  onChange={(e) => setFormValues((f) => ({ ...f, studentId: e.target.value }))}
                />
              </div>
            </div>
          )}

          <div className="row g-3 mb-3">
            <div className={formMode === 'create' ? 'col-md-6' : 'col-12'}>
              <label htmlFor="student-full-name" className="form-label fw-semibold">
                Full Name
              </label>
              <input
                id="student-full-name"
                type="text"
                className="form-control"
                value={formValues.fullName}
                maxLength={150}
                disabled={formSubmitting}
                onChange={(e) => setFormValues((f) => ({ ...f, fullName: e.target.value }))}
              />
            </div>
          </div>
          <div className="row g-3 mb-3">
            <div className="col-md-6">
              <label htmlFor="student-department" className="form-label fw-semibold">
                Department
              </label>
              <input
                id="student-department"
                type="text"
                className="form-control"
                value={formValues.department}
                disabled={formSubmitting}
                onChange={(e) => setFormValues((f) => ({ ...f, department: e.target.value }))}
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="student-class" className="form-label fw-semibold">
                Class
              </label>
              <input
                id="student-class"
                type="text"
                className="form-control"
                value={formValues.className}
                disabled={formSubmitting}
                onChange={(e) => setFormValues((f) => ({ ...f, className: e.target.value }))}
              />
            </div>
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
          title={pendingAction.type === 'activate' ? 'Activate Student?' : 'Deactivate Student?'}
          confirmLabel={
            actionSubmitting
              ? 'Working...'
              : pendingAction.type === 'activate'
                ? 'Activate'
                : 'Deactivate'
          }
          confirmDisabled={actionSubmitting}
          onConfirm={handleConfirmAction}
          onCancel={closePendingAction}
        >
          {pendingAction.type === 'activate' ? (
            <p>
              Activate <strong>{pendingAction.student.full_name}</strong>? They will be able to log
              in again.
            </p>
          ) : (
            <p>
              Deactivate <strong>{pendingAction.student.full_name}</strong>? They will no longer be
              able to log in. Any exam in progress is not affected.
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
