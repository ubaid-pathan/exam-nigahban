import { useState } from 'react'
import ConfirmModal from '../ConfirmModal'
import { EMPTY_USER_FORM, validateUserForm } from '../../utils/userValidation'

// Reuses ConfirmModal (size="xl" for the wide, multi-column layout) exactly
// like QuestionFormModal does -- no new modal component/library. Every
// field sits in the same `row g-3` using `col-12 col-sm-6 col-lg-4`, so
// Bootstrap's own grid gives the required 1/2/3-column responsive layout
// (mobile/tablet/desktop) without any custom breakpoint CSS, and fields
// simply reflow when Program/Section/ID appear or disappear rather than
// leaving a hand-placed row with a gap in it.
export default function CreateUserDialog({ submitting, error, onSubmit, onCancel }) {
  const [values, setValues] = useState(EMPTY_USER_FORM)
  const [validationError, setValidationError] = useState('')

  const isStudent = values.role === 'student'

  const setField = (field) => (event) => {
    setValues((current) => ({ ...current, [field]: event.target.value }))
  }

  const handleRoleChange = (event) => {
    const role = event.target.value
    setValues((current) => ({
      ...current,
      role,
      // Cleared from state, not just hidden -- switching back to Student
      // starts from a blank Program/Section rather than resurrecting a
      // stale value, and switching to Admin guarantees nothing is left in
      // state that could accidentally be submitted.
      ...(role === 'admin' ? { idNumber: '', program: '', section: '' } : {}),
    }))
  }

  const handleConfirm = () => {
    const message = validateUserForm(values)
    if (message) {
      setValidationError(message)
      return
    }
    setValidationError('')

    const base = {
      username: values.username.trim(),
      password: values.password,
      fullName: values.fullName.trim(),
      email: values.email.trim(),
    }

    onSubmit(
      isStudent
        ? {
            role: 'student',
            ...base,
            studentId: values.idNumber.trim(),
            department: values.program.trim(),
            className: values.section.trim(),
          }
        : { role: 'admin', ...base },
    )
  }

  const displayError = validationError || error

  return (
    <ConfirmModal
      title="Create User"
      confirmLabel={submitting ? 'Creating...' : 'Create User'}
      confirmDisabled={submitting}
      onConfirm={handleConfirm}
      onCancel={onCancel}
      size="xl"
    >
      {/* Decoy fields: Chrome ignores autocomplete="off" on username/password
          inputs and autofills the signed-in admin's own saved credentials
          into this account-creation form regardless -- these absorb that
          autofill instead of the real fields below them. Hidden from view
          and from screen readers/tab order; never read from. */}
      <div aria-hidden="true" style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden' }}>
        <input type="text" name="username" tabIndex={-1} autoComplete="username" />
        <input type="password" name="password" tabIndex={-1} autoComplete="current-password" />
      </div>
      <div className="row g-3 mb-3">
        <div className="col-12 col-sm-6 col-lg-4">
          <label htmlFor="user-username" className="form-label fw-semibold">
            Username
          </label>
          <input
            id="user-username"
            type="text"
            className="form-control"
            autoComplete="off"
            value={values.username}
            disabled={submitting}
            onChange={setField('username')}
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-4">
          <label htmlFor="user-password" className="form-label fw-semibold">
            Password
          </label>
          <input
            id="user-password"
            type="password"
            className="form-control"
            // This creates a NEW account's password, not a login -- without
            // an explicit autocomplete hint, the browser matches the
            // adjacent username+password inputs as a login form and
            // autofills the currently signed-in admin's own saved
            // credentials into them.
            autoComplete="new-password"
            value={values.password}
            disabled={submitting}
            onChange={setField('password')}
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-4">
          <label htmlFor="user-full-name" className="form-label fw-semibold">
            Full Name
          </label>
          <input
            id="user-full-name"
            type="text"
            className="form-control"
            maxLength={150}
            value={values.fullName}
            disabled={submitting}
            onChange={setField('fullName')}
          />
        </div>

        <div className="col-12 col-sm-6 col-lg-4">
          <label htmlFor="user-email" className="form-label fw-semibold">
            Email
          </label>
          <input
            id="user-email"
            type="email"
            className="form-control"
            value={values.email}
            disabled={submitting}
            onChange={setField('email')}
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-4">
          <label htmlFor="user-role" className="form-label fw-semibold">
            Role
          </label>
          <select
            id="user-role"
            className="form-select"
            value={values.role}
            disabled={submitting}
            onChange={handleRoleChange}
          >
            <option value="student">Student</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        {isStudent && (
          <div className="col-12 col-sm-6 col-lg-4">
            <label htmlFor="user-id-number" className="form-label fw-semibold">
              ID No.
            </label>
            <input
              id="user-id-number"
              type="text"
              className="form-control"
              value={values.idNumber}
              disabled={submitting}
              onChange={setField('idNumber')}
            />
          </div>
        )}

        {isStudent && (
          <>
            <div className="col-12 col-sm-6 col-lg-4">
              <label htmlFor="user-program" className="form-label fw-semibold">
                Program
              </label>
              <input
                id="user-program"
                type="text"
                className="form-control"
                value={values.program}
                disabled={submitting}
                onChange={setField('program')}
              />
            </div>
            <div className="col-12 col-sm-6 col-lg-4">
              <label htmlFor="user-section" className="form-label fw-semibold">
                Section
              </label>
              <input
                id="user-section"
                type="text"
                className="form-control"
                value={values.section}
                disabled={submitting}
                onChange={setField('section')}
              />
            </div>
          </>
        )}
      </div>

      {displayError && (
        <div className="alert alert-danger py-2 small mb-0" role="alert">
          {displayError}
        </div>
      )}
    </ConfirmModal>
  )
}
