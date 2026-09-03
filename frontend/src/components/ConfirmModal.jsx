export default function ConfirmModal({
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  confirmDisabled = false,
  size,
  // Optional and defaults to the exact previous behavior (primary) --
  // every existing caller is unaffected. Callers guarding a destructive
  // action (e.g. delete) can pass "danger" so the confirm button visually
  // matches the action it's confirming.
  confirmVariant = 'primary',
}) {
  const dialogClassName = size
    ? `modal-dialog modal-${size}`
    : 'modal-dialog'

  return (
    <div
      className="modal-backdrop-manual"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <div className={dialogClassName} style={{ margin: 0 }}>
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="confirm-modal-title">
              {title}
            </h5>
          </div>
          <div className="modal-body">{children}</div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              {cancelLabel}
            </button>
            <button
              type="button"
              className={`btn btn-${confirmVariant}`}
              onClick={onConfirm}
              disabled={confirmDisabled}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
