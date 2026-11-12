/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { DeliveryStatus } from '../../api/homeDeliveryApi';
import { getCurrentLocale } from '@/i18n'

export const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  items_selected: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  packed: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  out_for_delivery: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
  delivered: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  delivery_failed: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  picked_up: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
  cancelled: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  draft: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  planned: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  in_progress: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  completed: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
};

export function getStatusColor(status: string): string {
  return STATUS_COLORS[status] ?? 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300';
}

export function formatDate(d: string): string {
  return new Date(d).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' });
}

export const DELIVERY_STEPS: DeliveryStatus[] = [
  'scheduled',
  'items_selected',
  'packed',
  'out_for_delivery',
  'delivered',
];
