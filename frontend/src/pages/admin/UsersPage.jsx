import { useCallback, useEffect, useState } from 'react'
import { createStudent, listStudents, updateStudent, updateStudentStatus } from '../../api/students'
import { createAdmin, listAdmins, updateAdminStatus } from '../../api/admins'
import { useAuth } from '../../context/AuthContext'
import { getErrorMessage } from '../../utils/apiError'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'
import ConfirmModal from '../../components/ConfirmModal'
import CreateUserDialog from '../../components/admin/CreateUserDialog'
import { EditIcon, PauseIcon, PlayIcon } from '../../components/admin/icons'

const PAGE_SIZE = 10
// The two source endpoints each paginate independently server-side; a
// single merged Users table instead fetches one large page from each (the
// backend's own max) and paginates the merged result client-side. Safe for
// this system's realistic admin/student roster sizes without requiring any
// backend endpoint changes.
const SOURCE_PAGE_SIZE = 100

const EMPTY_EDIT_FORM = { fullName: '', department: '', className: '' }

function statusBadgeClass(isActive) {
  return isActive ? 'text-bg-success' : 'text-bg-warning'
}

function statusLabel(isActive) {
  return isActive ? 'Active' : 'Inactive'
}

function roleBadgeClass(role) {
  // Matches the badge styling already used elsewhere in the app: Admin
  // mirrors the primary-colored "Admin" badge in AdminSidebar/AdminLayout,
  // Student mirrors the secondary/grey "Student" badge in StudentLayout.
  return role === 'admin' ? 'text-bg-primary' : 'text-bg-secondary'
}

function dash(value) {
  return value || <span className="text-muted">&mdash;</span>
}

function normalizeStudent(student) {
  return {
    key: `student-${student.id}`,
    role: 'student',
    name: student.full_name,
    idNumber: student.student_id,
    email: student.email,
    program: student.department,
    section: student.class_name,
    status: student.account_status,
    isSystemAdmin: false,
    raw: student,
  }
}

function normalizeAdmin(admin) {
  return {
    key: `admin-${admin.id}`,
    // The account's identity/display name -- admins have no separate
    // full_name unless one was set at creation (see backend
    // app/models/user.py), so fall back to username, exactly as the old
    // AdminManagementPage table already did.
    role: 'admin',
    name: admin.full_name || admin.username,
    idNumber: null,
    email: admin.email,
    program: null,
    section: null,
    status: admin.status,
    // The protected root account: badged in the table and its deactivate
    // control replaced by an explanation. The backend refuses the request
    // regardless (403) -- this only stops the UI offering an action that
    // cannot succeed.
    isSystemAdmin: Boolean(admin.is_system_admin),
    raw: admin,
  }
}

