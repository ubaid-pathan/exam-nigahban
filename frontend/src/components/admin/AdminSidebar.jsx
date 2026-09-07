import { NavLink } from 'react-router-dom'
import { ADMIN_NAV_ITEMS } from './adminNavItems'
import { useAuth } from '../../context/AuthContext'
import { CloseIcon } from './icons'

// Purely presentational: branding and the nav links. Owns no auth or
// WebSocket state of its own. `open`/`onNavigate` only control the mobile
// off-canvas drawer's visibility/close behavior; on desktop (>=768px, via
// CSS) the sidebar is always visible regardless of `open`. The account
// area (username/Admin badge/Logout) lives only in the header now
// (AdminLayout.jsx) -- this avoided a duplicate logout control.
export default function AdminSidebar({ open, onClose, onNavigate }) {
  const { user } = useAuth()
  const navLinkClass = ({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`

  // A link the account cannot use is hidden rather than shown and
  // refused. The route and the API enforce this independently -- this
  // only avoids leading an ordinary administrator to a page that turns
  // them away.
  const navItems = ADMIN_NAV_ITEMS.filter(
    (item) => !item.systemAdminOnly || user?.is_system_admin,
  )

  return (
    <>
      {open && (
        <div className="admin-sidebar__overlay" onClick={onClose} aria-hidden="true" />
      )}
      <aside className={`admin-sidebar${open ? ' admin-sidebar--open' : ''}`}>
        <div className="admin-sidebar__brand">
          <div className="d-flex align-items-start justify-content-between">
            <div>
              <div className="admin-sidebar__brand-name">Exam Nigahban</div>
              <div className="admin-sidebar__brand-label">Admin Panel</div>
            </div>
            <button
              type="button"
              className="admin-sidebar__close-btn d-md-none"
              onClick={onClose}
              aria-label="Close navigation menu"
            >
              <CloseIcon width={18} height={18} />
            </button>
          </div>
        </div>

        <nav className="admin-sidebar__nav" aria-label="Admin navigation">
          {navItems.map(({ to, end, label, Icon }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClass} onClick={onNavigate}>
              <Icon width={18} height={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
