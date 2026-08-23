export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="alert alert-danger" role="alert">
      <h2 className="h6 mb-1">{title}</h2>
      {message && <p className="mb-2">{message}</p>}
      {onRetry && (
        <button type="button" className="btn btn-sm btn-outline-danger" onClick={onRetry}>
          Try Again
        </button>
      )}
    </div>
  )
}
