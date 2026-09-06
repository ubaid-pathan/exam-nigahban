import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { TOKEN_KEY } from '../api/client'
import { connectAdminAlertsSocket } from '../api/adminAlertsSocket'
import { listMonitoringEvents } from '../api/monitoring'
import NotificationBell from '../components/admin/NotificationBell'
import AdminSidebar from '../components/admin/AdminSidebar'
import { getAdminPageTitle } from '../components/admin/adminNavItems'
import { LogoutIcon, MenuIcon } from '../components/admin/icons'
import {
  addNotification,
  loadStoredNotifications,
  markAllRead,
  removeNotification,
  saveStoredNotifications,
  toNotification,
} from '../utils/adminNotifications'

// A burst of alerts (several rules firing across sessions at once) would
// otherwise trigger one backlog refetch per message. Coalescing them into
// a single request keeps the badge accurate without hammering the API.
const PENDING_REFETCH_DEBOUNCE_MS = 800

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [latestAlert, setLatestAlert] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  // Seeded from localStorage so an accidental refresh mid-exam does not
  // discard alerts the admin has not acted on yet.
  const [notifications, setNotifications] = useState(() =>
    loadStoredNotifications(window.localStorage),
  )
  const [notifOpen, setNotifOpen] = useState(false)
  // The authoritative review backlog, from the API rather than from this
  // socket's message count -- so it is correct after a reload and identical
  // for every signed-in admin. See NotificationBell for why this is kept
  // separate from the "new since last opened" count.
  const [pendingCount, setPendingCount] = useState(0)

  // AdminLayout stays mounted across every /admin/* page, so this is the
  // one place a single persistent connection makes sense -- opened only
  // for an authenticated admin with a real token, closed on cleanup
  // (covers unmount, logout, and React StrictMode's dev-mode double
  // mount/cleanup pass alike, since each effect run closes its own
  // `socket` instance rather than a shared one).
  //
  // Depends on the admin's id/role rather than the `user` object itself:
  // AuthContext's login() sets `user` to a fresh object and then its
  // token-driven effect fetches and sets it again with another fresh
  // object for the same admin, so depending on `user` by reference would
  // tear down and reopen the socket an extra time on every login even
  // though the authenticated identity never actually changed.
  //
  // This effect is deliberately untouched by the sidebar/header redesign
  // below -- it does not read `mobileNavOpen` or anything else UI-related,
  // so opening/closing the mobile drawer, navigating between admin pages,
  // or any other layout-only re-render can never affect it.
  useEffect(() => {
    if (!user || user.role !== 'admin') {
      return undefined
    }

    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      return undefined
    }

    const socket = connectAdminAlertsSocket({
      token,
      onOpen: () => setWsConnected(true),
      onMessage: (message) => {
        // latestAlert is kept exactly as before -- DashboardPage consumes
        // it from the outlet context to trigger its own refetch, and that
        // contract is unchanged by the notification queue below.
        setLatestAlert(message)
        const notification = toNotification(message)
        if (notification) {
          setNotifications((current) => addNotification(current, notification))
        }
      },
      onClose: () => setWsConnected(false),
      onError: () => {
        // Best-effort real-time channel: a connection error must never
        // break the admin UI. Automatic reconnection is handled by the
        // socket client's exponential backoff.
      },
    })

    return () => {
      socket?.close()
    }
  }, [user?.id, user?.role])

  // UI-only: closes the mobile drawer whenever the route changes (e.g. via
  // browser back/forward, not just a nav-link click) and on Escape.
  useEffect(() => {
    setMobileNavOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!mobileNavOpen) {
      return undefined
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setMobileNavOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [mobileNavOpen])

  // UI-only: the overlay behind the mobile drawer should block interaction
  // with the page underneath entirely, including scrolling it -- without
  // this, the page content keeps scrolling behind the (semi-transparent)
  // overlay while the drawer stays visually fixed in place, which breaks
  // the expected off-canvas-drawer behavior.
  useEffect(() => {
    if (!mobileNavOpen) {
      return undefined
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [mobileNavOpen])

  // Persist the queue on every change so a refresh restores it.
  useEffect(() => {
    saveStoredNotifications(window.localStorage, notifications)
  }, [notifications])

  // Refetch the authoritative PENDING_REVIEW backlog on mount and whenever
  // an alert arrives. Failures are swallowed: a stale badge is far better
  // than a broken admin shell, and the next alert retries anyway.
  useEffect(() => {
    if (!user || user.role !== 'admin') {
      return undefined
    }

    let cancelled = false
    const refetch = () => {
      listMonitoringEvents({ status: 'PENDING_REVIEW', page: 1, pageSize: 1 })
        .then((data) => {
          if (!cancelled) setPendingCount(data?.total ?? 0)
        })
        .catch(() => {})
    }

    const timer = setTimeout(refetch, latestAlert ? PENDING_REFETCH_DEBOUNCE_MS : 0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
    // Also refetched on navigation and whenever the panel is opened, so an
    // admin who has just reviewed a batch of events sees the backlog fall
    // rather than a stale number waiting on the next socket message.
  }, [user?.id, user?.role, latestAlert, location.pathname, notifOpen])

  // Opening the panel clears only the "new" marker. The badge tracks the
  // real review backlog and must not be cleared by merely looking at it.
  const handleToggleNotifications = useCallback(() => {
    setNotifOpen((wasOpen) => {
      if (!wasOpen) {
        setNotifications((current) => markAllRead(current))
      }
      return !wasOpen
    })
  }, [])

  const handleDismissNotification = useCallback((id) => {
    setNotifications((current) => removeNotification(current, id))
  }, [])

  const handleClearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // Close the panel on navigation, mirroring the mobile drawer above.
  useEffect(() => {
    setNotifOpen(false)
  }, [location.pathname])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const pageTitle = getAdminPageTitle(location.pathname)

  return (
    <div className="admin-shell">
      <AdminSidebar
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        onNavigate={() => setMobileNavOpen(false)}
      />

      <div className="admin-main">
        <header className="admin-header">
          <div className="d-flex align-items-center gap-3">
            <button
              type="button"
              className="admin-header__menu-btn d-md-none"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={mobileNavOpen}
            >
              <MenuIcon width={20} height={20} />
            </button>
            <span className="admin-header__title">{pageTitle}</span>
          </div>

          <div className="d-flex align-items-center gap-3">
            <NotificationBell
              notifications={notifications}
              pendingCount={pendingCount}
              connected={wsConnected}
              open={notifOpen}
              onToggle={handleToggleNotifications}
              onClose={() => setNotifOpen(false)}
              onDismiss={handleDismissNotification}
              onClearAll={handleClearNotifications}
            />
            {user && (
              <div className="admin-header__account d-flex align-items-center gap-2">
                <span className="admin-header__username text-truncate small">
                  {user.username}
                </span>
                <span className="badge text-bg-primary">Admin</span>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
                  onClick={handleLogout}
                >
                  <LogoutIcon width={14} height={14} />
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="admin-content">
          <Outlet context={{ latestAlert, wsConnected }} />
        </main>
      </div>
    </div>
  )
}
