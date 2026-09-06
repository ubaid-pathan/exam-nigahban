import { Link } from 'react-router-dom'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  severityBadgeClass,
  severityLabel,
} from '../utils/monitoringStatus'
import {
  actionTypeBadgeClass,
  actionTypeLabel,
  enforcementStatusBadgeClass,
  enforcementStatusLabel,
} from '../utils/enforcementStatus'

// Small, presentational live-alert indicator for the admin navbar. It owns
// no WebSocket state and does not fetch anything -- AdminLayout supplies
// the latest broadcast alert (or null/undefined, before the first one
// arrives) as a prop. Renders nothing until then.
export default function LiveAlertIndicator({ latestAlert }) {
  if (!latestAlert) {
    return null
  }

  // Enforcement broadcasts carry action_type/status instead of a
  // monitoring event's severity/event_type, and deep-link to the
  // enforcement log rather than the monitoring feed.
  if (latestAlert.type === 'enforcement_action') {
    return (
      <Link
        to="/admin/enforcement"
        role="status"
        className="d-flex align-items-center gap-1 text-decoration-none"
      >
        <span className={`badge ${actionTypeBadgeClass(latestAlert.action_type)}`}>
          {actionTypeLabel(latestAlert.action_type)}
        </span>
        <span className="text-light small">Enforcement</span>
        <span className={`badge ${enforcementStatusBadgeClass(latestAlert.status)}`}>
          {enforcementStatusLabel(latestAlert.status)}
        </span>
      </Link>
    )
  }

  return (
    <Link
      to="/admin/monitoring"
      role="status"
      className="d-flex align-items-center gap-1 text-decoration-none"
    >
      <span className={`badge ${severityBadgeClass(latestAlert.severity)}`}>
        {severityLabel(latestAlert.severity)}
      </span>
      <span className="text-light small">{latestAlert.event_type}</span>
      <span className={`badge ${eventStatusBadgeClass(latestAlert.status)}`}>
        {eventStatusLabel(latestAlert.status)}
      </span>
    </Link>
  )
}
