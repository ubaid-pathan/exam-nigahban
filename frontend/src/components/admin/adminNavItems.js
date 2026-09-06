import {
  AuditIcon,
  DashboardIcon,
  ExamsIcon,
  FileIcon,
  MonitoringIcon,
  ShieldAlertIcon,
  UsersIcon,
} from './icons'

// Single source of truth for the admin sidebar's navigation, reused by
// AdminSidebar (the link list) and AdminLayout (the header's current-page
// title lookup) so the routes/labels/icons are never duplicated across the
// two.
//
// Students and Administrators were consolidated into one Users entry
// (/admin/users, UsersPage.jsx) -- the old /admin/students and
// /admin/administrators routes/pages still exist and still work (App.jsx
// keeps them, unlinked) so nothing that already points at them breaks;
// they're simply no longer part of the primary navigation.
export const ADMIN_NAV_ITEMS = [
  { to: '/admin', end: true, label: 'Dashboard', Icon: DashboardIcon },
  { to: '/admin/monitoring', label: 'Monitoring Events', Icon: MonitoringIcon },
  { to: '/admin/enforcement', label: 'Enforcement', Icon: ShieldAlertIcon },
  { to: '/admin/exams', label: 'Exams', Icon: ExamsIcon },
  { to: '/admin/users', label: 'Users', Icon: UsersIcon },
  { to: '/admin/reports', label: 'Reports', Icon: FileIcon },
  { to: '/admin/audit', label: 'Audit History', Icon: AuditIcon },
]

// Resolves the header's current-page title from the route pathname. Exact
// matches win first (so "/admin" only labels itself, not every admin
// route); otherwise the longest matching prefix wins, so a nested route
// like /admin/exams/:examId/questions still labels itself "Exams" instead
// of falling through to a generic default.
export function getAdminPageTitle(pathname) {
  const exact = ADMIN_NAV_ITEMS.find((item) => item.to === pathname)
  if (exact) {
    return exact.label
  }

  const prefixMatch = ADMIN_NAV_ITEMS.filter(
    (item) => item.to !== '/admin' && pathname.startsWith(`${item.to}/`)
  ).sort((a, b) => b.to.length - a.to.length)[0]

  return prefixMatch?.label ?? 'Admin Panel'
}
