// Small hand-authored icon set for the admin sidebar/header -- the project
// has no icon package installed (only plain `bootstrap`, not
// `bootstrap-icons`), and CLAUDE.md asks to avoid unnecessary dependencies,
// so these are inline SVGs rather than a new library. All share the same
// 24x24 viewBox, stroke weight, and currentColor fill so they read as one
// consistent set at any size the caller applies via className/style.

const commonProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: 'false',
}

export function DashboardIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.5" />
      <rect x="13" y="3.5" width="7.5" height="4.5" rx="1.5" />
      <rect x="13" y="10.5" width="7.5" height="10" rx="1.5" />
      <rect x="3.5" y="13.5" width="7.5" height="7" rx="1.5" />
    </svg>
  )
}

export function MonitoringIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M3 12h3.5l2-6 4 12 2-9 1.5 3H21" />
    </svg>
  )
}

export function ExamsIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="5" y="4" width="14" height="17" rx="1.5" />
      <path d="M9 3.5h6a1 1 0 0 1 1 1V6H8V4.5a1 1 0 0 1 1-1Z" />
      <path d="M8.5 11h7M8.5 14.5h7M8.5 18h4.5" />
    </svg>
  )
}

export function StudentsIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <circle cx="17.5" cy="9.5" r="2.3" />
      <path d="M15 20a4.2 4.2 0 0 1 6.5-3.5" />
    </svg>
  )
}

export function UsersIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <circle cx="17.5" cy="9.5" r="2.3" />
      <path d="M15 20a4.2 4.2 0 0 1 6.5-3.5" />
    </svg>
  )
}

export function AdministratorsIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M12 3.5 5 6.2v5.3c0 4.6 2.9 7.9 7 8.9 4.1-1 7-4.3 7-8.9V6.2L12 3.5Z" />
      <circle cx="12" cy="10.5" r="2.3" />
      <path d="M8.7 16c.6-1.6 1.9-2.5 3.3-2.5s2.7.9 3.3 2.5" />
    </svg>
  )
}

export function AuditIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l2.8 2" />
      <path d="M8 3.5h8" />
    </svg>
  )
}

export function LogoutIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M9 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h3" />
      <path d="M14.5 16 19 12l-4.5-4" />
      <path d="M19 12H9" />
    </svg>
  )
}

export function MenuIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M3.5 6.5h17M3.5 12h17M3.5 17.5h17" />
    </svg>
  )
}

export function CloseIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M5 5l14 14M19 5 5 19" />
    </svg>
  )
}

export function EditIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M4 16.5V20h3.5L18.8 8.7a1.5 1.5 0 0 0 0-2.1l-1.4-1.4a1.5 1.5 0 0 0-2.1 0L4 16.5Z" />
      <path d="M13.5 6.5l3 3" />
    </svg>
  )
}

export function QuestionsIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="5.5" cy="7" r="1" />
      <circle cx="5.5" cy="12" r="1" />
      <circle cx="5.5" cy="17" r="1" />
      <path d="M9 7h11M9 12h11M9 17h11" />
    </svg>
  )
}

export function PauseIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="6" y="4.5" width="4" height="15" rx="1" />
      <rect x="14" y="4.5" width="4" height="15" rx="1" />
    </svg>
  )
}

export function PlayIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M7 4.5v15l13-7.5-13-7.5Z" />
    </svg>
  )
}

export function TrashIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M4.5 7h15" />
      <path d="M9.5 7V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v2" />
      <path d="M6.5 7l.8 12.5A1.5 1.5 0 0 0 8.8 21h6.4a1.5 1.5 0 0 0 1.5-1.5L17.5 7" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  )
}

export function PersonIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </svg>
  )
}

export function LockIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="5" y="11" width="14" height="9.5" rx="1.5" />
      <path d="M8 11V7.5a4 4 0 0 1 8 0V11" />
    </svg>
  )
}

// Same shield silhouette as AdministratorsIcon (kept consistent rather than
// inventing a new shield shape) with an exclamation glyph instead of a
// person, so it reads as "restricted/alert" rather than "administrator".
export function ShieldAlertIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M12 3.5 5 6.2v5.3c0 4.6 2.9 7.9 7 8.9 4.1-1 7-4.3 7-8.9V6.2L12 3.5Z" />
      <path d="M12 8.5v4" />
      <circle cx="12" cy="15.5" r="0.75" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function CheckCircleIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12.3l2.4 2.4 4.6-5.4" />
    </svg>
  )
}

export function FileIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M6.5 3.5h7l4 4v12.5a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M13.5 3.5V8h4" />
      <path d="M9 13h6M9 16.5h6" />
    </svg>
  )
}

// Outline bell for the header's notification control. Matches the stroke
// weight and 24x24 viewBox of every other icon in this file (see
// commonProps) rather than introducing a second visual style.
export function BellIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M18 8.5a6 6 0 1 0-12 0c0 4.2-1.4 5.6-2 6.3-.2.3 0 .7.4.7h15.2c.4 0 .6-.4.4-.7-.6-.7-2-2.1-2-6.3Z" />
      <path d="M10.2 19a2 2 0 0 0 3.6 0" />
    </svg>
  )
}
