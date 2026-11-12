/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { API_BASE } from '@/api/types'
import {
  Bell, CheckCheck, Loader2, List, Eye, Rows2, Rows3,
  Settings, Trash2, Undo2
} from 'lucide-react'
import { NOTIFICATIONS_CHANGED_EVENT } from '../components/notifications/notifications-data'
import { useAuth } from '../contexts/AuthContext'
import api from '../api/api'
import toast from 'react-hot-toast'
import { clsx } from '../utils/helpers'
import { EMPTY_STATE_KEYS } from '../constants/brandMessages'
import { Button } from '@/components/ui/Button'
import { useTranslation } from '@/i18n'
import { NotificationsFiltersBar } from '../components/notifications/NotificationsFiltersBar'
import { FocusModeView } from '../components/notifications/FocusModeView'
import { NotificationListItem } from '../components/notifications/NotificationListItem'
import { KeyboardShortcutsHelp } from '../components/notifications/KeyboardShortcutsHelp'
import { groupNotificationsByDate } from '../components/notifications/notifications-data'
import ConfirmDialog from '../components/ConfirmDialog'
import type { Notification, ViewDensity, ViewMode, TypeFilter, ReadFilter } from '../components/notifications/notifications-data'
import { usePersistedState } from '@/hooks/usePersistedState'

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 10) return 'Updated just now'
  if (seconds < 60) return `Updated ${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `Updated ${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  return `Updated ${hours}h ago`
}

