/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowRight, Check, ChevronLeft, ChevronRight, Loader2, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { clsx } from '../../utils/helpers'
import { formatDateTime, getNotificationIcon } from './notifications-data'
import type { Notification } from './notifications-data'

const ACTION_LINK_CLASS =
  'inline-flex items-center justify-center gap-2 px-4 py-3 min-h-[48px] rounded-xl ' +
  'text-base font-semibold bg-lsc-rose hover:bg-lsc-rose/90 text-white shadow-md ' +
  'hover:shadow-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose'

function FocusModeAction({ notification }: { notification: Notification }): React.ReactElement | null {
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

interface FocusModeViewProps {
  notifications: Notification[]
  focusIndex: number
  setFocusIndex: (idx: number) => void
  processingIds: Set<number | string>
  onMarkAsRead: (n: Notification) => void
  onDelete: (n: Notification) => void
  onNavigate: (direction: 'prev' | 'next') => void
  onNotificationClick: (n: Notification) => void
  cardRef?: React.Ref<HTMLDivElement>
}

export function FocusModeView({
  notifications,
  focusIndex,
  setFocusIndex,
  processingIds,
  onMarkAsRead,
  onDelete,
  onNavigate,
  onNotificationClick,
  cardRef,
}: FocusModeViewProps): React.ReactElement {
  return (
    <div className="p-6 sm:p-8">
      {notifications.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-6">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {focusIndex + 1} of {notifications.length}
            </span>
            <div className="flex items-center gap-1.5">
              {notifications.map((_, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => setFocusIndex(idx)}
                  aria-label={`Go to notification ${idx + 1}`}
                  aria-current={idx === focusIndex ? 'true' : undefined}
                  className={clsx(
                    'w-2.5 h-2.5 rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-1',
                    idx === focusIndex
                      ? 'bg-lsc-rose'
                      : 'bg-lsc-border dark:bg-earth-700 hover:bg-lsc-rose/50'
                  )}
                />
              ))}
            </div>
          </div>

          {(() => {
            const notification = notifications[focusIndex]
            if (!notification) return null
            const { icon: Icon, colorClass, bgClass, label } = getNotificationIcon(notification.type)
            const isProcessing = processingIds.has(notification.id)

            return (
              <div
                ref={cardRef}
                tabIndex={-1}
                className={clsx(
                  'p-6 rounded-xl border-2 transition-colors',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
                  notification.is_read
                    ? 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800'
                    : 'border-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10'
                )}
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', bgClass)}>
                    <Icon className={clsx('w-6 h-6', colorClass)} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', bgClass, colorClass)}>
                        {label}
                      </span>
                      {!notification.is_read && (
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-lsc-rose/20 text-lsc-rose">
                          Unread
                        </span>
                      )}
                    </div>
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream leading-relaxed">
                      {notification.title}
                    </h3>
                  </div>
                </div>

                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4 text-base">
                  {notification.message}
                </p>

                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                  {formatDateTime(notification.created_at)}
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                  {notification.action_url && notification.action_label ? (
                    <FocusModeAction notification={notification} />
                  ) : (notification.link_url || notification.action_url) && (
                    <Button variant="primary"
                      onClick={() => onNotificationClick(notification)}
                    >
                      View details
                    </Button>
                  )}
                  {!notification.is_read && (
                    <Button variant="primary"
                      onClick={() => onMarkAsRead(notification)}
                      disabled={isProcessing}
                    >
                      {isProcessing ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          Mark as read
                        </>
                      )}
                    </Button>
                  )}
                  <Button variant="danger"
                    onClick={() => onDelete(notification)}
                    disabled={isProcessing}
                  >
                    {isProcessing ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )
          })()}

          <div className="flex items-center justify-between mt-6">
            <Button variant="secondary"
              onClick={() => onNavigate('prev')}
              disabled={focusIndex === 0}
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">(↑/k)</span>
            </Button>
            <Button variant="secondary"
              onClick={() => onNavigate('next')}
              disabled={focusIndex === notifications.length - 1}
            >
              Next
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">(↓/j)</span>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
