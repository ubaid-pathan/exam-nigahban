export default function QuestionPalette({ questions, currentIndex, answeredIds, onSelect }) {
  return (
    <div className="question-palette" role="group" aria-label="Question navigation">
      {questions.map((question, index) => {
        const isAnswered = answeredIds.has(question.id)
        const isCurrent = index === currentIndex
        const variant = isCurrent
          ? 'btn-primary'
          : isAnswered
            ? 'btn-success'
            : 'btn-outline-secondary'
        return (
          <button
            key={question.id}
            type="button"
            className={`btn btn-sm question-palette__btn ${variant}`}
            onClick={() => onSelect(index)}
            aria-current={isCurrent ? 'true' : undefined}
            aria-label={`Question ${index + 1}, ${isAnswered ? 'answered' : 'unanswered'}`}
          >
            {index + 1}
          </button>
        )
      })}
    </div>
  )
}
