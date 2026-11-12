/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Briefcase,
  MoreHorizontal,
  X,
  LogIn,
  LogOut,
  Monitor,
  MessageCircle,
  Laptop,
  Globe,
  CreditCard,
  ShoppingCart,
  Feather,
  Bookmark,
  BookOpen,
  GraduationCap,
  DoorOpen,
  Gavel,
  Sparkles,
  Truck,
  VolumeX,
  Volume2,
  Settings2,
  Heart,
  Phone as PhoneIcon,
  FileText,
  Compass,
  Printer,
  BookOpenCheck,
  ListChecks,
  Award,
  MessageCircleQuestion,
  Users,
  Calendar,
  MapPin,
  Scale,
} from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '../i18n/I18nContext'
import { useHapticFeedback } from '../hooks/useHapticFeedback'
import LanguageSwitcher from './LanguageSwitcher'
import { clsx } from '@/utils/helpers'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useScrollLock } from '../hooks/useScrollLock'

interface MobileMoreMenuProps {
  onOpenAuth: () => void
  isTinyPhone?: boolean
}

export default function MobileMoreMenu({ onOpenAuth, isTinyPhone = false }: MobileMoreMenuProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false)
  const [showLanguages, setShowLanguages] = useState(false)
  const location = useLocation()
  const { isAuthenticated, logout, user } = useAuth()
  const { t } = useTranslation()
  const haptic = useHapticFeedback()
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const triggerButtonRef = useRef<HTMLButtonElement>(null)
  const { settings: a11ySettings, updateSetting: updateA11ySetting } = useUnifiedAccessibility()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const quietMode = a11ySettings?.quietMode || false
  const touchStartY = useRef<number>(0)
  const touchEndY = useRef<number>(0)

  const handleClose = useCallback(() => {
    setIsOpen(false)
    setShowLanguages(false)
  }, [])

  // Swipe down to close gesture
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartY.current = e.touches[0]?.clientY ?? 0
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    touchEndY.current = e.touches[0]?.clientY ?? 0
  }, [])

  const handleTouchEnd = useCallback(() => {
    const swipeDistance = touchEndY.current - touchStartY.current
    const swipeThreshold = 100 // Minimum swipe distance in pixels

    // If swiped down more than threshold, close the menu
    if (swipeDistance > swipeThreshold) {
      haptic.light()
      handleClose()
    }
  }, [handleClose, haptic])

  // Close menu when route changes
  useEffect(() => {
    Promise.resolve().then(() => {
      handleClose()
    })
  }, [location.pathname, handleClose])

  useScrollLock(isOpen)

  const isActive = (path: string): boolean => {
    // Split off optional query string so links like '/account?tab=checkouts'
    // can compare query params against the current URL, not just pathname.
    const [pathOnly = '', queryStr] = path.split('?')
    if (!location.pathname.startsWith(pathOnly)) return false
    if (!queryStr) return true
    const expected = new URLSearchParams(queryStr)
    const actual = new URLSearchParams(location.search)
    for (const [k, v] of expected) {
      if (actual.get(k) !== v) return false
    }
    return true
  }
  const isStaffUser = Boolean(user && ['staff', 'admin', 'super_admin', 'director'].includes(user.role))

  // ─────────────────────────────────────────────────────────
  // Mirror desktop nav grouping: 3 top-level "areas" (Services,
  // Explore, Visit), each with one or more sub-sections. Items
  // already in the bottom tab bar (Catalog, Events, Hours,
  // Account) are surfaced via quick-action chips above instead.
  // ─────────────────────────────────────────────────────────
  const navAreas = useMemo(
    () => [
      {
        key: 'services',
        heading: t('navigation.services'),
        sections: [
          {
            heading: t('navigation.libraryServices'),
            items: [
              ...(isFeatureEnabled('front_desk_enabled') ? [{ to: '/get-started', label: t('navigation.getALibraryCard'), icon: CreditCard, description: t('navigation.getALibraryCardDesc') }] : []),
              ...(isFeatureEnabled('home_delivery_enabled') ? [{ to: '/home-delivery', label: t('navigation.homeDelivery'), icon: Truck, description: t('navigation.homeDeliveryDesc') }] : []),
              ...(isFeatureEnabled('meeting_rooms_enabled') ? [{ to: '/rooms', label: t('navigation.reserveARoom'), icon: DoorOpen, description: t('navigation.reserveARoomDesc') }] : []),
              { to: '/suggest-purchase', label: t('navigation.suggestPurchase'), icon: ShoppingCart, description: t('navigation.suggestPurchaseDesc') },
            ],
          },
          {
            heading: t('navigation.helpAndSupport'),
            items: [
              { to: '/contact', label: t('navigation.contactUs'), icon: PhoneIcon, description: t('navigation.contactUsDesc') },
              { to: '/get-help', label: t('navigation.getHelp'), icon: MessageCircle, description: t('components.layout.chatEmailOrCallFor') },
              ...(isFeatureEnabled('legal_services_enabled') ? [{ to: '/legal', label: t('navigation.legalHelp') || 'Legal Help', icon: Scale, description: t('navigation.legalHelpDesc') || 'Free legal resources, forms, and aid connections' }] : []),
              { to: '/tech', label: t('navigation.techSupport'), icon: Laptop, description: t('navigation.techSupportDesc') },
            ],
          },
        ],
      },
      {
        key: 'explore',
        heading: t('navigation.explore'),
        sections: [
          {
            heading: t('navigation.exploreReadAndDiscover'),
            items: [
              ...(isFeatureEnabled('community_features_enabled') ? [{ to: '/blog', label: t('navigation.blog', 'Blog'), icon: FileText, description: t('navigation.blogDesc', 'Insights on library technology and digital literacy') }] : []),
              ...(isFeatureEnabled('book_clubs_enabled') ? [{ to: '/book-clubs', label: t('navigation.bookClubs'), icon: BookOpen, description: t('navigation.bookClubsDesc') }] : []),
              ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/digital', label: t('navigation.digitalResources'), icon: Monitor, description: t('navigation.digitalResourcesDesc') }] : []),
              ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/discover', label: t('navigation.discover', 'Discover'), icon: Compass, description: t('navigation.discoverDesc', 'Staff picks, new arrivals, and what your neighbors are reading') }] : []),
              ...(isFeatureEnabled('reading_programs_enabled') ? [{ to: '/programs', label: t('navigation.readingPrograms'), icon: Bookmark, description: t('navigation.readingProgramsDesc') }] : []),
            ],
          },
          {
            heading: t('navigation.exploreLearnAndCreate'),
            items: [
              ...(isFeatureEnabled('ai_tools_enabled') ? [{ to: '/ai', label: t('navigation.aiTools'), icon: Sparkles, description: t('navigation.aiToolsDesc') }] : []),
              ...(isFeatureEnabled('banned_books_tracking_enabled') ? [{ to: '/banned-books', label: t('navigation.intellectualFreedom'), icon: Scale, description: t('navigation.intellectualFreedomDesc') }] : []),
              ...(isFeatureEnabled('learning_platform_enabled') ? [{ to: '/learn', label: t('navigation.learningAndClasses'), icon: GraduationCap, description: t('navigation.learningAndClassesDesc') }] : []),
              ...(isFeatureEnabled('indie_platform_enabled') ? [{ to: '/indie', label: t('navigation.localAuthors'), icon: Feather, description: t('navigation.localAuthorsDesc') }] : []),
            ],
          },
        ],
      },
      {
        key: 'visit',
        heading: t('navigation.visit'),
        sections: [
          {
            // Single-section area — render with no subheading to avoid duplicate
            heading: null,
            items: [
              ...(isTinyPhone && isFeatureEnabled('front_desk_enabled') ? [{ to: '/branches', label: t('navigation.hoursAndLocations'), icon: MapPin, description: t('navigation.hoursAndLocationsDesc') }] : []),
              ...(isFeatureEnabled('board_features_enabled') ? [{ to: '/board/meetings', label: t('navigation.boardAndGovernance'), icon: Gavel, description: t('navigation.boardAndGovernanceDesc') }] : []),
            ],
          },
        ],
      },
    ],
    [t, isFeatureEnabled, isTinyPhone]
  )

  // Strip out empty sections and empty areas (when feature flags hide everything)
  const filteredNavAreas = useMemo(
    () =>
      navAreas
        .map((area) => ({
          ...area,
          sections: area.sections.filter((s) => s.items.length > 0),
        }))
        .filter((area) => area.sections.length > 0),
    [navAreas]
  )

  // Mobile-only community shortcuts — not in desktop nav but kept for discoverability
  const communityItems = useMemo(
    () => [
      { to: '/help-guide', label: t('navigation.lifeSituationsCommunityHelp', 'Life Situations & Community Help'), icon: Heart },
      ...(isFeatureEnabled('community_features_enabled') ? [{ to: '/parent-mentors', label: t('navigation.parentMentors', 'Parent Mentors'), icon: Heart }] : []),
    ],
    [isFeatureEnabled]
  )

  const handleSignIn = () => {
    handleClose()
    onOpenAuth()
  }

  const handleSignOut = () => {
    logout()
    handleClose()
  }

  // Shared link styles - tighter spacing for half-sheet
  const linkClasses = (path: string) =>
    clsx(
      'flex items-center gap-3 px-3 py-2.5 min-h-[44px] rounded-xl transition-colors touch-manipulation',
      isActive(path)
        ? 'bg-lsc-rose/10 text-lsc-rose'
        : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10'
    )

  return (
    <>
      {/* More button in bottom nav */}
      <button
        ref={triggerButtonRef}
        onClick={() => {
          haptic.light()
          setIsOpen(true)
        }}
        className={clsx(
          'flex flex-col items-center justify-center gap-1 sm:gap-1.5 px-1 sm:px-4 py-2.5 min-w-[48px] sm:min-w-[68px] min-h-[56px] sm:min-h-[60px] flex-1 rounded-none transition-all duration-200 touch-manipulation',
          isOpen
            ? 'text-lsc-rose dark:text-lsc-rose-light'
            : 'text-lsc-dark hover:text-lsc-rose dark:text-lsc-cream dark:hover:text-lsc-rose'
        )}
        aria-label={t('navigation.menu')}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <MoreHorizontal aria-hidden="true" className="w-6 h-6" />
        <span className="text-xs whitespace-nowrap leading-tight">{t('navigation.menu')}</span>
      </button>

      {/* Half-sheet navigation overlay */}
      {isOpen && (
        <FocusTrap
          active={isOpen}
          focusTrapOptions={{
            initialFocus: () => closeButtonRef.current,
            allowOutsideClick: true,
            // Escape is handled by the FocusTrap (was duplicated with a manual
            // document-level keydown listener — removed).
            escapeDeactivates: true,
            // Fallback must be focusable; document.body is not. Trigger button
            // is rendered alongside the drawer in the same parent.
            fallbackFocus: () => (closeButtonRef.current ?? triggerButtonRef.current)!,
            returnFocusOnDeactivate: true,
            onDeactivate: () => {
              // Sync visual state when ESC deactivates the trap so the drawer
              // actually closes. returnFocusOnDeactivate handles focus return;
              // the explicit trigger-focus call is belt-and-suspenders.
              handleClose()
              triggerButtonRef.current?.focus()
            },
          }}
        >
          <div className="fixed inset-0 z-50 flex flex-col justify-end pointer-events-none">
            {/* Semi-transparent backdrop - click to dismiss */}
            <div
              className="absolute inset-0 bg-black/30 dark:bg-black/50 motion-safe:animate-backdrop-fade pointer-events-auto"
              onClick={() => {
                haptic.light()
                handleClose()
              }}
              aria-hidden="true"
            />

            {/* Half-sheet panel */}
            <div
              role="dialog"
              aria-label={t('navigation.menu')}
              aria-modal="true"
              className="relative bg-lsc-cream dark:bg-lsc-brown rounded-t-3xl max-h-[70vh] flex flex-col motion-safe:animate-slide-up-half shadow-soft-xl pointer-events-auto"
              style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
              {/* Header with swipe indicator */}
              <div className="flex flex-col flex-shrink-0">
                {/* Swipe indicator */}
                <div className="flex items-center justify-center py-2" aria-hidden="true">
                  <div className="w-12 h-1 bg-lsc-dark/20 dark:bg-lsc-cream/20 rounded-full" />
                </div>
                <div className="flex items-center justify-between px-4 py-2">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('navigation.menu')}
                  </h2>
                  <button
                    ref={closeButtonRef}
                    onClick={() => {
                      haptic.light()
                      handleClose()
                    }}
                    className="p-3 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-full hover:bg-lsc-border dark:hover:bg-lsc-dark/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-status-warning-400 touch-manipulation"
                    aria-label={t('common.close')}
                  >
                    <X aria-hidden="true" className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
                  </button>
                </div>
              </div>

              {/* Quick-action tiles */}
              <div className="flex flex-wrap gap-2 px-4 pb-3 flex-shrink-0">
                <Link
                  to="/get-help"
                  className="flex items-center gap-2 px-4 py-2.5 min-h-[44px] bg-lsc-rose/10 dark:bg-lsc-rose/15 text-lsc-rose dark:text-lsc-rose-light rounded-full text-sm font-medium transition-colors hover:bg-lsc-rose/15 dark:hover:bg-lsc-rose/20 touch-manipulation"
                >
                  <MessageCircle aria-hidden="true" className="w-4 h-4" />
                  {t('navigation.getHelp')}
                </Link>
                {isFeatureEnabled('meeting_rooms_enabled') && (
                  <Link
                    to="/rooms"
                    className="flex items-center gap-2 px-4 py-2.5 min-h-[44px] bg-lsc-border/50 dark:bg-lsc-dark/30 text-lsc-dark dark:text-lsc-cream rounded-full text-sm font-medium transition-colors hover:bg-lsc-border dark:hover:bg-lsc-dark/40 touch-manipulation"
                  >
                    <DoorOpen aria-hidden="true" className="w-4 h-4" />
                    {t('navigation.reserveARoom')}
                  </Link>
                )}
                {isFeatureEnabled('collection_management_enabled') && (
                <Link
                  to="/digital"
                  className="flex items-center gap-2 px-4 py-2.5 min-h-[44px] bg-lsc-border/50 dark:bg-lsc-dark/30 text-lsc-dark dark:text-lsc-cream rounded-full text-sm font-medium transition-colors hover:bg-lsc-border dark:hover:bg-lsc-dark/40 touch-manipulation"
                >
                  <Monitor aria-hidden="true" className="w-4 h-4" />
                  {t('navigation.digitalResources')}
                </Link>
                )}
              </div>

              {/* Scrollable content */}
              <nav
                className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 space-y-4"
                aria-label={t('navigation.mobileNavigation')}
              >
                {/* Auth section - sign-in prompt for unauthenticated users */}
                {!isAuthenticated && (
                  <div className="space-y-2 pb-2">
                    <button
                      onClick={handleSignIn}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
                    >
                      <LogIn aria-hidden="true" className="w-5 h-5" />
                      <span className="font-medium">{t('navigation.login')}</span>
                    </button>
                  </div>
                )}

                {/* Grouped nav areas — mirrors desktop dropdown grouping
                    (Services / Explore / Visit), with subsection headings
                    inside each area. */}
                {filteredNavAreas.map((area) => (
                  <section
                    key={area.key}
                    aria-labelledby={`mobile-nav-area-${area.key}`}
                    className="space-y-2"
                  >
                    <h3
                      id={`mobile-nav-area-${area.key}`}
                      className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream px-3 pt-1"
                    >
                      {area.heading}
                    </h3>
                    {area.sections.map((section, idx) => (
                      <div key={section.heading ?? `${area.key}-${idx}`}>
                        {section.heading && (
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/70 px-3 mb-1">
                            {section.heading}
                          </h4>
                        )}
                        {section.items.map(({ to, label, icon: Icon, description }: { to: string; label: string; icon: React.ElementType; description?: string }) => (
                          <Link
                            key={to}
                            to={to}
                            className={linkClasses(to)}
                            aria-current={isActive(to) ? 'page' : undefined}
                          >
                            <Icon aria-hidden="true" className="w-5 h-5 shrink-0" />
                            <span className="flex flex-col items-start min-w-0 flex-1">
                              <span className="text-base">{label}</span>
                              {description && (
                                <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 leading-tight">
                                  {description}
                                </span>
                              )}
                            </span>
                          </Link>
                        ))}
                      </div>
                    ))}
                  </section>
                ))}

                {/* My Library — personal items for authenticated patrons.
                    Mirrors the AccountDropdown cleanup: canonical My Account and
                    My Checkouts links; ebooks/shelf reachable as tabs inside /account.
                    My Print Jobs and My Reports remain (separate top-level routes). */}
                {isAuthenticated && (
                  <section aria-labelledby="mobile-nav-area-my-library" className="space-y-1">
                    <h3
                      id="mobile-nav-area-my-library"
                      className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream px-3 pt-1"
                    >
                      {t('navigation.myLibrary')}
                    </h3>
                    <Link to="/account" className={linkClasses('/account')} aria-current={isActive('/account') ? 'page' : undefined}>
                      <Monitor aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.myAccount')}</span>
                    </Link>
                    <Link to="/account?tab=checkouts" className={linkClasses('/account?tab=checkouts')}>
                      <Monitor aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.myCheckouts', 'My Checkouts')}</span>
                    </Link>
                    {isFeatureEnabled('printing_enabled') && (
                      <Link to="/my-prints" className={linkClasses('/my-prints')} aria-current={isActive('/my-prints') ? 'page' : undefined}>
                        <Printer aria-hidden="true" className="w-5 h-5" />
                        <span className="text-base">{t('navigation.myPrintJobs')}</span>
                      </Link>
                    )}
                    <Link to="/my-reports" className={linkClasses('/my-reports')} aria-current={isActive('/my-reports') ? 'page' : undefined}>
                      <FileText aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.myReports')}</span>
                    </Link>
                  </section>
                )}

                {/* For Teachers — patron-side teacher portal, auth + feature gated */}
                {isAuthenticated && isFeatureEnabled('for_teachers_enabled') && (
                  <section aria-labelledby="mobile-nav-area-for-teachers" className="space-y-1">
                    <h3
                      id="mobile-nav-area-for-teachers"
                      className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream px-3 pt-1"
                    >
                      {t('navigation.forTeachers')}
                    </h3>
                    <Link to="/teacher/reading-dashboard" className={linkClasses('/teacher/reading-dashboard')} aria-current={isActive('/teacher/reading-dashboard') ? 'page' : undefined}>
                      <BookOpenCheck aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.teacherReadingDashboard')}</span>
                    </Link>
                    <Link to="/teacher/reading-lists" className={linkClasses('/teacher/reading-lists')} aria-current={isActive('/teacher/reading-lists') ? 'page' : undefined}>
                      <ListChecks aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.teacherReadingLists')}</span>
                    </Link>
                    <Link to="/teacher/professional-development" className={linkClasses('/teacher/professional-development')} aria-current={isActive('/teacher/professional-development') ? 'page' : undefined}>
                      <Award aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.professionalDevelopment')}</span>
                    </Link>
                    <Link to="/teacher/library-consultations" className={linkClasses('/teacher/library-consultations')} aria-current={isActive('/teacher/library-consultations') ? 'page' : undefined}>
                      <MessageCircleQuestion aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.librarianConsultations')}</span>
                    </Link>
                    <Link to="/teacher/family-challenges" className={linkClasses('/teacher/family-challenges')} aria-current={isActive('/teacher/family-challenges') ? 'page' : undefined}>
                      <Users aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.familyReadingChallenges')}</span>
                    </Link>
                    <Link to="/teacher/library-visits" className={linkClasses('/teacher/library-visits')} aria-current={isActive('/teacher/library-visits') ? 'page' : undefined}>
                      <Calendar aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base">{t('navigation.libraryVisitScheduling')}</span>
                    </Link>
                  </section>
                )}

                {/* Community — mobile-only, not surfaced in desktop nav */}
                {communityItems.length > 0 && (
                  <section aria-labelledby="mobile-nav-area-community">
                    <h3
                      id="mobile-nav-area-community"
                      className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream px-3 pt-1 mb-1"
                    >
                      {t('navigation.community')}
                    </h3>
                    {communityItems.map(({ to, label, icon: Icon }) => (
                      <Link
                        key={to}
                        to={to}
                        className={linkClasses(to)}
                        aria-current={isActive(to) ? 'page' : undefined}
                      >
                        <Icon aria-hidden="true" className="w-5 h-5" />
                        <span className="text-base">{label}</span>
                      </Link>
                    ))}
                  </section>
                )}

                {/* Staff - only visible to staff/admin users */}
                {isStaffUser && (
                  <div className="border-t border-lsc-border dark:border-lsc-dark/30 pt-3">
                    <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 px-3 mb-1">
                      {t('navigation.staff')}
                    </h3>
                    {[
                      { to: '/staff', label: t('navigation.staff'), icon: Briefcase },
                    ].map(({ to, label, icon: Icon }) => (
                      <Link
                        key={to}
                        to={to}
                        className={linkClasses(to)}
                        aria-current={isActive(to) ? 'page' : undefined}
                      >
                        <Icon aria-hidden="true" className="w-5 h-5" />
                        <span className="text-base">{label}</span>
                      </Link>
                    ))}
                  </div>
                )}

                {/* Settings - with sign-out inline */}
                <div className="border-t border-lsc-border dark:border-lsc-dark/30 pt-3">
                  <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 px-3 mb-1">
                    {t('navigation.settings')}
                  </h3>

                  <button
                    onClick={() => {
                      haptic.medium()
                      updateA11ySetting('quietMode', !quietMode)
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 min-h-[44px] rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors touch-manipulation"
                    aria-pressed={quietMode}
                  >
                    {quietMode ? (
                      <VolumeX aria-hidden="true" className="w-5 h-5" />
                    ) : (
                      <Volume2 aria-hidden="true" className="w-5 h-5" />
                    )}
                    <span className="text-base">
                      {quietMode ? t('header.quietModeOn', 'Quiet Mode: On') : t('header.quietMode', 'Quiet Mode')}
                    </span>
                  </button>

                  <Link
                    to="/accessibility"
                    className={linkClasses('/accessibility')}
                    aria-current={isActive('/accessibility') ? 'page' : undefined}
                    onClick={handleClose}
                  >
                    <Settings2 aria-hidden="true" className="w-5 h-5" />
                    <span className="text-base">{t('accessibility.title')}</span>
                  </Link>

                  <button
                    onClick={() => setShowLanguages(!showLanguages)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 min-h-[44px] rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors touch-manipulation"
                    aria-expanded={showLanguages}
                  >
                    <Globe aria-hidden="true" className="w-5 h-5" />
                    <span className="text-base">{t('navigation.language')}</span>
                  </button>

                  {showLanguages && (
                    <div className="px-2 py-2 bg-lsc-border/30 dark:bg-lsc-dark/20 rounded-xl mx-2 mb-2">
                      <LanguageSwitcher inline />
                    </div>
                  )}

                  {/* Sign out - inline in settings section */}
                  {isAuthenticated && (
                    <button
                      onClick={handleSignOut}
                      className="w-full flex items-center gap-3 px-3 py-2.5 min-h-[44px] rounded-xl text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors touch-manipulation"
                    >
                      <LogOut aria-hidden="true" className="w-5 h-5" />
                      <span className="text-base font-medium">{t('navigation.logout')}</span>
                    </button>
                  )}
                </div>
              </nav>
            </div>
          </div>
        </FocusTrap>
      )}
    </>
  )
}