export default function NotificationsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [readFilter, setReadFilter] = useState<ReadFilter>('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [processingIds, setProcessingIds] = useState<Set<number | string>>(new Set())
  const [markingAllRead, setMarkingAllRead] = useState(false)
  const [showMarkAllConfirm, setShowMarkAllConfirm] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<number | null>(null)
  const [, setRefreshTick] = useState(0)
  const [liveMessage, setLiveMessage] = useState('')
  const perPage = 20

  const [viewDensity, setViewDensity] = usePersistedState<ViewDensity>('notifications-density', 'comfortable')
  const [viewMode, setViewMode] = usePersistedState<ViewMode>('notifications-view-mode', 'list')
  const [focusIndex, setFocusIndex] = useState(0)
  const [deletedNotification, setDeletedNotification] = useState<Notification | null>(null)
  const undoTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const viewToggleRef = useRef<HTMLDivElement | null>(null)
  const focusCardRef = useRef<HTMLDivElement | null>(null)

  // Re-render the "Updated Xs ago" label once a minute so it stays roughly
  // truthful between polls. This only ticks the label; the real refetch is
  // the poll below.
  useEffect(() => {
    const interval = setInterval(() => setRefreshTick(t => t + 1), 30000)
    return () => clearInterval(interval)
  }, [])

  // `background: true` is used by the poll and visibility-resume refresh: it
  // skips the loading skeleton and the error toast so a routine refetch never
  // blanks the list or nags the patron.
  const fetchNotifications = useCallback(async ({ background = false }: { background?: boolean } = {}) => {
    if (!background) setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('limit', perPage.toString())
      params.append('offset', ((page - 1) * perPage).toString())

      // The live feed exposes a single `category` filter; map it directly.
      if (typeFilter !== 'all') {
        params.append('category', typeFilter)
      }

      // The live feed only supports `unread_only`; there is no read-only
      // server filter, so the "read" case is narrowed client-side below.
      if (readFilter === 'unread') {
        params.append('unread_only', 'true')
      }

      const data = await api.get(`${API_BASE}/notifications/live?${params.toString()}`)
      let items: Notification[] = data.items || []
      if (readFilter === 'read') {
        items = items.filter(n => n.is_read)
      }
      setNotifications(items)
      const total = typeof data.total === 'number' ? data.total : items.length
      setTotalCount(total)
      setTotalPages(Math.max(1, Math.ceil(total / perPage)))
      setLastRefreshed(Date.now())
      // Announce the result count for foreground fetches (filter changes,
      // the Refresh button). Background polls stay silent to avoid noise.
      if (!background) {
        setLiveMessage(
          `${total === 1 ? '1 notification' : `${total} notifications`}.`
        )
      }
    } catch {
      if (!background) {
        toast.error(t('notifications.failedToLoadNotifications'))
        setNotifications([])
      }
    } finally {
      if (!background) setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, typeFilter, readFilter])

  // Keep a ref to the latest fetch so the poll effect below doesn't tear down
  // and restart its timer on every filter change.
  const fetchRef = useRef(fetchNotifications)
  useEffect(() => {
    fetchRef.current = fetchNotifications
  }, [fetchNotifications])

  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications()
    }
  }, [isAuthenticated, fetchNotifications])

  // Real 60s background poll (matches the bell dropdown's cadence), paused
  // while the tab is hidden so it stays calm and cheap.
  useEffect(() => {
    if (!isAuthenticated) return

    let interval: ReturnType<typeof setInterval> | null = null

    const start = () => {
      if (interval) return
      interval = setInterval(() => fetchRef.current({ background: true }), 60000)
    }
    const stop = () => {
      if (interval) {
        clearInterval(interval)
        interval = null
      }
    }

    const handleVisibility = () => {
      if (document.hidden) {
        stop()
      } else {
        fetchRef.current({ background: true })
        start()
      }
    }

    if (!document.hidden) start()
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [isAuthenticated])

  useEffect(() => {
    setPage(1)
  }, [typeFilter, readFilter])

  const handleMarkAsRead = async (notification: Notification) => {
    // The live feed only supports marking read (one-way); already-read
    // notifications cannot be toggled back to unread.
    if (notification.is_read) return
    setProcessingIds(prev => new Set(prev).add(notification.id))
    try {
      await api.post(`${API_BASE}/notifications/live/${notification.id}/read`)
      setNotifications(prev =>
        prev.map(n => (n.id === notification.id ? { ...n, is_read: true } : n))
      )
      window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED_EVENT))
      toast.success(t('toast.notifications.markedAsRead'))
    } catch {
      toast.error(t('notifications.failedToUpdateNotification'))
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(notification.id)
        return next
      })
    }
  }

  const handleDelete = async (notification: Notification) => {
    if (undoTimeoutRef.current) {
      clearTimeout(undoTimeoutRef.current)
    }

    setProcessingIds(prev => new Set(prev).add(notification.id))
    try {
      await api.delete(`${API_BASE}/notifications/live/${notification.id}`)
      setNotifications(prev => prev.filter(n => n.id !== notification.id))
      setTotalCount(prev => prev - 1)
      setDeletedNotification(notification)
      window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED_EVENT))

      undoTimeoutRef.current = setTimeout(() => {
        setDeletedNotification(null)
      }, 12000)

      // Plain string so react-hot-toast keeps its default role="status".
      toast.success('Notification deleted', { duration: 5000 })
    } catch {
      toast.error(t('notifications.failedToDeleteNotification'))
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(notification.id)
        return next
      })
    }
  }

  const handleUndoDelete = async () => {
    if (!deletedNotification) return

    if (undoTimeoutRef.current) {
      clearTimeout(undoTimeoutRef.current)
    }

    // The live feed has no un-dismiss endpoint, so undo is a local-only
    // restore; a refresh will reconcile against the server.
    setNotifications(prev => {
      const restored = [...prev, deletedNotification]
      return restored.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    })
    setTotalCount(prev => prev + 1)
    setDeletedNotification(null)
    window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED_EVENT))
    toast.success(t('toast.notifications.notificationRestored'))
  }

  useEffect(() => {
    return () => {
      if (undoTimeoutRef.current) {
        clearTimeout(undoTimeoutRef.current)
      }
    }
  }, [])

  const handleMarkAllRead = async () => {
    setMarkingAllRead(true)
    try {
      await api.post(`${API_BASE}/notifications/live/read-all`)
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED_EVENT))
      toast.success(t('notifications.allNotificationsMarkedAsRead'))
    } catch {
      toast.error(t('notifications.failedToMarkAllAs'))
    } finally {
      setMarkingAllRead(false)
    }
  }

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.is_read) {
      handleMarkAsRead(notification)
    }

    const target = notification.link_url || notification.action_url
    if (target) {
      if (/^https?:\/\//i.test(target)) {
        window.location.href = target
      } else {
        navigate(target)
      }
    }
  }

  const handleFocusNavigation = (direction: 'prev' | 'next') => {
    if (direction === 'next' && focusIndex < notifications.length - 1) {
      setFocusIndex(prev => prev + 1)
    } else if (direction === 'prev' && focusIndex > 0) {
      setFocusIndex(prev => prev - 1)
    }
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip when focus is on any interactive element: the bare `r` refresh
      // key (and the focus-mode keys) must not fire while the patron is using
      // a filter <select> or a button.
      if (
        e.target instanceof Element &&
        e.target.closest('input, textarea, select, button, [contenteditable="true"]')
      ) {
        return
      }

      if (viewMode === 'focus' && notifications.length > 0) {
        const currentNotification = notifications[focusIndex]

        switch (e.key) {
          case 'j':
          case 'ArrowDown':
            e.preventDefault()
            handleFocusNavigation('next')
            break
          case 'k':
          case 'ArrowUp':
            e.preventDefault()
            handleFocusNavigation('prev')
            break
          case 'x':
            if (currentNotification) {
              handleMarkAsRead(currentNotification)
            }
            break
          case 'Enter':
            if (currentNotification) {
              handleNotificationClick(currentNotification)
            }
            break
        }
      }

      if (e.key === 'r' && !e.metaKey && !e.ctrlKey) {
        fetchNotifications()
      }
      if (e.key === 'z' && (e.metaKey || e.ctrlKey) && deletedNotification) {
        e.preventDefault()
        handleUndoDelete()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, focusIndex, notifications, deletedNotification])

  useEffect(() => {
    setFocusIndex(0)
  }, [notifications.length])

  // Move focus into the focused card when entering Focus mode, and return it
  // to the List/Focus toggle when leaving, so keyboard users aren't dropped at
  // the top of the document on each switch.
  const prevViewModeRef = useRef(viewMode)
  useEffect(() => {
    if (prevViewModeRef.current === viewMode) return
    if (viewMode === 'focus') {
      focusCardRef.current?.focus()
    } else {
      viewToggleRef.current?.querySelector('button')?.focus()
    }
    prevViewModeRef.current = viewMode
  }, [viewMode])

  // Announce the undo banner so screen-reader users know a delete can be
  // reversed (announce-only; focus stays where the patron left it).
  useEffect(() => {
    if (deletedNotification) {
      setLiveMessage('Notification deleted. Press the Undo button to restore it.')
    }
  }, [deletedNotification])

  const unreadCount = notifications.filter(n => !n.is_read).length
  const groupedNotifications = groupNotificationsByDate(notifications)

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen py-12 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <Bell className="w-16 h-16 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Sign in to view notifications
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Please sign in to see your library notifications.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto">
        <p className="sr-only" aria-live="polite" aria-atomic="true">
          {liveMessage}
        </p>
        <div className="mb-8">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl flex items-center justify-center">
                <Bell className="w-6 h-6 text-lsc-rose" />
              </div>
              <div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  Notifications
                </h1>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Holds, due dates, fines, and library updates
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div ref={viewToggleRef} className="flex items-center bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-1">
                <Button variant="secondary"
                  onClick={() => setViewMode('list')}
                  aria-pressed={viewMode === 'list'}
                  className={clsx(viewMode === 'list' && 'ring-2 ring-lsc-rose')}
                  aria-label={t('aria.notifications.listView')}
                  title={t('notifications.listViewSeeAllNotifications')}
                >
                  <List className="w-4 h-4" />
                  <span className="hidden sm:inline">List</span>
                </Button>
                <Button variant="secondary"
                  onClick={() => setViewMode('focus')}
                  aria-pressed={viewMode === 'focus'}
                  className={clsx(viewMode === 'focus' && 'ring-2 ring-lsc-rose')}
                  aria-label={t('aria.notifications.focusView')}
                  title={t('notifications.focusViewOneNotificationAt')}
                >
                  <Eye className="w-4 h-4" />
                  <span className="hidden sm:inline">Focus</span>
                </Button>
              </div>

              <Button variant="secondary" size="sm"
                onClick={() => setViewDensity(prev => prev === 'comfortable' ? 'compact' : 'comfortable')}
                aria-pressed={viewDensity === 'compact'}
                className={clsx(viewDensity === 'compact' && 'ring-2 ring-lsc-rose')}
                aria-label={viewDensity === 'comfortable' ? 'Switch to compact view' : 'Switch to comfortable view'}
                title={viewDensity === 'comfortable' ? 'Compact view (less spacing)' : 'Comfortable view (more spacing)'}
              >
                {viewDensity === 'comfortable' ? (
                  <Rows3 className="w-4 h-4" />
                ) : (
                  <Rows2 className="w-4 h-4" />
                )}
              </Button>

              <Link
                to="/account?tab=notifications"
                className="p-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                aria-label={t('aria.notifications.notificationSettings')}
                title="Manage notification preferences"
              >
                <Settings className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {!loading && unreadCount > 0 && (
            <div className="mt-4 p-4 bg-lsc-rose/5 dark:bg-lsc-rose/10 border border-lsc-rose/20 rounded-xl">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-lsc-rose/20 rounded-lg flex items-center justify-center">
                    <span className="text-lg font-bold text-lsc-rose">{unreadCount}</span>
                  </div>
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {unreadCount === 1 ? '1 unread notification' : `${unreadCount} unread notifications`}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {viewMode === 'focus' ? 'Use arrow keys or j/k to navigate' : 'Review at your own pace'}
                    </p>
                  </div>
                </div>
                <Button variant="primary"
                  onClick={() => setShowMarkAllConfirm(true)}
                  disabled={markingAllRead}
                >
                  {markingAllRead ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <CheckCheck className="w-4 h-4" />
                  )}
                  Clear all
                </Button>
              </div>
            </div>
          )}

          {deletedNotification && (
            <div className="mt-4 p-3 bg-earth-100 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <Trash2 className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <span>Notification deleted</span>
              </div>
              <Button variant="secondary"
                onClick={handleUndoDelete}
              >
                <Undo2 className="w-4 h-4" />
                Undo
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">(Ctrl+Z)</span>
              </Button>
            </div>
          )}
        </div>

        <NotificationsFiltersBar
          typeFilter={typeFilter}
          setTypeFilter={setTypeFilter}
          readFilter={readFilter}
          setReadFilter={setReadFilter}
          loading={loading}
          onRefresh={fetchNotifications}
          totalCount={totalCount}
          unreadCount={unreadCount}
        />

        {lastRefreshed && !loading && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mb-3">
            {formatRelativeTime(lastRefreshed)}
          </p>
        )}

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
          {loading ? (
            <div className="divide-y divide-lsc-border dark:divide-earth-700">
              {[1, 2, 3].map((i) => (
                <div key={i} className={clsx('p-4 sm:p-6', viewDensity === 'compact' && 'p-3 sm:p-4')}>
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-lsc-cream dark:bg-earth-700 motion-safe:animate-pulse" />
                    <div className="flex-1 space-y-3">
                      <div className="h-4 bg-lsc-cream dark:bg-earth-700 rounded w-3/4 motion-safe:animate-pulse" />
                      <div className="h-3 bg-lsc-cream dark:bg-earth-700 rounded w-1/2 motion-safe:animate-pulse" />
                      <div className="h-3 bg-lsc-cream dark:bg-earth-700 rounded w-1/4 motion-safe:animate-pulse" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-16 px-4 text-center">
              <Bell className="w-16 h-16 text-lsc-dark/10 dark:text-lsc-cream/10 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                {typeFilter !== 'all' || readFilter !== 'all'
                  ? t(EMPTY_STATE_KEYS.notifications.noNotificationsWithFilters.message)
                  : t(EMPTY_STATE_KEYS.notifications.noNotifications.message)}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 max-w-sm mx-auto leading-relaxed">
                {typeFilter !== 'all' || readFilter !== 'all'
                  ? t(EMPTY_STATE_KEYS.notifications.noNotificationsWithFilters.suggestion)
                  : t(EMPTY_STATE_KEYS.notifications.noNotifications.suggestion)}
              </p>
              {(typeFilter !== 'all' || readFilter !== 'all') && (
                <Button variant="primary"
                  onClick={() => { setTypeFilter('all'); setReadFilter('all'); }}
                >
                  Clear filters
                </Button>
              )}
            </div>
          ) : viewMode === 'focus' ? (
            <FocusModeView
              notifications={notifications}
              focusIndex={focusIndex}
              setFocusIndex={setFocusIndex}
              processingIds={processingIds}
              onMarkAsRead={handleMarkAsRead}
              onDelete={handleDelete}
              onNavigate={handleFocusNavigation}
              onNotificationClick={handleNotificationClick}
              cardRef={focusCardRef}
            />
          ) : (
            <div>
              {Array.from(groupedNotifications.entries()).map(([dateGroup, groupNotifications]) => (
                <div key={dateGroup}>
                  <div className="px-4 sm:px-6 py-3 bg-lsc-cream/50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                    <h2 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                      {dateGroup}
                      <span className="ml-2 font-normal text-lsc-dark/70 dark:text-lsc-cream/70">
                        ({groupNotifications.length})
                      </span>
                    </h2>
                  </div>

                  <ul role="list" className="divide-y divide-lsc-border dark:divide-earth-700">
                    {groupNotifications.map((notification) => (
                      <NotificationListItem
                        key={notification.id}
                        notification={notification}
                        viewDensity={viewDensity}
                        isProcessing={processingIds.has(notification.id)}
                        onMarkAsRead={handleMarkAsRead}
                        onDelete={handleDelete}
                        onNotificationClick={handleNotificationClick}
                      />
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && viewMode === 'list' && (
            <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-t border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-800/50">
              <Button variant="secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1 || loading}
              >
                Previous
              </Button>

              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Page {page} of {totalPages}
              </span>

              <Button variant="secondary"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || loading}
              >
                Next
              </Button>
            </div>
          )}
        </div>

        <KeyboardShortcutsHelp />

        <p className="mt-4 text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/70">
          Use Focus mode for a calmer, one-at-a-time view. Your preferences are saved automatically.
        </p>
      </div>

      <ConfirmDialog
        isOpen={showMarkAllConfirm}
        title="Mark all as read"
        message="This will mark all unread notifications as read. You won't be able to undo this."
        confirmText="Mark all read"
        confirmVariant="warning"
        onConfirm={() => {
          setShowMarkAllConfirm(false)
          handleMarkAllRead()
        }}
        onCancel={() => setShowMarkAllConfirm(false)}
        loading={markingAllRead}
      />
    </div>
  )
}
