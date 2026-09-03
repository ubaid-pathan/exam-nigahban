// Admin-facing timestamp formatting in Pakistan Standard Time (Asia/Karachi,
// UTC+05:00). Stored/API timestamps remain UTC -- only the presentation
// layer converts, via the native Intl API (no new dependency).
const PKT_FORMATTER = new Intl.DateTimeFormat('en-PK', {
  timeZone: 'Asia/Karachi',
  dateStyle: 'medium',
  timeStyle: 'short',
})

// The backend serializes datetimes as naive ISO strings with no timezone
// indicator (e.g. "2026-08-30T21:07:04.024031"), since they're generated
// with datetime.utcnow() (see app/models/*.py). Per the ECMAScript spec, a
// date-TIME string with no offset is parsed as the *browser's local* time,
// not UTC -- even though the value is actually UTC. Left alone, that would
// misinterpret the source instant before ever converting to Asia/Karachi,
// silently corrupting the result unless the viewer's own timezone happens
// to already be UTC. Appending "Z" (only when no offset is already present)
// corrects the source interpretation to UTC, matching how it's actually
// generated -- this is the proper-conversion step, not a manual +5 hours.
function asUtcDate(value) {
  if (typeof value === 'string' && !/[Zz]|[+-]\d{2}:\d{2}$/.test(value)) {
    return new Date(`${value}Z`)
  }
  return new Date(value)
}

// Formats an API timestamp for admin-facing display in PKT. Returns '' for
// a missing/empty value rather than an "Invalid Date" string.
export function formatDateTimePKT(value) {
  if (!value) {
    return ''
  }
  return PKT_FORMATTER.format(asUtcDate(value))
}
