/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Shift Swap Notifications
 *
 * Shows unread notifications for shift swap activities
 */

import React, { useState } from 'react'
import { Bell } from 'lucide-react'
import { t } from '@/i18n'

export interface Notification {
  id: number
  user_id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

interface Props {
  notifications: Notification[]
  onNotificationClick: (notification: Notification) => void
}

export const ShiftSwapNotifications: React.FC<Props> = ({
  notifications,
  onNotificationClick,
}) => {
  const [showPanel, setShowPanel] = useState(false)

  const unreadCount = notifications.filter(n => !n.is_read).length

  const getIconForType = (type: string) => {
    switch (type) {
      case 'new_match': return '⚡'
      case 'swap_claimed': return '👋'
      case 'claim_approved': return '✅'
      case 'claim_rejected': return '❌'
      case 'swap_expiring': return '⏰'
      default: return '🔔'
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="notifications-widget">
      <button
        className="notifications-button"
        onClick={() => setShowPanel(!showPanel)}
        aria-label={t('aria.notificationsDropdown.notifications')}
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount}</span>
        )}
      </button>

      {showPanel && (
        <div className="notifications-panel">
          <div className="panel-header">
            <h3>Notifications</h3>
            <button className="close-btn" onClick={() => setShowPanel(false)}>×</button>
          </div>

          <div className="notifications-list">
            {notifications.length === 0 ? (
              <div className="empty-state">
                <p>No notifications yet</p>
              </div>
            ) : (
              notifications.slice(0, 10).map((notification) => (
                // eslint-disable-next-line jsx-a11y/click-events-have-key-events
                <div
                  key={notification.id}
                  className={`notification-item ${notification.is_read ? 'read' : 'unread'}`}
                  onClick={() => onNotificationClick(notification)}
                >
                  <span className="icon">{getIconForType(notification.notification_type)}</span>
                  <div className="content">
                    <strong>{notification.title}</strong>
                    <p>{notification.message}</p>
                    <small>{formatTime(notification.created_at)}</small>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ShiftSwapNotifications
