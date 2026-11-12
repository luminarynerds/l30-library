/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useMemo, useCallback, useEffect, useRef, useId, memo, Component, type ReactNode, type ErrorInfo } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { BookOpen, Calendar, User, Briefcase, MessageCircle, Compass, CreditCard, Sparkles, Search, MapPin, HelpCircle, Settings } from 'lucide-react'
import { useBranding } from '../contexts/BrandingContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { useAuth } from '../contexts/AuthContext'
import { useEssentialsMode } from '../contexts/EssentialsModeContext'
import { useTranslation } from '../i18n/I18nContext'
import { useAccessibility } from '../features/accessibility/hooks/useAccessibility'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { useStickyHeader } from '../hooks/useStickyHeader'
import { useFocusTrap } from '../hooks/useFocusTrap'
import AuthModals from './AuthModals'
import MobileMoreMenu from './MobileMoreMenu'
import NavDropdown from './NavDropdown'
import { getNavConfig } from './header/navConfig'
import MoreOverflow from './header/MoreOverflow'
import AccountDropdown from './AccountDropdown'
import Breadcrumbs from './Breadcrumbs'
import LanguageSwitcher from './LanguageSwitcher'
import NotificationsDropdown from './NotificationsDropdown'
import Footer from './Footer'
import HeaderSearch from './HeaderSearch'
import LibraryStatusBanner from './LibraryStatusBanner'
import SystemStatusBanner from './SystemStatusBanner'
import NavigationProgress from './NavigationProgress'
import { PanicAlertSystem } from './PanicAlertSystem'
import { QuickAccessibilityWidget } from '../features/accessibility/components/QuickAccessibilityWidget'
import { QuietModeToggle } from '@/components/neurodivergent/QuietModeToggle'
import HeaderSOSButton from './HeaderSOSButton'
import CommandPalette from './CommandPalette/CommandPalette'
import { clsx } from '../utils/helpers'
import { isActive as isActiveShared } from '../utils/nav'

// Error boundary for panic alert system — prevents crashes from breaking the page
class PanicErrorBoundary extends Component<{children: ReactNode}, {hasError: boolean}> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch(error: Error, _info: ErrorInfo) {
    Sentry.captureException(error)
  }
  render() {
    if (this.state.hasError) return null
    return this.props.children
  }
}

// Memoized navigation link component
const NavLink = memo(function NavLink({
  to,
  isActive,
  icon: Icon,
  children,
  shortcut,
}: {
  to: string
  isActive: boolean
  icon: React.ElementType
  children: React.ReactNode
  /** Optional W3C aria-keyshortcuts value (announce-only; bindings live in Layout). */
  shortcut?: string
}) {
  return (
    <Link
      to={to}
      className={clsx(
        'flex items-center shrink-0 gap-1.5 px-2 xl:px-2.5 py-2 rounded-xl text-sm font-medium motion-safe:transition-all whitespace-normal',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
        isActive
          ? 'nav-active bg-lsc-rose/10 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light font-bold'
          : 'text-earth-700 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/15 hover:text-earth-950 dark:hover:text-lsc-cream'
      )}
      aria-current={isActive ? 'page' : undefined}
      aria-keyshortcuts={shortcut || undefined}
    >
      <Icon aria-hidden="true" className="w-5 h-5 hidden 2xl:block" />
      {children}
    </Link>
  )
})

