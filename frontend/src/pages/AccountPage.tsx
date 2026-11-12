/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import type { OrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import {
  getMyCheckouts,
  getMyHolds,
  getMyHistory,
  getMyFinesSummary,
  renewCheckout,
  cancelHold,
  getMyFavorites,
  removeFavorite,
  getMyLists,
  createList,
  getList,
  deleteList,
  removeFromList,
  updateListPrivacy,
  getMyEventRegistrations,
  Checkout,
  Hold,
  FinesSummary,
  Favorite,
  ReadingList,
  ReadingListWithItems,
  MyEventRegistration,
} from '../services/api'
import {
  User, Users, LogOut, Book, Clock, Calendar,
  Loader2, Settings, Bell, Shield, History,
  Heart, List, BookMarked, AlertCircle, Database,
  HandHeart,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useSearchParams } from 'react-router-dom'
import { useJourneyTracker } from '@/hooks/useJourneyTracker'
import { useTranslation, getCurrentLocale } from '@/i18n'

const MyBooksPage = lazy(() => import('./MyBooksPage'))
const VolunteerDashboard = lazy(() => import('../components/VolunteerManagement').then(m => ({ default: m.VolunteerDashboard })))
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { fetchApi } from '@/lib/api-client'
import { NotificationsSection } from '../components/account/NotificationsSection'
import { ListsSection } from '../components/account/ListsSection'
import { SecuritySection } from '../components/account/SecuritySection'
import { useSessions, usePasswordChange } from '../hooks/useSecurity'
import { getNotificationPreferences, updateNotificationPreferences, NotificationPreferences } from '@/api/notifications-api'
import { getActiveBorrows, returnEbook, type EbookBorrow } from '@/api/indie-catalog-api'
import { getMyMetisLibCheckouts, type MetisLibCheckout } from '@/api/domains/catalog/metislib-api'
import { AuthForm } from '../components/account/AuthForm'
import TemporaryCardBanner from '../components/TemporaryCardBanner'
import { OverviewTab } from '../components/account/OverviewTab'
import { CheckoutsTab } from '../components/account/CheckoutsTab'
import { HoldsTab } from '../components/account/HoldsTab'
import { EventsTab } from '../components/account/EventsTab'
import { FamilyOverview } from '../components/account/FamilyOverview'
import { FavoritesTab } from '../components/account/FavoritesTab'
import { HistoryTab } from '../components/account/HistoryTab'
import { SettingsTab } from '../components/account/SettingsTab'
import { MyDataTab } from '../components/account/MyDataTab'
import { FinesReviewSection } from '../components/account/FinesReviewSection'
import { Link } from 'react-router-dom'
import PageContainer from '@/components/layout/PageContainer'
import { usePageTitle } from '@/hooks/usePageTitle'

type UnifiedCheckoutItem =
  | { type: 'library'; data: Checkout }
  | { type: 'indie'; data: EbookBorrow }
  | { type: 'metislib'; data: MetisLibCheckout }

type AccountTab = 'overview' | 'checkouts' | 'ebooks' | 'holds' | 'events' | 'family' | 'favorites' | 'lists' | 'history' | 'my-data' | 'settings' | 'notifications' | 'security' | 'author-dashboard' | 'volunteer'

const ALL_TABS: AccountTab[] = ['overview', 'checkouts', 'ebooks', 'holds', 'events', 'family', 'favorites', 'lists', 'history', 'my-data', 'settings', 'notifications', 'security', 'author-dashboard', 'volunteer']

// Single source of truth for tab -> org-feature flag. Consulted by both the
// useState initializer (to avoid mounting a flag-disabled tab from a bookmarked
// URL) and by rawNavSections (so the visible nav stays in sync). Tabs not
// listed here are always available.
const TAB_FLAGS: Partial<Record<AccountTab, keyof OrganizationFeatures>> = {
  ebooks: 'indie_platform_enabled',
  events: 'events_enabled',
  family: 'family_card_enabled',
  volunteer: 'volunteers_enabled',
  notifications: 'notifications_enabled',
  'author-dashboard': 'indie_platform_enabled',
}

export default function AccountPage(): React.ReactElement {
  const { t } = useTranslation()
  usePageTitle(t('account.myAccount', 'My Account'))
  const { user, token, isLoading, isAuthenticated, logout } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') as AccountTab | null
  const [activeTab, setActiveTab] = useState<AccountTab>(() => {
    if (!initialTab || !ALL_TABS.includes(initialTab as AccountTab)) return 'overview'
    const flag = TAB_FLAGS[initialTab as AccountTab]
    if (flag && !isFeatureEnabled(flag as Parameters<typeof isFeatureEnabled>[0])) return 'overview'
    return initialTab as AccountTab
  })

  const accountTracker = useJourneyTracker({ journeyType: "account_self_service" })
  const renewalTracker = useJourneyTracker({ journeyType: "renewal" })

  // Track account_accessed on mount
  useEffect(() => { accountTracker.trackStage("account_accessed") }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Track section_selected on tab change
  useEffect(() => {
    if (activeTab !== "overview") {
      accountTracker.trackStage("section_selected", { section: activeTab })
    }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps


  const [checkouts, setCheckouts] = useState<Checkout[]>([])
  const [holds, setHolds] = useState<Hold[]>([])
  const [history, setHistory] = useState<Checkout[]>([])
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [lists, setLists] = useState<ReadingList[]>([])
  const [myEvents, setMyEvents] = useState<MyEventRegistration[]>([])
  const [finesSummary, setFinesSummary] = useState<FinesSummary>({ total_outstanding: 0, total_paid: 0, outstanding_count: 0, paid_count: 0 })
  const [indieBorrows, setIndieBorrows] = useState<EbookBorrow[]>([])
  const [indieBorrowError, setIndieBorrowError] = useState(false)
  const [metislibCheckouts, setMetislibCheckouts] = useState<MetisLibCheckout[]>([])

  const [checkoutsLoading, setCheckoutsLoading] = useState(false)
  const [indieBorrowsLoading, setIndieBorrowsLoading] = useState(false)
  const [holdsLoading, setHoldsLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [favoritesLoading, setFavoritesLoading] = useState(false)
  const [listsLoading, setListsLoading] = useState(false)
  const [eventsLoading, setEventsLoading] = useState(false)
  const [renewingId, setRenewingId] = useState<number | null>(null)
  const [returningBorrowId, setReturningBorrowId] = useState<number | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [removingFavId, setRemovingFavId] = useState<number | null>(null)
  const [deletingListId, setDeletingListId] = useState<number | null>(null)
  const [creatingList, setCreatingList] = useState(false)

  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences | null>(null)
  const [notifLoading, setNotifLoading] = useState(false)
  const [notifSaving, setNotifSaving] = useState(false)

  const sessionsHook = useSessions(token)
  const passwordHook = usePasswordChange(token)

  const { data: onboardingStatus } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: () => patronOnboardingApi.getStatus(),
    enabled: isAuthenticated && !!user?.onboarding_completed_at,
  })

  const fetchCheckouts = useCallback(async () => {
    if (!token) return
    setCheckoutsLoading(true)
    try {
      const data = await getMyCheckouts(token)
      setCheckouts(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadCheckouts'))
    } finally {
      setCheckoutsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchIndieBorrows = useCallback(async () => {
    setIndieBorrowsLoading(true)
    try {
      const data = await getActiveBorrows()
      setIndieBorrows(data)
      setIndieBorrowError(false)
    } catch {
      // Non-critical — inline message instead of toast
      setIndieBorrowError(true)
    } finally {
      setIndieBorrowsLoading(false)
    }
  }, [])

  const fetchMetislibCheckouts = useCallback(async () => {
    try {
      const data = await getMyMetisLibCheckouts()
      setMetislibCheckouts(data)
    } catch {
      // Non-critical — MetisLib may be unavailable
    }
  }, [])

  const fetchHolds = useCallback(async () => {
    if (!token) return
    setHoldsLoading(true)
    try {
      const data = await getMyHolds(token)
      setHolds(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadHolds'))
    } finally {
      setHoldsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchHistory = useCallback(async () => {
    if (!token) return
    setHistoryLoading(true)
    try {
      const data = await getMyHistory(token)
      setHistory(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadHistory'))
    } finally {
      setHistoryLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchFavorites = useCallback(async () => {
    if (!token) return
    setFavoritesLoading(true)
    try {
      const data = await getMyFavorites(token)
      setFavorites(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadFavorites'))
    } finally {
      setFavoritesLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchLists = useCallback(async () => {
    if (!token) return
    setListsLoading(true)
    try {
      const data = await getMyLists(token)
      setLists(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadLists'))
    } finally {
      setListsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchFines = useCallback(async () => {
    if (!token) return
    try {
      const data = await getMyFinesSummary(token)
      setFinesSummary(data)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }, [token])

  const fetchEvents = useCallback(async () => {
    // Gate on isAuthenticated, not token. fetchApi handles its own auth (cookie
    // + 401-refresh-retry), and React-state `token` can be briefly null during
    // rotation right after another auth'd call — which would silently skip the
    // refetch and leave a cancelled registration visible.
    if (!isAuthenticated) return
    setEventsLoading(true)
    try {
      const data = await getMyEventRegistrations()
      setMyEvents(data)
    } catch (_err) {
      toast.error(t('account.failedToLoadEventRegistrations'))
    } finally {
      setEventsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  const loadNotificationPrefs = useCallback(async () => {
    if (!token) return
    setNotifLoading(true)
    try {
      const prefs = await getNotificationPreferences(token)
      setNotifPrefs(prefs)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setNotifLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchCheckouts()
      fetchIndieBorrows()
      fetchMetislibCheckouts()
      fetchHolds()
      fetchFines()
      fetchEvents()
      fetchApi('/ebook-access-cards/my-card')
        .catch(() => {})
    }
  }, [isAuthenticated, token, fetchCheckouts, fetchIndieBorrows, fetchMetislibCheckouts, fetchHolds, fetchFines, fetchEvents])


  useEffect(() => {
    window.scrollTo(0, 0)
    const main = document.getElementById('main-content')
    if (main) main.scrollTop = 0
  }, [activeTab])
  useEffect(() => {
    if (isAuthenticated && token && activeTab === 'favorites') {
      fetchFavorites()
    }
  }, [isAuthenticated, token, activeTab, fetchFavorites])

  useEffect(() => {
    if (isAuthenticated && token && activeTab === 'lists') {
      fetchLists()
    }
  }, [isAuthenticated, token, activeTab, fetchLists])

  useEffect(() => {
    if (isAuthenticated && token && activeTab === 'history') {
      fetchHistory()
    }
  }, [isAuthenticated, token, activeTab, fetchHistory])

  useEffect(() => {
    if (activeTab === 'notifications' && isAuthenticated && !notifPrefs) {
      loadNotificationPrefs()
    }
  }, [activeTab, isAuthenticated, notifPrefs, loadNotificationPrefs])

  useEffect(() => {
    if (activeTab === 'security' && isAuthenticated) {
      sessionsHook.refresh()
    }
  }, [activeTab, isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleNotifUpdate = async (field: string, value: boolean | number) => {
    if (!token) return
    setNotifSaving(true)
    try {
      const result = await updateNotificationPreferences(token, { [field]: value })
      setNotifPrefs(result.preferences)
      toast.success(t('account.preferenceUpdated'))
    } catch (_err) {
      toast.error(t('account.failedToUpdatePreference'))
    } finally {
      setNotifSaving(false)
    }
  }

  const handleRenew = async (checkoutId: number) => {
    if (!token) return
    setRenewingId(checkoutId)
    renewalTracker.trackStage('renewal_initiated')
    try {
      await renewCheckout(token, checkoutId)
      renewalTracker.trackStage('renewal_confirmed')
      await fetchCheckouts()
      toast.success(t('account.itemRenewedSuccessfully'))
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('account.failedToRenew')
      toast.error(msg)
    } finally {
      setRenewingId(null)
    }
  }

  const handleReturnBorrow = async (borrowId: number) => {
    setReturningBorrowId(borrowId)
    try {
      await returnEbook(borrowId)
      toast.success(t('account.ebookReturnedSuccessfully'))
      await fetchIndieBorrows()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('account.failedToReturnEbook'))
    } finally {
      setReturningBorrowId(null)
    }
  }

  const handleRefreshAll = () => {
    fetchCheckouts()
    fetchIndieBorrows()
    fetchMetislibCheckouts()
  }

  const unifiedCheckouts: UnifiedCheckoutItem[] = [
    ...checkouts.map((c): UnifiedCheckoutItem => ({ type: 'library', data: c })),
    ...indieBorrows.map((b): UnifiedCheckoutItem => ({ type: 'indie', data: b })),
    ...metislibCheckouts.filter(c => c.status === 'active').map((c): UnifiedCheckoutItem => ({ type: 'metislib', data: c })),
  ].sort((a, b) => {
    const dateA = a.type === 'library' ? a.data.due_date : a.type === 'indie' ? a.data.due_at : (a.data.expires_at ?? '')
    const dateB = b.type === 'library' ? b.data.due_date : b.type === 'indie' ? b.data.due_at : (b.data.expires_at ?? '')
    return new Date(dateA).getTime() - new Date(dateB).getTime()
  })

  const handleCancelHold = async (holdId: number) => {
    if (!token) return
    setCancellingId(holdId)
    try {
      await cancelHold(token, holdId)
      toast.success(t('account.holdCancelledSuccessfully'))
      await fetchHolds()
    } catch (_err) {
      toast.error(t('account.failedToCancelHold2'))
    } finally {
      setCancellingId(null)
    }
  }

  const handleRemoveFavorite = async (catalogItemId: number) => {
    if (!token) return
    setRemovingFavId(catalogItemId)
    try {
      await removeFavorite(token, catalogItemId)
      toast.success(t('account.removedFromFavorites'))
      await fetchFavorites()
    } catch (_err) {
      toast.error(t('account.failedToRemoveFavorite2'))
    } finally {
      setRemovingFavId(null)
    }
  }

  const handleDeleteList = async (listId: number) => {
    if (!token) return
    setDeletingListId(listId)
    try {
      await deleteList(token, listId)
      toast.success(t('account.listDeleted'), { duration: 5000 })
      await fetchLists()
    } catch (_err) {
      toast.error(t('account.failedToDeleteList'))
    } finally {
      setDeletingListId(null)
    }
  }

  const handleCreateList = async (name: string, description?: string): Promise<ReadingList | null> => {
    if (!token) return null
    setCreatingList(true)
    try {
      const newList = await createList(token, name, description)
      toast.success(t('account.listCreated'))
      await fetchLists()
      return newList
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('account.failedToCreateList'))
      return null
    } finally {
      setCreatingList(false)
    }
  }

  const handleGetList = async (listId: number): Promise<ReadingListWithItems | null> => {
    if (!token) return null
    try {
      return await getList(token, listId)
    } catch (_err) {
      toast.error(t('account.failedToLoadList'))
      return null
    }
  }

  const handleRemoveItemFromList = async (listId: number, catalogItemId: number): Promise<boolean> => {
    if (!token) return false
    try {
      await removeFromList(token, listId, catalogItemId)
      toast.success(t('account.itemRemovedFromList'))
      return true
    } catch (_err) {
      toast.error(t('account.failedToRemoveItem'))
      return false
    }
  }

  const handleUpdateListPrivacy = async (listId: number, isPublic: boolean): Promise<ReadingList | null> => {
    if (!token) return null
    try {
      const updated = await updateListPrivacy(token, listId, isPublic)
      toast.success(isPublic ? t('account.listMadePublic') : t('account.listMadePrivate'))
      setLists(prev => prev.map(l => l.id === listId ? { ...l, is_public: isPublic } : l))
      return updated
    } catch (_err) {
      toast.error(t('account.failedToUpdateListPrivacy'))
      return null
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
      toast.success(t('account.loggedOutSuccess'))
    } catch (_err) {
      toast.error(t('account.logoutFailed'))
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const isOverdue = (dueDate: string) => {
    return new Date(dueDate) < new Date()
  }

  const overdueCount = checkouts.filter(c => isOverdue(c.due_date)).length
  const holdsReadyCount = holds.filter(h => h.status === 'ready').length
  const dueSoonCount = checkouts.filter(c => {
    const due = new Date(c.due_date)
    const now = new Date()
    const threeDays = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000)
    return due > now && due <= threeDays
  }).length

  type NavItem = {
    id: AccountTab
    label: string
    icon: React.ElementType
    badge?: number | undefined
    alert?: boolean | undefined
    dot?: boolean | undefined
    flag?: keyof OrganizationFeatures
  }
  type NavSection = { label: string; items: NavItem[] }

  const rawNavSections: NavSection[] = [
    {
      label: t('account.navMyLibrary'),
      items: [
        { id: 'overview' as const, label: t('account.tabOverview'), icon: User },
        { id: 'checkouts' as const, label: t('account.tabCheckouts'), icon: Book, badge: checkouts.length + indieBorrows.length + metislibCheckouts.filter(c => c.status === 'active').length || undefined, alert: overdueCount > 0 },
        { id: 'ebooks' as const, label: t('account.tabEbooks'), icon: BookMarked, badge: indieBorrows.length || undefined, flag: TAB_FLAGS['ebooks'] },
        { id: 'holds' as const, label: t('account.tabHolds'), icon: Clock, badge: holds.length || undefined, dot: holdsReadyCount > 0 },
        { id: 'events' as const, label: t('account.tabEvents'), icon: Calendar, badge: myEvents.length || undefined, flag: TAB_FLAGS['events'] },
        { id: 'family' as const, label: t('account.tabFamily'), icon: Users, flag: TAB_FLAGS['family'] },
        { id: 'volunteer' as const, label: t('account.tabVolunteer'), icon: HandHeart, flag: TAB_FLAGS['volunteer'] },
      ],
    },
    {
      label: t('account.navCollections'),
      items: [
        { id: 'favorites' as const, label: t('account.tabFavorites'), icon: Heart, badge: favorites.length || undefined },
        { id: 'lists' as const, label: t('account.tabLists'), icon: List, badge: lists.length || undefined },
        { id: 'history' as const, label: t('account.tabHistory'), icon: History },
      ],
    },
    {
      label: t('account.navAccount'),
      items: [
        { id: 'my-data' as const, label: t('account.tabMyData', 'My Data'), icon: Database },
        { id: 'settings' as const, label: t('account.tabSettings'), icon: Settings },
        { id: 'notifications' as const, label: t('account.tabNotifications'), icon: Bell, flag: TAB_FLAGS['notifications'] },
        { id: 'security' as const, label: t('account.tabSecurity'), icon: Shield },
        ...(user?.indie_author ? [{ id: 'author-dashboard' as const, label: t('account.tabAuthorDashboard'), icon: BookMarked, flag: TAB_FLAGS['author-dashboard'] }] : []),
      ],
    },
  ]

  const navSections: NavSection[] = rawNavSections
    .map(section => ({
      ...section,
      items: section.items.filter(item => !item.flag || isFeatureEnabled(item.flag as Parameters<typeof isFeatureEnabled>[0])),
    }))
    // Drop sections whose every item was flag-culled. Today no section is
    // exclusively flag-gated, but this keeps the cascade safe if one is added.
    .filter(section => section.items.length > 0)

  useEffect(() => {
    const visibleIds = new Set(navSections.flatMap(s => s.items.map(i => i.id)))
    if (!visibleIds.has(activeTab)) {
      setActiveTab('overview')
      setSearchParams({ tab: 'overview' }, { replace: true })
    }
  }, [navSections, activeTab, setSearchParams])

  const initials = user ? `${(user.first_name || '')[0] || ''}${(user.last_name || '')[0] || ''}`.toUpperCase() : '?'

  // Guards kept below all hooks so hook order stays stable across renders.
  if (isLoading) {
    return (
      <div className="min-h-screen bg-cream dark:bg-lsc-dark flex items-center justify-center" role="status">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        <span className="sr-only">{t('account.loadingAccount')}</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <AuthForm />
  }

  return (
    <div className="min-h-screen bg-cream dark:bg-lsc-dark">
      <PageContainer className="py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('account.myAccount')}</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream mt-1">{t('account.welcomeBack', { name: user?.first_name ?? '' })}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
          >
            <LogOut className="w-5 h-5" />
            {t('account.signOut')}
          </button>
        </div>

        <TemporaryCardBanner />

        {/* Mobile horizontal pill nav */}
        <div className="lg:hidden mb-4 relative">
          <nav className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide -mx-4 px-4" aria-label={t('account.navAccount')}>
            {navSections.flatMap(s => s.items).map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center gap-2 px-3 py-2 rounded-full text-sm whitespace-nowrap flex-shrink-0 transition-colors ${
                    isActive
                      ? 'bg-lsc-rose/10 dark:bg-lsc-rose/15 text-lsc-rose font-semibold'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/80 shadow-sm'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{tab.label}</span>
                  {'badge' in tab && tab.badge != null && (
                    <span className={`text-xs font-semibold min-w-4 h-4 px-1 rounded-full flex items-center justify-center ${
                      'alert' in tab && tab.alert
                        ? 'bg-status-danger-600 text-white'
                        : isActive
                          ? 'bg-lsc-rose text-white'
                          : 'bg-lsc-dark/[.08] dark:bg-lsc-cream/10'
                    }`}>
                      {tab.badge}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-cream dark:from-lsc-dark to-transparent"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Desktop sidebar nav */}
          <div className="hidden lg:block lg:col-span-1">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md overflow-hidden sticky top-4">
              {/* Patron summary */}
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center gap-3">
                <div className="w-11 h-11 bg-lsc-rose/10 dark:bg-lsc-rose/15 rounded-xl flex items-center justify-center text-lsc-rose font-bold flex-shrink-0">
                  {initials}
                </div>
                <div>
                  <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{user?.first_name} {user?.last_name}</p>
                  {user?.library_card && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{t('account.cardLabel', { num: user.library_card })}</p>}
                  {(dueSoonCount > 0 || overdueCount > 0) && (
                    <p className="text-xs font-semibold mt-0.5 flex items-center gap-1">
                      {overdueCount > 0 ? (
                        <span className="text-status-danger-600 dark:text-status-danger-400 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          {t('account.itemsOverdue', { count: overdueCount })}
                        </span>
                      ) : (
                        <span className="text-lsc-rose flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {t('account.itemsDueSoon', { count: dueSoonCount })}
                        </span>
                      )}
                    </p>
                  )}
                </div>
              </div>

              {/* Grouped navigation */}
              <nav className="p-2" aria-label={t('account.navAccount')}>
                {navSections.map((section, si) => (
                  <div key={section.label} className={si > 0 ? 'mt-1 pt-1 border-t border-lsc-border/50 dark:border-earth-700/50' : ''}>
                    <p className="px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/40">
                      {section.label}
                    </p>
                    {section.items.map((tab) => {
                      const Icon = tab.icon
                      const isActive = activeTab === tab.id
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          aria-current={isActive ? 'page' : undefined}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${
                            isActive
                              ? 'bg-lsc-rose/10 dark:bg-lsc-rose/15 text-lsc-rose font-semibold'
                              : 'text-lsc-dark/70 dark:text-lsc-cream/80 hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 hover:text-lsc-dark dark:hover:text-lsc-cream'
                          }`}
                        >
                          <Icon className="w-5 h-5 flex-shrink-0" />
                          <span className="flex-1 text-left">{tab.label}</span>
                          {'badge' in tab && tab.badge != null && (
                            <span className={`text-xs font-semibold min-w-5 h-5 px-1.5 rounded-full flex items-center justify-center ${
                              'alert' in tab && tab.alert
                                ? 'bg-status-danger-600 text-white'
                                : isActive
                                  ? 'bg-lsc-rose text-white'
                                  : 'bg-lsc-dark/[.08] dark:bg-lsc-cream/10 text-lsc-dark/70 dark:text-lsc-cream/60'
                            }`}>
                              {tab.badge}
                            </span>
                          )}
                          {'alert' in tab && tab.alert && <span className="w-1.5 h-1.5 rounded-full bg-status-danger-600 flex-shrink-0" role="status" aria-label={t('account.ariaCheckoutsOverdue', { count: overdueCount })} />}
                          {'dot' in tab && tab.dot && <span className="w-1.5 h-1.5 rounded-full bg-lsc-rose flex-shrink-0" role="status" aria-label={t('account.ariaHoldsReady', { count: holdsReadyCount })} />}
                        </button>
                      )
                    })}
                  </div>
                ))}
              </nav>
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md p-6">
              {activeTab === 'overview' && (
                <>
                <OverviewTab
                  user={user!}
                  checkouts={checkouts}
                  indieBorrows={indieBorrows}
                  holds={holds}
                  finesSummary={finesSummary}
                  myEvents={myEvents}
                  unifiedCheckouts={unifiedCheckouts}
                  checkoutsLoading={checkoutsLoading}
                  indieBorrowsLoading={indieBorrowsLoading}
                  holdsLoading={holdsLoading}
                  eventsLoading={eventsLoading}
                  {...(onboardingStatus ? { onboardingStatus } : {})}
                  onSetTab={(tab) => setActiveTab(tab as AccountTab)}
                  formatDate={formatDate}
                  isOverdue={isOverdue}
                  onRenew={handleRenew}
                  renewingId={renewingId}
                />
                  {finesSummary.outstanding_count > 0 && (
                    <div className="mt-6">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('account.fines')}</h3>
                      <FinesReviewSection />
                    </div>
                  )}
                </>
              )}

              {activeTab === 'checkouts' && (
                <>
                {indieBorrowError && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-status-warning-500 flex-shrink-0" />
                    Some ebook data couldn&apos;t be loaded. Library checkouts are still shown below.
                  </p>
                )}
                <CheckoutsTab
                  unifiedCheckouts={unifiedCheckouts}
                  checkoutsLoading={checkoutsLoading}
                  indieBorrowsLoading={indieBorrowsLoading}
                  renewingId={renewingId}
                  returningBorrowId={returningBorrowId}
                  onRefresh={handleRefreshAll}
                  onRenew={handleRenew}
                  onReturnBorrow={handleReturnBorrow}
                  formatDate={formatDate}
                  isOverdue={isOverdue}
                />
                </>
              )}

              {activeTab === 'ebooks' && (
                <Suspense fallback={
                  <div className="flex justify-center py-12" role="status" aria-live="polite">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                    <span className="sr-only">{t('account.loadingEbooks', 'Loading eBooks…')}</span>
                  </div>
                }>
                  <MyBooksPage embedded />
                </Suspense>
              )}

              {activeTab === 'holds' && (
                <HoldsTab
                  holds={holds}
                  holdsLoading={holdsLoading}
                  cancellingId={cancellingId}
                  onRefresh={fetchHolds}
                  onCancel={handleCancelHold}
                  formatDate={formatDate}
                />
              )}

              {activeTab === 'events' && (
                <EventsTab
                  events={myEvents}
                  eventsLoading={eventsLoading}
                  onRefresh={fetchEvents}
                  onCancelled={(registrationId) =>
                    setMyEvents((prev) => prev.filter((r) => r.id !== registrationId))
                  }
                />
              )}

              {activeTab === 'family' && <FamilyOverview />}

              {activeTab === 'favorites' && (
                favoritesLoading && favorites.length === 0 ? (
                  <div className="flex justify-center py-12" role="status" aria-live="polite">
                    <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                    <span className="sr-only">{t('account.loadingFavorites', 'Loading favorites...')}</span>
                  </div>
                ) : (
                  <FavoritesTab
                    favorites={favorites}
                    favoritesLoading={favoritesLoading}
                    removingFavId={removingFavId}
                    onRefresh={fetchFavorites}
                    onRemove={handleRemoveFavorite}
                    formatDate={formatDate}
                  />
                )
              )}

              {activeTab === 'lists' && (
                <ListsSection
                  lists={lists}
                  loading={listsLoading}
                  creating={creatingList}
                  deletingId={deletingListId}
                  onRefresh={fetchLists}
                  onCreate={handleCreateList}
                  onDelete={handleDeleteList}
                  onGetList={handleGetList}
                  onRemoveItem={handleRemoveItemFromList}
                  onUpdatePrivacy={handleUpdateListPrivacy}
                />
              )}

              {activeTab === 'history' && (
                historyLoading && history.length === 0 ? (
                  <div className="flex justify-center py-12" role="status" aria-live="polite">
                    <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                    <span className="sr-only">{t('account.loadingHistory', 'Loading history...')}</span>
                  </div>
                ) : (
                  <HistoryTab
                    history={history}
                    historyLoading={historyLoading}
                    onRefresh={fetchHistory}
                    formatDate={formatDate}
                    onSetTab={(tab) => setActiveTab(tab as AccountTab)}
                  />
                )
              )}

              {activeTab === 'my-data' && <MyDataTab />}

              {activeTab === 'settings' && <SettingsTab />}

              {activeTab === 'notifications' && (
                <NotificationsSection
                  preferences={notifPrefs}
                  loading={notifLoading}
                  saving={notifSaving}
                  onUpdate={handleNotifUpdate}
                />
              )}

              {activeTab === 'security' && (
                <SecuritySection
                  sessions={sessionsHook.sessions}
                  sessionsLoading={sessionsHook.loading}
                  revokingSessionId={sessionsHook.revokingId}
                  onSessionRefresh={sessionsHook.refresh}
                  onRevokeSession={sessionsHook.revoke}
                  onRevokeAllOtherSessions={sessionsHook.revokeAllOthers}
                  isRevokingAllSessions={sessionsHook.revokingAll}
                  onChangePassword={async (current, newPw, confirm) => {
                    return await passwordHook.change({ currentPassword: current, newPassword: newPw, confirmPassword: confirm })
                  }}
                  isChangingPassword={passwordHook.isChanging}
                />
              )}

              {activeTab === 'volunteer' && (
                <Suspense fallback={
                  <div className="flex justify-center py-12" role="status" aria-live="polite">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                    <span className="sr-only">{t('account.loadingVolunteerDashboard', 'Loading volunteer dashboard…')}</span>
                  </div>
                }>
                  <VolunteerDashboard />
                </Suspense>
              )}

              {activeTab === 'author-dashboard' && user?.indie_author && (
                <div>
                  <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">{t('account.authorDashboard')}</h2>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/80 mb-6">{t('account.authorDashboardDesc')}</p>
                  <Link
                    to="/indie/dashboard"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                  >
                    <BookMarked className="w-5 h-5" />
                    {t('account.goToAuthorDashboard')}
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </PageContainer>
    </div>
  )
}
