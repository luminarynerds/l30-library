import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  type HomeDeliveryApplication,
  type HomeDeliveryEnrollment,
  type DeliveryFrequency,
  type HomeDeliveryItemRequest,
} from '@/api/homeDeliveryApi'

export type TabId = 'apply' | 'enrollment' | 'deliveries' | 'preferences' | 'requests'

export const GENRE_OPTIONS = [
  'Mystery', 'Romance', 'Sci-Fi', 'Fantasy', 'Historical Fiction', 'Thriller',
  'Literary Fiction', 'Biography', 'Self-Help', 'Science', 'History', 'Cooking',
  'Gardening', 'Travel', 'Poetry', 'True Crime', 'Humor',
]

export const FREQUENCY_OPTIONS: { value: DeliveryFrequency; label: string }[] = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Every Two Weeks' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'on_demand', label: 'On Demand' },
]

export const DAY_OPTIONS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

export const REQUEST_TYPE_OPTIONS: { value: HomeDeliveryItemRequest['request_type']; label: string }[] = [
  { value: 'specific_title', label: 'Specific Title' },
  { value: 'author', label: 'By Author' },
  { value: 'subject', label: 'By Subject' },
  { value: 'genre', label: 'By Genre' },
  { value: 'surprise_me', label: 'Surprise Me' },
]

export function statusBadge(status: string): string {
  const base = 'inline-flex items-center px-2 py-1 rounded text-xs font-medium'
  switch (status) {
    case 'pending':
    case 'under_review':
    case 'scheduled':
    case 'items_selected':
      return `${base} bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300`
    case 'approved':
    case 'active':
    case 'delivered':
    case 'picked_up':
      return `${base} bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300`
    case 'denied':
    case 'delivery_failed':
    case 'cancelled':
    case 'terminated':
    case 'suspended':
      return `${base} bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300`
    case 'waitlisted':
    case 'paused':
    case 'packed':
      return `${base} bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light`
    case 'out_for_delivery':
      return `${base} bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300`
    default:
      return `${base} bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300`
  }
}

export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function formatDate(dateStr?: string): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export type { HomeDeliveryApplication, HomeDeliveryEnrollment, DeliveryFrequency, HomeDeliveryItemRequest }
