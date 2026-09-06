// Pure helpers backing the admin header's notification bell.
//
// Kept free of React/DOM so the queue semantics (normalization, dedupe,
// capping, read-marking, persistence) are unit-testable on their own,
// matching how the monitoring engine separates its pure logic from its
// hooks (see monitoring/temporalRuleEngine.js).
//
// Terminology follows CLAUDE.md's monitoring-language rules: every label
// below describes the detected activity and its review state only --
// never "cheating", "cheater", or "guilty" wording of any kind.

import { eventTypeLabel, eventStatusLabel, severityLabel } from './monitoringStatus'
import { actionTypeLabel, enforcementStatusLabel } from './enforcementStatus'

// Newest-first cap. A burst during a busy exam must not grow the stored
// list without bound; 20 comfortably covers a session's worth of review
// while keeping the localStorage payload small.
export const MAX_NOTIFICATIONS = 20

export const NOTIFICATIONS_STORAGE_KEY = 'exam_nigahban_admin_notifications'

/**
 * Converts one raw admin-alert WebSocket message (already validated by
 * api/adminAlertsSocket.js) into the flat shape the bell renders.
 *
 * Returns null for anything unrecognized so a future backend message type
 * is dropped here rather than rendering as a blank row.
 *
 * `id` is derived from the backend's own row id, which makes it a natural
 * dedupe key: a reconnect that replays an alert cannot produce a second
 * entry for the same event.
 */
export function toNotification(message, receivedAt = Date.now()) {
  if (!message || typeof message !== 'object') return null

  if (message.type === 'monitoring_event') {
    return {
      id: `event:${message.event_id}`,
      kind: 'monitoring_event',
      severity: message.severity ?? null,
      title: eventTypeLabel(message.event_type),
      detail: `${severityLabel(message.severity)} severity · ${eventStatusLabel(message.status)}`,
      context: `Session ${message.session_id}`,
      to: '/admin/monitoring',
      receivedAt,
      read: false,
    }
  }

  if (message.type === 'enforcement_action') {
    return {
      id: `enforcement:${message.action_id}`,
      kind: 'enforcement_action',
      // Enforcement actions carry no severity of their own; the bell
      // styles them by action type instead (see NotificationBell).
      severity: null,
      title: actionTypeLabel(message.action_type),
      detail: `Enforcement · ${enforcementStatusLabel(message.status)}`,
      context: `Session ${message.session_id}`,
      to: '/admin/enforcement',
      receivedAt,
      read: false,
    }
  }

  return null
}

/**
 * Returns a new list with `notification` prepended, deduped by id and
 * capped at `max`. Never mutates the input.
 *
 * A repeat of an existing id replaces the older entry and moves it back to
 * the top, rather than being ignored: the newer message carries the newer
 * status (e.g. an event that has since been reviewed).
 */
export function addNotification(list, notification, max = MAX_NOTIFICATIONS) {
  if (!notification) return list
  const withoutDuplicate = (list || []).filter((item) => item.id !== notification.id)
  return [notification, ...withoutDuplicate].slice(0, max)
}

/** Returns a new list with every entry marked read. Never mutates. */
export function markAllRead(list) {
  return (list || []).map((item) => (item.read ? item : { ...item, read: true }))
}

/** Returns a new list without the entry matching `id`. Never mutates. */
export function removeNotification(list, id) {
  return (list || []).filter((item) => item.id !== id)
}

/**
 * How many entries arrived since the panel was last opened.
 *
 * Deliberately distinct from the bell's badge number, which shows the
 * authoritative PENDING_REVIEW backlog from the API: reading an alert does
 * not review the event, so only this count clears on open.
 */
export function unreadCount(list) {
  return (list || []).reduce((total, item) => total + (item.read ? 0 : 1), 0)
}

/**
 * Reads the persisted list, tolerating every failure mode: unavailable
 * storage (private windows, blocked site data), absent key, invalid JSON,
 * or a stored value that is not a list of well-formed entries.
 */
export function loadStoredNotifications(storage) {
  try {
    const raw = storage?.getItem(NOTIFICATIONS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter(
        (item) =>
          item &&
          typeof item === 'object' &&
          typeof item.id === 'string' &&
          typeof item.title === 'string',
      )
      .slice(0, MAX_NOTIFICATIONS)
  } catch {
    return []
  }
}

/** Persists the list, silently tolerating unavailable/full storage. */
export function saveStoredNotifications(storage, list) {
  try {
    storage?.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(list || []))
  } catch {
    // Persistence is a convenience, never a requirement -- the in-memory
    // list keeps working when storage is blocked or full.
  }
}

/**
 * Clears the persisted list. Called on logout so one admin's alerts are
 * never shown to whoever signs in next on the same browser.
 */
export function clearStoredNotifications(storage) {
  try {
    storage?.removeItem(NOTIFICATIONS_STORAGE_KEY)
  } catch {
    // Nothing to do -- see saveStoredNotifications.
  }
}

/**
 * Compact age label for a notification row ("just now", "4m", "2h", "3d").
 * Pure function of the two timestamps so it can be tested without clocks.
 */
export function formatAge(receivedAt, now = Date.now()) {
  const seconds = Math.max(0, Math.floor((now - receivedAt) / 1000))
  if (seconds < 45) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${Math.max(1, minutes)}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}
