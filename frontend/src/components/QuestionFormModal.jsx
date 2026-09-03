import { useState } from 'react'
import ConfirmModal from './ConfirmModal'
import { ANSWER_OPTIONS, EMPTY_QUESTION_VALUES, validateQuestionForm } from '../utils/questionValidation'

const OPTION_LETTERS = ['a', 'b', 'c', 'd']

export default function QuestionFormModal({
  mode,
  initialValues,
  submitting,
  error,
  onSubmit,
  onCancel,
}) {
  const [values, setValues] = useState(initialValues || EMPTY_QUESTION_VALUES)
  const [validationError, setValidationError] = useState('')

  const handleFieldChange = (field) => (e) => {
    setValues((current) => ({ ...current, [field]: e.target.value }))
  }

  const handleConfirm = () => {
    const message = validateQuestionForm(values)
    if (message) {
      setValidationError(message)
      return
    }
    setValidationError('')
    onSubmit(values)
  }

  const displayError = validationError || error

  return (
    <ConfirmModal
      title={mode === 'create' ? 'Add Question' : 'Edit Question'}
      confirmLabel={
        submitting ? 'Saving...' : mode === 'create' ? 'Add Question' : 'Save Changes'
      }
      confirmDisabled={submitting}
      onConfirm={handleConfirm}
      onCancel={onCancel}
      size="lg"
    >
      <div className="mb-3">
        <label htmlFor="question-text" className="form-label fw-semibold">
          Question Text
        </label>
        <textarea
          id="question-text"
          className="form-control"
          rows={3}
          value={values.question_text}
          disabled={submitting}
          onChange={handleFieldChange('question_text')}
        />
      </div>

      <div className="row g-3 mb-3">
        {OPTION_LETTERS.map((letter) => (
          <div className="col-md-6" key={letter}>
            <label htmlFor={`question-option-${letter}`} className="form-label fw-semibold">
              Option {letter.toUpperCase()}
            </label>
            <input
              id={`question-option-${letter}`}
              type="text"
              className="form-control"
              maxLength={500}
              value={values[`option_${letter}`]}
              disabled={submitting}
              onChange={handleFieldChange(`option_${letter}`)}
            />
          </div>
        ))}
      </div>

      <div className="mb-3">
        <label htmlFor="question-correct-answer" className="form-label fw-semibold">
          Correct Answer
        </label>
        <select
          id="question-correct-answer"
          className="form-select"
          value={values.correct_answer}
          disabled={submitting}
          onChange={handleFieldChange('correct_answer')}
        >
          {ANSWER_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {displayError && (
        <div className="alert alert-danger py-2 small mb-0" role="alert">
          {displayError}
        </div>
      )}
    </ConfirmModal>
  )
}
