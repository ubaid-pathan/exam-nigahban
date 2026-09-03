export const USER_ROLES = ['student', 'admin']

export const EMPTY_USER_FORM = {
  fullName: '',
  idNumber: '',
  email: '',
  role: 'student',
  program: '',
  section: '',
  username: '',
  password: '',
}

// Deliberately simple format check, matching the backend's own validator
// (app/schemas/user.py) rather than adding a validation library -- this
// project has no existing dependency for it.
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export function isValidEmail(value) {
  return EMAIL_PATTERN.test(value)
}

// Mirrors validateQuestionForm's contract (utils/questionValidation.js):
// returns a single human-readable error message, or '' when the form is
// valid. Program/Section are only required when role is 'student' -- an
// admin account has no such fields to fill in.
export function validateUserForm(values) {
  if (!values.fullName?.trim()) {
    return 'Full name is required.'
  }
  if (!values.username?.trim()) {
    return 'Username is required.'
  }
  if (!values.password || values.password.length < 8) {
    return 'Password must be at least 8 characters.'
  }
  if (!values.email?.trim()) {
    return 'Email is required.'
  }
  if (!isValidEmail(values.email.trim())) {
    return 'Enter a valid email address.'
  }
  if (!USER_ROLES.includes(values.role)) {
    return 'Select a valid role.'
  }

  if (values.role === 'student') {
    if (!values.idNumber?.trim()) {
      return 'ID No. is required.'
    }
    if (!values.program?.trim()) {
      return 'Program is required.'
    }
    if (!values.section?.trim()) {
      return 'Section is required.'
    }
  }

  return ''
}
