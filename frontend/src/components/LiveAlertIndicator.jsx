import { Link } from 'react-router-dom'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  severityBadgeClass,
  severityLabel,
} from '../utils/monitoringStatus'

// Small, presentational live-alert indicator for the admin navbar. It owns
// no WebSocket state and does not fetch anything -- AdminLayout supplies
// the latest broadcast monitoring_event (or null/undefined, before the
// first one arrives) as a prop. Renders nothing until then.
export default function LiveAlertIndicator({ latestAlert }) {
  if (!latestAlert) {
    return null
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
