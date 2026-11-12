/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  BookCheck,
  CalendarClock,
  AlertTriangle,
  CircleDollarSign,
  Receipt,
  Lock,
  Unlock,
  MessageCircle,
  Search,
  ShieldAlert,
  Bell,
} from 'lucide-react'

export type ViewDensity = 'comfortable' | 'compact'
export type ViewMode = 'list' | 'focus'

/**
 * Dispatched on `window` whenever the patron changes notification read state
 * (mark read, mark all read, delete, undo). The nav bell dropdown listens for
 * it and re-fetches its unread count so the badge doesn't stay stale until its
 * own 60s poll.
 */
export const NOTIFICATIONS_CHANGED_EVENT = 'l30:notifications:changed'

export type TypeFilter =
  | 'all'
  | 'hold_available'
  | 'hold_expiring'
  | 'hold_cancelled'
  | 'checkout_receipt'
  | 'due_date_reminder'
  | 'overdue_notice'
  | 'fine_assessed'
  | 'fine_paid'
  | 'account_blocked'
  | 'account_unblocked'
  | 'reference_chat_reply'
  | 'catalog_saved_search_match'
  | 'panic_alert'

export type ReadFilter = 'all' | 'read' | 'unread'

export interface Notification {
  id: number | string
  type: string
  category?: string
  title: string
  message: string
  is_read: boolean
  created_at: string
  source_event_type?: string
  related_loan_id?: string | null
  related_hold_id?: string | null
  related_fine_id?: string | null
  related_item_title?: string | null
  action_url?: string | null
  action_label?: string | null
  link_url?: string
}

export const notificationConfig: Record<string, { icon: React.ElementType; colorClass: string; bgClass: string; label: string }> = {
  hold_available: {
    icon: BookCheck,
    colorClass: 'text-status-success-600 dark:text-status-success-400',
    bgClass: 'bg-status-success-100 dark:bg-status-success-900/30',
    label: 'Hold Ready',
  },
  hold_expiring: {
    icon: CalendarClock,
    colorClass: 'text-status-warning-600 dark:text-status-warning-400',
    bgClass: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    label: 'Hold Expiring',
  },
  hold_cancelled: {
    icon: AlertTriangle,
    colorClass: 'text-status-warning-600 dark:text-status-warning-400',
    bgClass: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    label: 'Hold Cancelled',
  },
  checkout_receipt: {
    icon: Receipt,
    colorClass: 'text-lsc-rose dark:text-lsc-rose-light',
    bgClass: 'bg-earth-100 dark:bg-earth-800/30',
    label: 'Checkout',
  },
  due_date_reminder: {
    icon: CalendarClock,
    colorClass: 'text-status-warning-600 dark:text-status-warning-400',
    bgClass: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    label: 'Due Date',
  },
  overdue_notice: {
    icon: AlertTriangle,
    colorClass: 'text-status-danger-600 dark:text-status-danger-400',
    bgClass: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    label: 'Overdue',
  },
  fine_assessed: {
    icon: CircleDollarSign,
    colorClass: 'text-status-danger-600 dark:text-status-danger-400',
    bgClass: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    label: 'Fine',
  },
  fine_paid: {
    icon: CircleDollarSign,
    colorClass: 'text-status-success-600 dark:text-status-success-400',
    bgClass: 'bg-status-success-100 dark:bg-status-success-900/30',
    label: 'Fine Paid',
  },
  account_blocked: {
    icon: Lock,
    colorClass: 'text-status-danger-600 dark:text-status-danger-400',
    bgClass: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    label: 'Account Blocked',
  },
  account_unblocked: {
    icon: Unlock,
    colorClass: 'text-status-success-600 dark:text-status-success-400',
    bgClass: 'bg-status-success-100 dark:bg-status-success-900/30',
    label: 'Account Restored',
  },
  reference_chat_reply: {
    icon: MessageCircle,
    colorClass: 'text-category-600 dark:text-category-400',
    bgClass: 'bg-category-100 dark:bg-category-900/30',
    label: 'Reference Reply',
  },
  catalog_saved_search_match: {
    icon: Search,
    colorClass: 'text-category-600 dark:text-category-400',
    bgClass: 'bg-category-100 dark:bg-category-900/30',
    label: 'New Arrival',
  },
  panic_alert: {
    icon: ShieldAlert,
    colorClass: 'text-status-danger-600 dark:text-status-danger-400',
    bgClass: 'bg-status-danger-100 dark:bg-status-danger-900/40',
    label: 'Alert',
  },
}

export const typeFilterOptions: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'hold_available', label: 'Hold Ready' },
  { value: 'hold_expiring', label: 'Hold Expiring' },
  { value: 'hold_cancelled', label: 'Hold Cancelled' },
  { value: 'checkout_receipt', label: 'Checkout' },
  { value: 'due_date_reminder', label: 'Due Date' },
  { value: 'overdue_notice', label: 'Overdue' },
  { value: 'fine_assessed', label: 'Fine' },
  { value: 'fine_paid', label: 'Fine Paid' },
  { value: 'account_blocked', label: 'Account Blocked' },
  { value: 'account_unblocked', label: 'Account Restored' },
  { value: 'reference_chat_reply', label: 'Reference Reply' },
  { value: 'catalog_saved_search_match', label: 'New Arrivals' },
  { value: 'panic_alert', label: 'Alerts' },
]

export const readFilterOptions: { value: ReadFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'unread', label: 'Unread' },
  { value: 'read', label: 'Read' },
]

export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) {
    return `Today at ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
  } else if (diffInDays === 1) {
    return `Yesterday at ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
  } else if (diffInDays < 7) {
    return date.toLocaleDateString([], { weekday: 'long', hour: 'numeric', minute: '2-digit' })
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function getDateGroup(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) return 'Today'
  if (diffInDays === 1) return 'Yesterday'
  if (diffInDays < 7) return 'This Week'
  if (diffInDays < 30) return 'This Month'
  return 'Earlier'
}

export function groupNotificationsByDate(notifications: Notification[]): Map<string, Notification[]> {
  const groups = new Map<string, Notification[]>()
  const order = ['Today', 'Yesterday', 'This Week', 'This Month', 'Earlier']

  order.forEach(group => groups.set(group, []))

  notifications.forEach(notification => {
    const group = getDateGroup(notification.created_at)
    const existing = groups.get(group) || []
    existing.push(notification)
    groups.set(group, existing)
  })

  order.forEach(group => {
    if (groups.get(group)?.length === 0) {
      groups.delete(group)
    }
  })

  return groups
}

export function getNotificationIcon(type: string): { icon: React.ElementType; colorClass: string; bgClass: string; label: string } {
  return notificationConfig[type] ?? { icon: Bell, colorClass: 'text-lsc-rose dark:text-lsc-rose-light', bgClass: 'bg-earth-100 dark:bg-earth-800/30', label: 'Notification' }
}
