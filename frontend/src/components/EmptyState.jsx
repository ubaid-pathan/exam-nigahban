export default function EmptyState({ title = 'Nothing here yet', message }) {
  return (
    <div className="text-center text-muted py-5">
      <h2 className="h6">{title}</h2>
      {message && <p className="mb-0">{message}</p>}
    </div>
  )
}
