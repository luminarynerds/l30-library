import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export const RECOGNITION_COLORS: Record<string, string> = {
  bronze: 'text-status-warning-700 bg-status-warning-100 dark:text-status-warning-400 dark:bg-status-warning-900/30',
  silver: 'text-earth-700 bg-earth-100 dark:text-earth-300 dark:bg-earth-800',
  gold: 'text-status-warning-700 bg-status-warning-100 dark:text-status-warning-400 dark:bg-status-warning-900/30',
  platinum: 'text-lsc-rose bg-earth-100 dark:text-lsc-rose-light dark:bg-earth-800/30',
  champion: 'text-category-700 bg-category-100 dark:text-category-400 dark:bg-category-900/30',
};

export const STATUS_COLORS: Record<string, string> = {
  active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  inactive: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  on_leave: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  pending_approval: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  terminated: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
};

export function formatDate(d: string): string {
  return new Date(d).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' });
}

export type VolunteerTab = 'roster' | 'availability' | 'hours';
