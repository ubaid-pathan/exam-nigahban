export const ANSWER_OPTIONS = ['A', 'B', 'C', 'D']

export const EMPTY_QUESTION_VALUES = {
  question_text: '',
  option_a: '',
  option_b: '',
  option_c: '',
  option_d: '',
  correct_answer: 'A',
}

export function validateQuestionForm(values) {
  if (!values.question_text?.trim()) {
    return 'Question text is required.'
  }
  if (
    !values.option_a?.trim() ||
    !values.option_b?.trim() ||
    !values.option_c?.trim() ||
    !values.option_d?.trim()
  ) {
    return 'All four options (A, B, C, D) are required.'
  }
  if (!ANSWER_OPTIONS.includes(values.correct_answer)) {
    return 'Select a valid correct answer (A, B, C, or D).'
  }
  return ''
}
