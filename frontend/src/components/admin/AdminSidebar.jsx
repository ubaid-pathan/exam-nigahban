import { NavLink } from 'react-router-dom'
import { ADMIN_NAV_ITEMS } from './adminNavItems'
import { CloseIcon } from './icons'

// Purely presentational: branding and the nav links. Owns no auth or
// WebSocket state of its own. `open`/`onNavigate` only control the mobile
// off-canvas drawer's visibility/close behavior; on desktop (>=768px, via
// CSS) the sidebar is always visible regardless of `open`. The account
// area (username/Admin badge/Logout) lives only in the header now
// (AdminLayout.jsx) -- this avoided a duplicate logout control.
export default function AdminSidebar({ open, onClose, onNavigate }) {
  const navLinkClass = ({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`

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
          {ADMIN_NAV_ITEMS.map(({ to, end, label, Icon }) => (
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