export function ShortcutHelpDialog({ onClose }: { onClose: () => void }): React.ReactElement {
  const headingId = useId()
  const focusTrapRef = useFocusTrap<HTMLDivElement>({
    isActive: true,
    initialFocus: true,
    restoreFocus: true,
    onEscape: onClose,
  })
  return (
    <div
      className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center motion-safe:animate-fade-in"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        ref={focusTrapRef}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 max-w-md w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={headingId} className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Keyboard Shortcuts</h2>
        <dl className="space-y-2 text-sm">
          {[
            ['⌘K / Ctrl+K', 'Open command palette'],
            ['g c', 'Go to Circulation'],
            ['g h', 'Go to Holds Shelf'],
            ['g p', 'Go to Patrons'],
            ['g r', 'Go to Book Drop'],
            ['?', 'Toggle this help'],
            ['Esc', 'Close dialogs'],
          ].map(([keys, desc]) => (
            <div key={keys} className="flex items-center justify-between gap-3 py-1">
              <span className="text-lsc-dark/80 dark:text-lsc-cream/80">{desc}</span>
              <kbd className="px-2 py-1 text-xs font-mono bg-lsc-cream dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream">{keys}</kbd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
          Shortcuts skip when focus is in an input field.
        </p>
        <button
          onClick={onClose}
          className="mt-4 w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  )
}

interface LayoutProps {
  /**
   * When true, renders the staff shell: full-bleed main, no site footer,
   * no breadcrumbs, no mobile bottom nav, and `h-screen overflow-hidden` root
   * so the StaffLayout sidebar can scroll independently. Defaults to false
   * (patron site chrome). Set at the route level in AppRoutes.tsx — pages
   * that use <StaffLayout> must be mounted under a Layout with staffShell.
   */
  staffShell?: boolean
}

export default function Layout({ staffShell = false }: LayoutProps = {}): React.ReactElement {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()
  const { t } = useTranslation()
  const branding = useBranding()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { isSticky, isVisible } = useStickyHeader(80)
  const { isEssentialsMode, toggleMode: toggleEssentialsMode, isLoading: isEssentialsLoading } = useEssentialsMode()
  const { settings: accessibilitySettings, updateSetting: updateAccessibilitySetting } = useAccessibility()
  const quietMode = useUnifiedAccessibility().settings.quietMode || false
  const [widgetOpen, setWidgetOpen] = useState(false)
  const [fabSeen, setFabSeen] = useState(() => {
    try { return !!localStorage.getItem('l30.a11yFabSeen') } catch { return true }
  })
  const [footerInView, setFooterInView] = useState(false)
  const footerObserverRef = useRef<HTMLElement | null>(null)
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false)
  const isStaffUser = Boolean(user && (['staff', 'admin', 'super_admin', 'director', 'legal', 'bookmobile', 'homebond'].includes(user.role) || user.is_board_member))
  // On staff/admin routes the left rail is the real nav, so suppress the
  // public marketing nav (catalog/events/dropdowns) from the top header.
  const isStaffRoute = location.pathname.startsWith('/staff') || location.pathname.startsWith('/admin')

  // Track whether we're at lg+ width — skip-link targets differ between
  // desktop (`#main-navigation`) and mobile (`#mobile-bottom-nav`), and the
  // desktop nav is `hidden lg:flex` so the link otherwise lands on a hidden
  // element below the breakpoint.
  const [isLargeScreen, setIsLargeScreen] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches
  )
  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = (e: MediaQueryListEvent) => setIsLargeScreen(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  // Global staff keyboard shortcuts (Cmd/Ctrl+K, g-prefixed nav, ? help)
  // Skip when focus is in an input/textarea/contenteditable
  const gPrefixRef = useRef<number | null>(null)
  useEffect(() => {
    if (!isStaffUser) return
    const isEditable = (el: EventTarget | null): boolean => {
      if (!(el instanceof HTMLElement)) return false
      const tag = el.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
      if (el.isContentEditable) return true
      return false
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
        gPrefixRef.current = null
        return
      }
      if (isEditable(e.target)) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === '?' && !e.repeat) {
        e.preventDefault()
        setShortcutHelpOpen((prev) => !prev)
        gPrefixRef.current = null
        return
      }
      if (e.key === 'g' && !e.repeat) {
        gPrefixRef.current = Date.now()
        return
      }
      if (gPrefixRef.current && Date.now() - gPrefixRef.current < 1000) {
        const target: Record<string, string> = {
          c: '/staff/circulation',
          h: '/staff/holds/shelf',
          p: '/staff/patrons',
          r: '/staff/book-drop',
        }
        const dest = target[e.key.toLowerCase()]
        if (dest) {
          e.preventDefault()
          navigate(dest)
          gPrefixRef.current = null
          return
        }
        gPrefixRef.current = null
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isStaffUser, navigate])

  // ─────────────────────────────────────────────────────────
  // NAVIGATION STRUCTURE
  // Declarative config lives in `header/navConfig.ts`. `getNavConfig` returns
  // the fully-filtered NavGroup[] for the current user/feature flags; the
  // render layer (MoreOverflow) decides what fits inline vs. into "More".
  // ─────────────────────────────────────────────────────────
  const groups = useMemo(
    () => getNavConfig({ t, isFeatureEnabled, role: user?.role, isAuthenticated }),
    [t, isFeatureEnabled, user?.role, isAuthenticated]
  )

  // Track viewport width to drop the lowest-priority mobile tile on small phones (<400px).
  const [isTinyPhone, setIsTinyPhone] = useState<boolean>(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(max-width: 399px)').matches
      : false,
  )
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(max-width: 399px)')
    const handler = (e: MediaQueryListEvent) => setIsTinyPhone(e.matches)
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', handler)
      return () => mq.removeEventListener('change', handler)
    }
    // Safari < 14 fallback
    mq.addListener(handler)
    return () => mq.removeListener(handler)
  }, [])

  // Observe the footer element so we can lift the FAB clear of the newsletter form.
  // We watch the footer landmark (id="footer") and lift when >=1px is in viewport.
  useEffect(() => {
    const el = document.getElementById('footer')
    if (!el) return
    footerObserverRef.current = el
    const obs = new IntersectionObserver(
      ([entry]) => setFooterInView(entry?.isIntersecting ?? false),
      { threshold: 0.01 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Mobile bottom nav — Search prominent, Account always visible.
  // Lowest-priority tile (Hours) drops into MobileMoreMenu on <400px screens.
  const bottomNavItems = useMemo(
    () => [
      ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/catalog', label: t('navigation.search'), icon: Search }] : []),
      ...(isFeatureEnabled('events_enabled') ? [{ to: '/events', label: t('navigation.events'), icon: Calendar }] : []),
      ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/discover', label: t('navigation.browse'), icon: Compass }] : []),
      ...(!isTinyPhone && isFeatureEnabled('front_desk_enabled') ? [{ to: '/branches', label: t('navigation.hoursAndLocations'), icon: MapPin }] : []),
      { to: '/account', label: t('navigation.account'), icon: User },
    ],
    [t, isFeatureEnabled, isTinyPhone]
  )

  // Longest-prefix-aware isActive shared across desktop nav + dropdowns + bottom nav.
  // Built from every section we render so prefix collisions (e.g. /staff vs
  // /staff/circulation) get resolved correctly.
  const knownNavPaths = useMemo(() => {
    return [
      '/catalog',
      '/events',
      '/discover',
      '/branches',
      '/account',
      '/ask-librarian',
      '/get-help',
      '/staff',
      ...groups.flatMap(g => g.sections.flatMap(s => s.items.map(i => i.to))),
    ]
  }, [groups])

  const isActive = useCallback(
    (path: string, exact = false): boolean =>
      isActiveShared(location.pathname, path, { exact, knownPaths: knownNavPaths }),
    [location.pathname, knownNavPaths],
  )


  // Ctrl+K: CommandPalette for staff (registered above), HeaderSearch for patrons (HeaderSearch.tsx).

  const handleOpenLogin = useCallback(() => {
    setAuthModalOpen(true)
  }, [])

  // Invite-only: "get a card" leads to the waiting list, not the sign-in modal.
  const handleOpenRegister = useCallback(() => {
    navigate('/register')
  }, [navigate])

  const handleCloseAuth = useCallback(() => {
    setAuthModalOpen(false)
  }, [])

  // Shell flag is declared at the route level (see AppRoutes.tsx) rather than inferred
  // from the URL. This lets pages outside /staff and /admin (e.g. /board/*,
  // /emergency-operations/*, /interlibrary-loan, /shift-swap) render with the
  // staff shell when they use <StaffLayout>.
  const isAdminRoute = staffShell
  const isEssentialsHomeRoute = isEssentialsMode && location.pathname === '/'

  return (
    <div className={clsx(
      "bg-lsc-cream dark:bg-lsc-dark flex flex-col",
      isAdminRoute ? "h-screen overflow-y-auto" : "min-h-screen"
    )}>
      {/* Skip links — must be first focusable elements in the DOM. Wrapped as a
          navigation landmark so screen-reader users can land here via landmark
          navigation. Targets are conditional: the desktop nav (#main-navigation)
          is `hidden lg:flex`, so below lg we point at the mobile bottom nav
          instead. The footer link is suppressed in the staff shell, which does
          not render <Footer />. */}
      <nav aria-label={t('a11y.skipLinks', 'Skip links')}>
        <div className="absolute left-4 top-4 z-[100] flex gap-2 focus-within:pointer-events-auto pointer-events-none">
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:px-4 focus:py-2 focus:bg-lsc-rose focus:text-lsc-cream focus:rounded-lg focus:shadow-lg focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
          >
            {t('a11y.skipToContent', 'Skip to main content')}
          </a>
          {isLargeScreen ? (
            <a
              href="#main-navigation"
              className="sr-only focus:not-sr-only focus:px-4 focus:py-2 focus:bg-lsc-rose focus:text-lsc-cream focus:rounded-lg focus:shadow-lg focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            >
              {t('navigation.skipToNavigation', 'Skip to navigation')}
            </a>
          ) : (
            !staffShell && (
              <a
                href="#mobile-bottom-nav"
                className="sr-only focus:not-sr-only focus:px-4 focus:py-2 focus:bg-lsc-rose focus:text-lsc-cream focus:rounded-lg focus:shadow-lg focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                {t('navigation.skipToMobileMenu', 'Skip to mobile menu')}
              </a>
            )
          )}
          {!staffShell && (
            <a
              href="#footer"
              className="sr-only focus:not-sr-only focus:px-4 focus:py-2 focus:bg-lsc-rose focus:text-lsc-cream focus:rounded-lg focus:shadow-lg focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            >
              {t('footer.skipToFooter', 'Skip to footer')}
            </a>
          )}
        </div>
      </nav>

      {/* Panic Alert System - keyboard shortcut only */}
      {isStaffUser && (
        <PanicErrorBoundary>
          <PanicAlertSystem
            showButton={false}
            enableKeyboardShortcut={true}
          />
        </PanicErrorBoundary>
      )}

      {/* Status banners — rendered ABOVE the sticky header so they persist
          when the header collapses on scroll-down (PR B). */}
      <SystemStatusBanner />
      <LibraryStatusBanner />

      {/* Sticky Header Container */}
      <div
        className={clsx(
          'sticky top-0 z-50',
          'motion-safe:transition-transform motion-safe:duration-300 motion-safe:ease-out',
          isSticky && !isVisible && '-translate-y-full'
        )}
      >
        <header
          className={clsx(
            'relative text-lsc-dark dark:text-lsc-cream',
            isSticky
              ? 'bg-lsc-white/95 dark:bg-earth-950/95 backdrop-blur-[12px] shadow-soft-lg border-b border-lsc-border dark:border-earth-700'
              : 'bg-lsc-white dark:bg-earth-950 border-b border-lsc-border dark:border-earth-700'
          )}
        >
          {/* Navigation progress indicator */}
          <NavigationProgress />

          <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <div className="flex items-center justify-between gap-2 xl:gap-4 lg:min-h-[60px] min-h-0">
              {/* Library name — desktop only */}
              <Link
                to="/"
                aria-label={t("errors.goHome")}
                className="hidden lg:flex items-center gap-2.5 shrink-0 text-lg font-bold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors whitespace-normal"
              >
                {branding.logo_url ? (
                  <img src={branding.logo_url} alt={branding.library_name} className="h-9 w-auto max-w-[240px] object-contain" />
                ) : (
                  <>
                    <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                    {branding.library_short_name}
                  </>
                )}
              </Link>

              {/* ─── Desktop Navigation ─── */}
              {/* lg (1024-1279px): Catalog + Events + "More" mega-menu (Services/Explore/Teachers/Visit/Ask).
                  xl+ (>=1280px):    Catalog + Events + Services + Explore + Teachers + Visit + Ask inline. */}
              <nav
                id="main-navigation"
                className="hidden lg:flex items-center gap-1 xl:gap-1.5 flex-1 min-w-0 pl-4"
                aria-label={t('navigation.mainNavigation')}
              >
                {/* On staff/admin routes the left rail is the real nav. Surface
                    Catalog + Events quick links and an explicit "View public
                    site" link so staff can reach patron pages — the top nav was
                    otherwise empty here after #1616 hid all marketing links. */}
                {isStaffRoute ? (
                  <>
                    {/* Quiet mode hides these quick links for a calmer header;
                        the staff left rail remains the primary navigation. */}
                    {!quietMode && isFeatureEnabled('collection_management_enabled') && (
                      <NavLink to="/catalog" isActive={isActive('/catalog')} icon={BookOpen}>
                        {t('navigation.catalog')}
                      </NavLink>
                    )}
                    {!quietMode && isFeatureEnabled('events_enabled') && (
                      <NavLink to="/events" isActive={isActive('/events')} icon={Calendar}>
                        {t('navigation.events')}
                      </NavLink>
                    )}
                  </>
                ) : (isEssentialsMode ? (
                  <>
                    {isFeatureEnabled('collection_management_enabled') && (
                    <NavLink to="/catalog" isActive={isActive('/catalog')} icon={BookOpen}>
                      {t('navigation.searchForBooks')}
                    </NavLink>
                    )}
                    {isFeatureEnabled('events_enabled') && (
                      <NavLink to="/events" isActive={isActive('/events')} icon={Calendar}>
                        {t('navigation.events')}
                      </NavLink>
                    )}
                    {isFeatureEnabled('front_desk_enabled') && (
                    <NavLink to="/branches" isActive={isActive('/branches')} icon={MapPin}>
                      {t('navigation.hoursAndLocations')}
                    </NavLink>
                    )}
                    {isFeatureEnabled('front_desk_enabled') && (
                    <NavLink to="/get-help" isActive={isActive('/get-help')} icon={MessageCircle}>
                      {t('navigation.getHelp')}
                    </NavLink>
                    )}
                    <button
                      type="button"
                      onClick={() => toggleEssentialsMode()}
                      disabled={isEssentialsLoading}
                      className="ml-auto inline-flex items-center gap-1.5 shrink-0 px-2.5 py-2 rounded-xl text-sm font-medium text-lsc-rose dark:text-lsc-rose-light border border-lsc-rose/40 dark:border-lsc-rose-light/40 hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose-light/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose motion-safe:transition-colors disabled:opacity-50"
                      aria-label={t('header.switchToFullMode', 'Switch to full view')}
                    >
                      <Sparkles aria-hidden="true" className="w-4 h-4" />
                      <span>{t('header.switchToFullMode', 'Full view')}</span>
                    </button>
                  </>
                ) : (
                  <>
                    {/* Catalog - primary action, gated by collection */}
                    {isFeatureEnabled('collection_management_enabled') && (
                    <NavLink to="/catalog" isActive={isActive('/catalog')} icon={BookOpen}>
                      {t('navigation.catalog')}
                    </NavLink>
                    )}

                    {/* Events - direct link (highest-traffic patron action) */}
                    {isFeatureEnabled('events_enabled') && (
                      <NavLink to="/events" isActive={isActive('/events')} icon={Calendar}>
                        {t('navigation.events')}
                      </NavLink>
                    )}

                    {/* Measured fit: MoreOverflow renders as many groups inline as the
                        available width allows, with any remainder collapsed into a single
                        "More" dropdown. Replaces the prior breakpoint-binary split, which
                        clipped items at narrow lg widths (overflow-hidden masked failure). */}
                    <MoreOverflow
                      items={groups}
                      renderItem={(g) => (
                        <NavDropdown
                          label={g.label}
                          icon={g.icon}
                          sections={g.sections}
                          isActive={isActive}
                          {...(g.align ? { align: g.align } : {})}
                        />
                      )}
                      moreLabel={t('navigation.more', 'More')}
                      isActive={isActive}
                    />

                    {/* Staff - conditional, visible at 2xl+ */}
                    {isStaffUser && (
                      <div className="hidden 2xl:block">
                        <NavLink to="/staff" isActive={isActive('/staff')} icon={Briefcase}>
                          {t('navigation.staff')}
                        </NavLink>
                      </div>
                    )}
                  </>
                ))}
              </nav>

              {/* Right side actions */}
              {/* Calm-mode toggle removed from header CTAs (was here, ~140px wide).
                  It is still discoverable via AccountDropdown's settings group
                  (desktop) and MobileMoreMenu (mobile). Removing it gives the
                  main nav the breathing room it needed at lg (1024-1279px). */}
              <div className="hidden lg:flex items-center gap-1.5 shrink-0">
                {isStaffUser && <HeaderSOSButton variant="desktop" />}
                <HeaderSearch variant="desktop" />

                {/* Ask a Librarian — icon button (PR B: demoted from inline nav). */}
                {isFeatureEnabled('front_desk_enabled') && (
                  <Link
                    to="/ask-librarian"
                    aria-label={t('navigation.askALibrarian', 'Ask a librarian')}
                    title={t('navigation.askALibrarian', 'Ask a librarian')}
                    className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose-light/10 hover:text-lsc-rose dark:hover:text-lsc-rose-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose motion-safe:transition-colors"
                  >
                    <HelpCircle aria-hidden="true" className="w-5 h-5" />
                  </Link>
                )}

                <QuietModeToggle showLabel={false} className="!px-2 !py-2 !rounded-lg !border-0" />

                <LanguageSwitcher />

                {/* Notifications (authenticated only) */}
                {isAuthenticated && <NotificationsDropdown variant="desktop" />}

                {/* Get a Library Card CTA (non-authenticated) */}
                {!isAuthenticated && (
                  <button
                    onClick={handleOpenRegister}
                    className="hidden xl:flex items-center gap-2 px-3 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-full text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
                  >
                    <CreditCard aria-hidden="true" className="w-4 h-4" />
                    {t('home.quickLinks.libraryCard.title')}
                  </button>
                )}

                {/* Account dropdown */}
                <AccountDropdown
                  onOpenLogin={handleOpenLogin}
                  onOpenRegister={handleOpenRegister}
                />
              </div>

              {/* Mobile: Library name + Search/Notifications */}
              <Link
                to="/"
                aria-label={t("errors.goHome")}
                className="lg:hidden flex items-center gap-2 shrink-0 text-base font-bold text-lsc-dark dark:text-lsc-cream whitespace-normal"
              >
                {branding.logo_url ? (
                  <img src={branding.logo_url} alt={branding.library_name} className="h-8 w-auto max-w-[180px] object-contain" />
                ) : (
                  <>
                    <BookOpen className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                    <span className="hidden sm:inline">{t('components.layout.l30Library', 'L30 Library')}</span>
                    <span className="sm:hidden">{branding.library_short_name}</span>
                  </>
                )}
              </Link>
              <div className="flex lg:hidden items-center gap-1">
                {isStaffUser && <HeaderSOSButton variant="mobile" />}
                <HeaderSearch variant="mobile" />
                {isFeatureEnabled('front_desk_enabled') && (
                  <Link
                    to="/ask-librarian"
                    aria-label={t('navigation.askALibrarian', 'Ask a librarian')}
                    title={t('navigation.askALibrarian', 'Ask a librarian')}
                    className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose-light/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
                  >
                    <HelpCircle aria-hidden="true" className="w-5 h-5" />
                  </Link>
                )}
                <LanguageSwitcher />
                {isAuthenticated && <NotificationsDropdown variant="mobile" />}
              </div>
            </div>
          </div>
        </header>


        {accessibilitySettings.blinders && (
          <div className="bg-lsc-rose border-t border-b border-lsc-rose/80">
            <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-2 flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium text-white">{t('components.layout.focusTunnelIsOn')}</span>
              <span className="text-white/90">{t('components.layout.thisNarrowsPageWidthTo')}</span>
              <button
                type="button"
                onClick={() => updateAccessibilitySetting('blinders', false)}
                className="ml-auto underline underline-offset-2 text-white hover:no-underline focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
              >
                {t('components.layout.turnOff')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <main
        id="main-content"
        className={clsx(
          "flex-1",
          isAdminRoute
            ? "overflow-auto min-h-0"
            : isEssentialsHomeRoute
              ? "w-full pb-24 lg:pb-8"
              : "max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full pb-24 lg:pb-8"
        )}
        tabIndex={-1}
      >
        {!isAdminRoute && !isEssentialsHomeRoute && <Breadcrumbs />}
        <Outlet />
      </main>

      {!isAdminRoute && <Footer />}

      {/* Mobile Bottom Navigation */}
      {!isAdminRoute && (
        <nav
          id="mobile-bottom-nav"
          tabIndex={-1}
          className="lg:hidden fixed bottom-0 left-0 right-0 bg-lsc-cream/95 dark:bg-lsc-brown/95 backdrop-blur-[12px] border-t border-lsc-border/60 dark:border-lsc-dark/20 z-40 shadow-soft-lg"
          style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
          aria-label={t('navigation.mobileNavigation')}
        >
          <div className="flex justify-around items-stretch gap-1">
            {bottomNavItems.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex flex-col items-center justify-center gap-1 px-1 sm:px-4 py-2.5 min-w-[64px] min-h-[48px] sm:min-h-[60px] flex-1 rounded-none transition-all duration-200 touch-manipulation relative',
                  isActive(to)
                    ? 'nav-active text-lsc-rose dark:text-lsc-rose-light font-bold'
                    : 'text-lsc-dark hover:text-lsc-rose dark:text-lsc-cream dark:hover:text-lsc-rose active:bg-lsc-border/30 dark:active:bg-lsc-dark/30'
                )}
                aria-current={isActive(to) ? 'page' : undefined}
              >
                {/* Active indicator bar (absolute — no layout shift) */}
                {isActive(to) && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-0.5 bg-lsc-rose dark:bg-lsc-rose-light rounded-b-lg motion-safe:animate-scale-in" aria-hidden="true" />
                )}
                <Icon aria-hidden="true" className="w-6 h-6" />
                <span className="text-xs leading-tight max-w-[60px] sm:max-w-none whitespace-normal">{label}</span>
              </Link>
            ))}
            <MobileMoreMenu
              onOpenAuth={handleOpenLogin}
              isTinyPhone={isTinyPhone}
            />
          </div>
        </nav>
      )}

      {/* Auth Modals */}
      <AuthModals
        isOpen={authModalOpen}
        onClose={handleCloseAuth}
      />

      {/* Floating Accessibility Widget - controlled: we render our own trigger button
           so we can (a) show a first-visit visible label and (b) lift clear of the
           footer newsletter form via footerInView. The widget hides its own trigger
           when open/onOpenChange are supplied. */}
      {!isAdminRoute && (
        <>
          {/* Custom trigger button with first-visit label */}
          {!widgetOpen && (
            <button
              type="button"
              onClick={() => {
                setWidgetOpen(true)
                if (!fabSeen) {
                  try { localStorage.setItem('l30.a11yFabSeen', '1') } catch { /* noop */ }
                  setFabSeen(true)
                }
              }}
              className={[
                'fixed right-4 z-[9980] flex items-center gap-2',
                'px-3 py-3 rounded-full shadow-lg',
                'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
                'motion-safe:transition-all',
                // Lift the FAB above the footer when it scrolls into view.
                // At lg+ (no mobile-bottom-nav), bottom-4 normally; when footer
                // is visible, lift to ~180px to clear the newsletter form at all
                // widths from 768px to 1600px.
                // Below lg, add extra for the mobile bottom nav (bottom-20 = 5rem).
                footerInView
                  ? 'bottom-[180px]'
                  : 'bottom-20 lg:bottom-4',
              ].join(' ')}
              aria-label={t('a11y.fab.label', 'Display and access settings')}
              aria-expanded={widgetOpen}
            >
              <Settings className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {!fabSeen && (
                <span className="text-sm font-medium whitespace-nowrap pr-1">
                  {t('a11y.fab.label', 'Display and access settings')}
                </span>
              )}
            </button>
          )}
          <QuickAccessibilityWidget
            position="bottom-right"
            onOpenSettings={() => { setWidgetOpen(false); window.location.href = '/accessibility' }}
            open={widgetOpen}
            onOpenChange={setWidgetOpen}
          />
        </>
      )}

      {/* Enhancement 3: Staff Command Palette (Cmd+K) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {/* Staff keyboard shortcut help overlay (?) */}
      {shortcutHelpOpen && isStaffUser && (
        <ShortcutHelpDialog onClose={() => setShortcutHelpOpen(false)} />
      )}
    </div>
  )
}
