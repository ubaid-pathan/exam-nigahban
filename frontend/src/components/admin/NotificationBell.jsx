import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { BellIcon, CloseIcon } from './icons'
import { severityBadgeClass, severityLabel } from '../../utils/monitoringStatus'
import { formatAge, unreadCount } from '../../utils/adminNotifications'

// The admin header's live monitoring/enforcement notification control.
//
// Presentational + interaction only: AdminLayout owns the WebSocket, the
// notification queue and its persistence, and passes everything in. This
// component never fetches and never touches storage.
//
// Two counts are shown deliberately, and they mean different things:
//
//   * the BADGE is the authoritative PENDING_REVIEW backlog from the API.
//     Reading an alert does not review an event, so opening this panel
//     never changes it -- only an actual admin decision does.
//   * the NEW marker is how many alerts arrived since the panel was last
//     opened. That is browser state, and it does clear on open.
//
// Collapsing the two would make the header claim work was done when it
// wasn't, which on an invigilation dashboard is the wrong lie to tell.
export default function NotificationBell({
  notifications = [],
  pendingCount = 0,
  connected = false,
  open = false,
  onToggle,
  onClose,
  onDismiss,
  onClearAll,
}) {
  const navigate = useNavigate()
  const containerRef = useRef(null)
  const buttonRef = useRef(null)

  const newCount = unreadCount(notifications)

  // Close on outside click and on Escape. Escape also returns focus to the
  // bell, so keyboard users are not dropped at the top of the document.
  useEffect(() => {
    if (!open) return undefined

    const handlePointerDown = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        onClose?.()
      }
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose?.()
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, onClose])

  const handleOpenNotification = (notification) => {
    onDismiss?.(notification.id)
    onClose?.()
    navigate(notification.to)
  }

  const badgeLabel = pendingCount > 99 ? '99+' : String(pendingCount)

  return (
    <div className="notif" ref={containerRef}>
      <button
        type="button"
        ref={buttonRef}
        className="notif__bell"
        onClick={onToggle}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={
          `Monitoring alerts: ${pendingCount} pending review` +
          (newCount > 0 ? `, ${newCount} new` : '') +
          (connected ? '' : ' (live updates disconnected)')
        }
      >
        <BellIcon width={19} height={19} aria-hidden="true" />

        {pendingCount > 0 && (
          <span className="notif__badge" aria-hidden="true">
            {badgeLabel}
          </span>
        )}

        {/* Silence on a proctoring dashboard is ambiguous -- it can mean
            "no violations" or "the socket died". This dot keeps those two
            visually distinct. */}
        <span
          className={`notif__wire ${connected ? 'notif__wire--live' : 'notif__wire--down'}`}
          aria-hidden="true"
        />
      </button>

      {/* Announced politely rather than assertively: a monitoring alert is
          informational, and interrupting an admin mid-review would be
          worse than a slightly delayed announcement. */}
      <span className="visually-hidden" role="status" aria-live="polite">
        {newCount > 0 ? `${newCount} new monitoring alert${newCount === 1 ? '' : 's'}` : ''}
      </span>

      {open && (
        <div className="notif__panel" role="dialog" aria-label="Monitoring alerts">
          <div className="notif__panel-head">
            <div>
              <p className="notif__panel-title">Alerts</p>
              <p className="notif__panel-sub">
                {pendingCount > 0
                  ? `${pendingCount} pending review`
                  : 'Nothing pending review'}
                {!connected && ' · live updates offline'}
              </p>
            </div>
            {notifications.length > 0 && (
              <button type="button" className="notif__clear" onClick={onClearAll}>
                Clear all
              </button>
            )}
          </div>

          <div className="notif__list">
            {notifications.length === 0 ? (
              <div className="notif__empty">
                <p className="mb-1 fw-semibold">No recent alerts</p>
                <p className="mb-0 small">
                  Monitoring alerts appear here as soon as they are detected.
                </p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`notif__item${item.read ? '' : ' notif__item--new'}`}
                >
                  <button
                    type="button"
                    className="notif__item-main"
                    onClick={() => handleOpenNotification(item)}
                  >
                    <span
                      className={`notif__stripe notif__stripe--${item.severity || item.kind}`}
                      aria-hidden="true"
                    />
                    <span className="notif__item-body">
                      <span className="notif__item-top">
                        <span className="notif__item-title">{item.title}</span>
                        {item.severity && (
                          <span className={`badge ${severityBadgeClass(item.severity)}`}>
                            {severityLabel(item.severity)}
                          </span>
                        )}
                      </span>
                      <span className="notif__item-detail">{item.detail}</span>
                      <span className="notif__item-meta">
                        {item.context} · {formatAge(item.receivedAt)}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    className="notif__dismiss"
                    onClick={() => onDismiss?.(item.id)}
                    aria-label={`Dismiss alert: ${item.title}`}
                  >
                    <CloseIcon width={13} height={13} aria-hidden="true" />
                  </button>
                </div>
              ))
            )}
          </div>

          <button
            type="button"
            className="notif__footer"
            onClick={() => {
              onClose?.()
              navigate('/admin/monitoring')
            }}
          >
            View all monitoring events
          </button>
        </div>
      )}
    </div>
  )
}
