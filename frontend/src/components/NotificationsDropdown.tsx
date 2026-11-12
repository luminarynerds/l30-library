/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import {
  Bell, AlertTriangle, Clock, Award, TrendingUp, MessageCircle,
  CheckCheck, ExternalLink, Loader2, ShieldAlert, AlertCircle,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import api from '../api/api'
import { t } from '@/i18n'
import { NOTIFICATIONS_CHANGED_EVENT } from './notifications/notifications-data'

const notificationConfig: Record<string, { icon: React.ElementType; colorClass: string; bgClass: string }> = {
  panic_alert: {
    icon: ShieldAlert,
    colorClass: 'text-status-danger-600 dark:text-status-danger-400',
    bgClass: 'bg-status-danger-100 dark:bg-status-danger-900/40',
  },
  goal_risk: {
    icon: AlertTriangle,
    colorClass: 'text-status-warning-600 dark:text-status-warning-400',
    bgClass: 'bg-status-warning-100 dark:bg-status-warning-900/30',
  },
  deadline: {
    icon: Clock,
    colorClass: 'text-status-warning-600 dark:text-status-warning-400',
    bgClass: 'bg-status-warning-100 dark:bg-status-warning-900/30',
  },
  milestone: {
    icon: Award,
    colorClass: 'text-status-success-600 dark:text-status-success-400',
    bgClass: 'bg-status-success-100 dark:bg-status-success-900/30',
  },
  progress: {
    icon: TrendingUp,
    colorClass: 'text-lsc-rose dark:text-lsc-rose-light',
    bgClass: 'bg-earth-100 dark:bg-earth-800/30',
  },
  comment: {
    icon: MessageCircle,
    colorClass: 'text-category-600 dark:text-category-400',
    bgClass: 'bg-category-100 dark:bg-category-900/30',
  },
}

export interface Notification {
  id: number | string
  type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
  link_url?: string
  action_url?: string
  related_goal_id?: number
  related_milestone_id?: number
}

interface NotificationsDropdownProps {
  className?: string
  variant?: 'desktop' | 'mobile'
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return t('notificationsDropdown.justNow')
  if (diffInSeconds < 3600) return t('notificationsDropdown.minutesAgo', { count: Math.floor(diffInSeconds / 60) })
  if (diffInSeconds < 86400) return t('notificationsDropdown.hoursAgo', { count: Math.floor(diffInSeconds / 3600) })
  if (diffInSeconds < 604800) return t('notificationsDropdown.daysAgo', { count: Math.floor(diffInSeconds / 86400) })
  return date.toLocaleDateString()
}

function getNotificationIcon(type: string): { icon: React.ElementType; colorClass: string; bgClass: string } {
  return notificationConfig[type] ?? notificationConfig['progress']!
}

export default function NotificationsDropdown({ className, variant }: NotificationsDropdownProps): React.ReactElement {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [markingAllRead, setMarkingAllRead] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/notifications/live/unread-count').catch(() => ({ unread_count: 0 }))
      setUnreadCount(data.unread_count || 0)
    } catch {
      // Silent: user may not have access
    }
  }, [])

  const fetchNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get('/api/v1/notifications/live?limit=10')
      setNotifications(data.items || data.notifications || data || [])
    } catch {
      setError(t('notificationsDropdown.fetchError') || 'Failed to load notifications')
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (variant === 'mobile') return
    fetchUnreadCount()
    const interval = setInterval(fetchUnreadCount, 60000)
    // Refresh the badge immediately when the notifications page reports a
    // read-state change, instead of waiting up to 60s for the next poll.
    window.addEventListener(NOTIFICATIONS_CHANGED_EVENT, fetchUnreadCount)
    return () => {
      clearInterval(interval)
      window.removeEventListener(NOTIFICATIONS_CHANGED_EVENT, fetchUnreadCount)
    }
  }, [fetchUnreadCount, variant])

  useEffect(() => {
    if (open) {
      fetchNotifications()
    }
  }, [open, fetchNotifications])

  const handleMarkAllRead = useCallback(async () => {
    setMarkingAllRead(true)
    try {
      await api.post('/api/v1/notifications/live/read-all')
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch {
      // handle silently
    } finally {
      setMarkingAllRead(false)
    }
  }, [])

  const handleNotificationClick = useCallback(async (notification: Notification) => {
    if (!notification.is_read) {
      try {
        await api.post(`/api/v1/notifications/live/${notification.id}/read`)
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n)),
        )
        setUnreadCount((prev) => Math.max(0, prev - 1))
      } catch {
        // Continue with navigation even if marking fails
      }
    }

    setOpen(false)

    const target = notification.link_url || notification.action_url
    if (target) {
      if (/^https?:\/\//i.test(target)) {
        window.location.href = target
      } else {
        navigate(target)
      }
    } else if (notification.related_goal_id) {
      navigate(`/strategic-plan?goal=${notification.related_goal_id}`)
    } else if (notification.related_milestone_id) {
      navigate(`/strategic-plan?milestone=${notification.related_milestone_id}`)
    }
  }, [navigate])

  return (
    <div className={clsx(
      variant === 'desktop' && 'hidden lg:block',
      variant === 'mobile' && 'lg:hidden',
      className,
    )}>
      <DropdownMenu.Root open={open} onOpenChange={setOpen}>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            className="relative inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 rounded-full text-earth-600 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/10 hover:text-earth-950 dark:hover:text-lsc-cream transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            aria-label={unreadCount > 0
              ? t('notificationsDropdown.ariaLabelWithCount', { count: unreadCount })
              : t('notificationsDropdown.ariaLabel')}
          >
            <Bell aria-hidden className="w-6 h-6" />
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-bold bg-lsc-rose text-white rounded-full shadow-sm ring-2 ring-lsc-white dark:ring-earth-950">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="end"
            sideOffset={8}
            collisionPadding={16}
            aria-label={t('aria.notificationsDropdown.notifications')}
            className={clsx(
              'bg-lsc-white dark:bg-earth-900 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700',
              'w-[calc(100vw-2rem)] max-w-sm sm:max-w-[384px] z-[60] overflow-hidden',
              'motion-safe:animate-menu-enter',
            )}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-800">
              <DropdownMenu.Label className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('notificationsDropdown.notifications')}
              </DropdownMenu.Label>
              {unreadCount > 0 && (
                <DropdownMenu.Item
                  onSelect={(e) => {
                    e.preventDefault()
                    void handleMarkAllRead()
                  }}
                  disabled={markingAllRead}
                  className="flex items-center gap-1.5 text-sm text-lsc-rose hover:text-lsc-rose/80 transition-colors data-[disabled]:opacity-50 outline-none cursor-pointer"
                >
                  {markingAllRead ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <CheckCheck className="w-4 h-4" />
                  )}
                  {t('notificationsDropdown.markAllRead')}
                </DropdownMenu.Item>
              )}
            </div>

            <div className="max-h-96 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
                </div>
              ) : error ? (
                <div className="py-8 px-4 text-center">
                  <AlertCircle aria-hidden className="w-10 h-10 text-status-danger-600 dark:text-status-danger-400 mx-auto mb-2" />
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream mb-3" role="alert">{error}</p>
                  <DropdownMenu.Item
                    onSelect={(e) => {
                      e.preventDefault()
                      void fetchNotifications()
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 data-[highlighted]:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium transition-colors outline-none cursor-pointer"
                  >
                    {t('notificationsDropdown.retry') || 'Retry'}
                  </DropdownMenu.Item>
                </div>
              ) : notifications.length === 0 ? (
                <div className="py-8 text-center">
                  <Bell aria-hidden className="w-10 h-10 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto mb-2" />
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('notificationsDropdown.noNotificationsYet')}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {t('notificationsDropdown.allCaughtUp')}
                  </p>
                </div>
              ) : (
                notifications.map((notification, idx) => {
                  const { icon: Icon, colorClass, bgClass } = getNotificationIcon(notification.type)
                  return (
                    <DropdownMenu.Item
                      key={notification.id}
                      onSelect={() => void handleNotificationClick(notification)}
                      className={clsx(
                        'w-full text-left px-4 py-3 transition-colors outline-none cursor-pointer block',
                        idx !== 0 && 'border-t border-lsc-border dark:border-earth-700',
                        'data-[highlighted]:bg-lsc-rose/10',
                        notification.is_read
                          ? 'bg-lsc-white dark:bg-earth-900'
                          : 'bg-lsc-cream/30 dark:bg-earth-800/50',
                      )}
                    >
                      <div className="flex gap-3">
                        <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0', bgClass)}>
                          <Icon aria-hidden className={clsx('w-5 h-5', colorClass)} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p
                              className={clsx(
                                'text-sm font-medium truncate',
                                notification.is_read
                                  ? 'text-lsc-dark/80 dark:text-lsc-cream/80'
                                  : 'text-lsc-dark dark:text-lsc-cream',
                              )}
                              title={notification.title}
                            >
                              {notification.title}
                            </p>
                            {!notification.is_read && (
                              <span aria-hidden className="w-2 h-2 rounded-full bg-lsc-rose flex-shrink-0 mt-1.5" />
                            )}
                          </div>
                          <p
                            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mt-0.5"
                            title={notification.message}
                          >
                            {notification.message}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {formatTimeAgo(notification.created_at)}
                          </p>
                        </div>
                      </div>
                    </DropdownMenu.Item>
                  )
                })
              )}
            </div>

            <div className="border-t border-lsc-border dark:border-earth-700 px-4 py-2 bg-lsc-cream/30 dark:bg-earth-800/50">
              <DropdownMenu.Item asChild>
                <Link
                  to="/notifications"
                  className="flex items-center justify-center gap-2 w-full py-2 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 transition-colors rounded-lg data-[highlighted]:bg-lsc-cream/50 dark:data-[highlighted]:bg-earth-700 outline-none"
                >
                  {t('notificationsDropdown.viewAllNotifications')}
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </DropdownMenu.Item>
            </div>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  )
}