export default function UsersPage() {
  const { user: currentAdmin } = useAuth()

  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const [createOpen, setCreateOpen] = useState(false)
  const [createSubmitting, setCreateSubmitting] = useState(false)
  const [createError, setCreateError] = useState('')

  const [editingRow, setEditingRow] = useState(null)
  const [editValues, setEditValues] = useState(EMPTY_EDIT_FORM)
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [editError, setEditError] = useState('')

  const [pendingAction, setPendingAction] = useState(null)
  const [actionError, setActionError] = useState('')
  const [actionSubmitting, setActionSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [studentsData, adminsData] = await Promise.all([
        listStudents({ search, page: 1, pageSize: SOURCE_PAGE_SIZE }),
        listAdmins({ search, page: 1, pageSize: SOURCE_PAGE_SIZE }),
      ])
      const merged = [
        ...studentsData.items.map(normalizeStudent),
        ...adminsData.items.map(normalizeAdmin),
      ].sort((a, b) => a.name.localeCompare(b.name))
      setRows(merged)
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to load users right now.'))
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))
  const pageRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

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
  const handleNext = () => setPage((current) => Math.min(totalPages, current + 1))

  const openCreate = () => {
    setCreateError('')
    setCreateOpen(true)
  }

  const closeCreate = () => {
    if (createSubmitting) return
    setCreateOpen(false)
  }

  const handleCreateSubmit = async (values) => {
    setCreateSubmitting(true)
    setCreateError('')
    try {
      if (values.role === 'student') {
        await createStudent({
          username: values.username,
          password: values.password,
          studentId: values.studentId,
          fullName: values.fullName,
          email: values.email,
          department: values.department,
          className: values.className,
        })
      } else {
        await createAdmin(values)
      }
      setSuccessMessage(
        values.role === 'student' ? 'Student created successfully.' : 'Admin created successfully.',
      )
      setCreateOpen(false)
      setPage(1)
      await load()
    } catch (err) {
      setCreateError(getErrorMessage(err, 'Unable to create the user right now.'))
    } finally {
      setCreateSubmitting(false)
    }
  }

  const openEdit = (row) => {
    setEditingRow(row)
    setEditValues({
      fullName: row.raw.full_name,
      department: row.raw.department || '',
      className: row.raw.class_name || '',
    })
    setEditError('')
  }

  const closeEdit = () => {
    if (editSubmitting) return
    setEditingRow(null)
  }

  const handleEditSubmit = async () => {
    const fullName = editValues.fullName.trim()
    if (!fullName) {
      setEditError('Full name is required.')
      return
    }
    setEditSubmitting(true)
    setEditError('')
    try {
      await updateStudent(editingRow.raw.id, {
        fullName,
        department: editValues.department.trim(),
        className: editValues.className.trim(),
      })
      setSuccessMessage('Student updated successfully.')
      setEditingRow(null)
      await load()
    } catch (err) {
      setEditError(getErrorMessage(err, 'Unable to update the student right now.'))
    } finally {
      setEditSubmitting(false)
    }
  }

  const openPendingAction = (type, row) => {
    setActionError('')
    setPendingAction({ type, row })
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
      if (pendingAction.row.role === 'student') {
        await updateStudentStatus(pendingAction.row.raw.id, activate)
      } else {
        await updateAdminStatus(pendingAction.row.raw.id, activate)
      }
      setSuccessMessage(activate ? 'User activated successfully.' : 'User deactivated successfully.')
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
          <h1 className="h4 mb-1">Users</h1>
          <p className="text-muted small mb-0">Manage students and administrators.</p>
        </div>
        <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
          + Create User
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
          <label htmlFor="user-search" className="form-label small">
            Search
          </label>
          <input
            id="user-search"
            type="text"
            className="form-control form-control-sm"
            placeholder="Name, ID, or username"
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

      {loading && <LoadingState message="Loading users..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && rows.length === 0 && (
        <EmptyState
          title="No users found"
          message={search ? 'No users match your search.' : 'Create your first user to get started.'}
        />
      )}

      {!loading && !error && rows.length > 0 && (
        <>
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>ID No.</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Program</th>
                  <th>Section</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => {
                  const isSelfAdmin =
                    row.role === 'admin' && currentAdmin && row.raw.id === currentAdmin.id
                  return (
                    <tr key={row.key}>
                      <td className="fw-semibold">
                        {row.name}
                        {isSelfAdmin && (
                          <span className="badge text-bg-light text-dark border ms-2">You</span>
                        )}
                      </td>
                      <td>{dash(row.idNumber)}</td>
                      <td>{dash(row.email)}</td>
                      <td>
                        <span className={`badge ${roleBadgeClass(row.role)}`}>
                          {row.role === 'admin' ? 'Admin' : 'Student'}
                        </span>
                      </td>
                      <td>{dash(row.program)}</td>
                      <td>{dash(row.section)}</td>
                      <td>
                        <span className={`badge ${statusBadgeClass(row.status)}`}>
                          {statusLabel(row.status)}
                        </span>
                        {/* Marks the protected root account. Shown rather
                            than hidden: a control disabled for a stated
                            reason reads as intentional, whereas a row that
                            simply behaves differently reads as a bug. */}
                        {row.isSystemAdmin && (
                          <span className="badge text-bg-dark ms-1">System Admin</span>
                        )}
                      </td>
                      <td>
                        {/* Flat flex row rather than a fused .btn-group --
                            matches ExamManagementPage.jsx's Actions column,
                            so every button can wrap independently instead
                            of the group staying rigid on narrow widths. */}
                        <div
                          className="d-flex flex-wrap align-items-center gap-2"
                          role="group"
                          aria-label="User actions"
                        >
                          {row.role === 'student' && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
                              onClick={() => openEdit(row)}
                            >
                              <EditIcon width={14} height={14} />
                              Edit
                            </button>
                          )}
                          {row.isSystemAdmin ? (
                            <span className="text-muted small">
                              Protected account &mdash; cannot be deactivated
                            </span>
                          ) : isSelfAdmin ? (
                            <span className="text-muted small">
                              You cannot deactivate your own account
                            </span>
                          ) : row.status ? (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-warning d-inline-flex align-items-center gap-1"
                              onClick={() => openPendingAction('deactivate', row)}
                            >
                              <PauseIcon width={14} height={14} />
                              Deactivate
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-success d-inline-flex align-items-center gap-1"
                              onClick={() => openPendingAction('activate', row)}
                            >
                              <PlayIcon width={14} height={14} />
                              Activate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="d-flex justify-content-between align-items-center mt-3">
            <p className="text-muted small mb-0">
              Page {page} of {totalPages} (Total: {rows.length})
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
                disabled={page >= totalPages}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {createOpen && (
        <CreateUserDialog
          submitting={createSubmitting}
          error={createError}
          onSubmit={handleCreateSubmit}
          onCancel={closeCreate}
        />
      )}

      {editingRow && (
        <ConfirmModal
          title={`Edit ${editingRow.name}`}
          confirmLabel={editSubmitting ? 'Saving...' : 'Save Changes'}
          confirmDisabled={editSubmitting}
          onConfirm={handleEditSubmit}
          onCancel={closeEdit}
          size="lg"
        >
          <div className="row g-3 mb-3">
            <div className="col-12">
              <label htmlFor="edit-user-full-name" className="form-label fw-semibold">
                Full Name
              </label>
              <input
                id="edit-user-full-name"
                type="text"
                className="form-control"
                maxLength={150}
                value={editValues.fullName}
                disabled={editSubmitting}
                onChange={(e) => setEditValues((f) => ({ ...f, fullName: e.target.value }))}
              />
            </div>
          </div>
          <div className="row g-3 mb-3">
            <div className="col-md-6">
              <label htmlFor="edit-user-program" className="form-label fw-semibold">
                Program
              </label>
              <input
                id="edit-user-program"
                type="text"
                className="form-control"
                value={editValues.department}
                disabled={editSubmitting}
                onChange={(e) => setEditValues((f) => ({ ...f, department: e.target.value }))}
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="edit-user-section" className="form-label fw-semibold">
                Section
              </label>
              <input
                id="edit-user-section"
                type="text"
                className="form-control"
                value={editValues.className}
                disabled={editSubmitting}
                onChange={(e) => setEditValues((f) => ({ ...f, className: e.target.value }))}
              />
            </div>
          </div>
          {editError && (
            <div className="alert alert-danger py-2 small mb-0" role="alert">
              {editError}
            </div>
          )}
        </ConfirmModal>
      )}

      {pendingAction && (
        <ConfirmModal
          title={pendingAction.type === 'activate' ? 'Activate User?' : 'Deactivate User?'}
          confirmLabel={
            actionSubmitting ? 'Working...' : pendingAction.type === 'activate' ? 'Activate' : 'Deactivate'
          }
          confirmDisabled={actionSubmitting}
          onConfirm={handleConfirmAction}
          onCancel={closePendingAction}
        >
          {pendingAction.type === 'activate' ? (
            <p>
              Activate <strong>{pendingAction.row.name}</strong>? They will be able to log in again.
            </p>
          ) : (
            <p>
              Deactivate <strong>{pendingAction.row.name}</strong>? They will no longer be able to log
              in.
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
