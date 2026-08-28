export default function ConfirmModal({
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  confirmDisabled = false,
  size,
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
              className="btn btn-primary"
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
