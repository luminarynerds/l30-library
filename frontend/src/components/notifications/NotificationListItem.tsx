/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowRight, Check, Loader2, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { clsx } from '../../utils/helpers'
import { useTranslation } from '@/i18n'
import { formatDateTime, getNotificationIcon } from './notifications-data'
import type { Notification, ViewDensity } from './notifications-data'

const ACTION_LINK_CLASS =
  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ' +
  'bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose hover:bg-lsc-rose/20 ' +
  'dark:hover:bg-lsc-rose/30 transition-colors focus:outline-none ' +
  'focus-visible:ring-2 focus-visible:ring-lsc-rose'

function NotificationAction({ notification }: { notification: Notification }): React.ReactElement | null {
  const url = notification.action_url
  const label = notification.action_label
  if (!url || !label) return null
  const isExternal = /^https?:\/\//i.test(url)
  return isExternal ? (
    <a href={url} className={ACTION_LINK_CLASS}>
      {label}
      <ArrowRight className="w-4 h-4" aria-hidden="true" />
    </a>
  ) : (
    <Link to={url} className={ACTION_LINK_CLASS}>
      {label}
      <ArrowRight className="w-4 h-4" aria-hidden="true" />
    </Link>
  )
}

interface NotificationListItemProps {
  notification: Notification
  viewDensity: ViewDensity
  isProcessing: boolean
  onMarkAsRead: (n: Notification) => void
  onDelete: (n: Notification) => void
  onNotificationClick: (n: Notification) => void
}

export function NotificationListItem({
  notification,
  viewDensity,
  isProcessing,
  onMarkAsRead,
  onDelete,
  onNotificationClick,
}: NotificationListItemProps): React.ReactElement {
  const { t } = useTranslation()
  const { icon: Icon, colorClass, bgClass, label } = getNotificationIcon(notification.type)

  return (
    <li
      className={clsx(
        'relative transition-colors',
        notification.is_read
          ? 'bg-lsc-white dark:bg-earth-800'
          : 'bg-lsc-cream/30 dark:bg-earth-700/30'
      )}
    >
      <div className={clsx(
        'flex items-start gap-4',
        viewDensity === 'comfortable' ? 'p-4 sm:p-6' : 'p-3 sm:p-4'
      )}>
        <div
          className={clsx(
            'rounded-lg flex items-center justify-center flex-shrink-0',
            viewDensity === 'comfortable' ? 'w-10 h-10' : 'w-8 h-8',
            bgClass
          )}
        >
          <Icon className={clsx(viewDensity === 'comfortable' ? 'w-5 h-5' : 'w-4 h-4', colorClass)} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <button
                type="button"
                onClick={() => onNotificationClick(notification)}
                className="flex items-center gap-2 flex-wrap text-left rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              >
                <span
                  className={clsx(
                    'font-medium hover:text-lsc-rose transition-colors leading-snug',
                    viewDensity === 'comfortable' ? 'text-base' : 'text-sm',
                    notification.is_read
                      ? 'text-lsc-dark/80 dark:text-lsc-cream/80'
                      : 'text-lsc-dark dark:text-lsc-cream'
                  )}
                >
                  {notification.title}
                </span>
                {!notification.is_read && (
                  <span className="w-2 h-2 rounded-full bg-lsc-rose flex-shrink-0" aria-label={t('aria.notifications.unread')} />
                )}
              </button>
              <p className={clsx(
                'text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 leading-relaxed',
                viewDensity === 'comfortable' ? 'text-sm' : 'text-xs'
              )}>
                {notification.message}
              </p>
              <div className={clsx(
                'flex items-center gap-3',
                viewDensity === 'comfortable' ? 'mt-2' : 'mt-1.5'
              )}>
                <span
                  className={clsx(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                    bgClass,
                    colorClass
                  )}
                >
                  {label}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatDateTime(notification.created_at)}
                </span>
              </div>
              {(notification.action_url && notification.action_label) && (
                <div className={clsx(viewDensity === 'comfortable' ? 'mt-3' : 'mt-2')}>
                  <NotificationAction notification={notification} />
                </div>
              )}
            </div>

            <div className="flex items-center gap-1">
              {!notification.is_read && (
                <Button variant="primary" size="sm"
                  onClick={() => onMarkAsRead(notification)}
                  disabled={isProcessing}
                  aria-label="Mark as read (x)"
                  title="Mark as read (x)"
                >
                  {isProcessing ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                </Button>
              )}
              <Button variant="danger" size="sm"
                onClick={() => onDelete(notification)}
                disabled={isProcessing}
                aria-label={t('aria.notifications.deleteNotification')}
                title="Delete notification"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </li>
  )
}
