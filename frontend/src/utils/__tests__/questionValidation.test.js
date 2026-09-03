import { describe, expect, it } from 'vitest'
import { EMPTY_QUESTION_VALUES, validateQuestionForm } from '../questionValidation'

const VALID_VALUES = {
  question_text: 'What is 2 + 2?',
  option_a: '3',
  option_b: '4',
  option_c: '5',
  option_d: '6',
  correct_answer: 'B',
}

describe('validateQuestionForm', () => {
  it('accepts a fully-filled valid form', () => {
    expect(validateQuestionForm(VALID_VALUES)).toBe('')
  })

  it('rejects empty question text', () => {
    expect(validateQuestionForm({ ...VALID_VALUES, question_text: '' })).toBe(
      'Question text is required.',
    )
  })

  it('rejects whitespace-only question text', () => {
    expect(validateQuestionForm({ ...VALID_VALUES, question_text: '   ' })).toBe(
      'Question text is required.',
    )
  })

  it.each(['option_a', 'option_b', 'option_c', 'option_d'])(
    'rejects a missing %s',
    (field) => {
      expect(validateQuestionForm({ ...VALID_VALUES, [field]: '' })).toBe(
        'All four options (A, B, C, D) are required.',
      )
    },
  )

  it('rejects a missing correct_answer', () => {
    expect(validateQuestionForm({ ...VALID_VALUES, correct_answer: '' })).toBe(
      'Select a valid correct answer (A, B, C, or D).',
    )
  })

  it('rejects a correct_answer outside A-D', () => {
    expect(validateQuestionForm({ ...VALID_VALUES, correct_answer: 'E' })).toBe(
      'Select a valid correct answer (A, B, C, or D).',
    )
  })

  it('the default empty form is rejected on question text', () => {
    expect(validateQuestionForm(EMPTY_QUESTION_VALUES)).toBe('Question text is required.')
  })
})
