/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Page size options
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const
const PAGE_SIZE_STORAGE_KEY = 'admin-users-page-size'

// Get stored page size or default
// NOTE: Removed illegal useTranslation() call that was in a non-component function
export const getStoredPageSize = (): number => {
  try {
    const stored = localStorage.getItem(PAGE_SIZE_STORAGE_KEY)
    if (stored) {
      const parsed = parseInt(stored, 10)
      if (PAGE_SIZE_OPTIONS.includes(parsed as typeof PAGE_SIZE_OPTIONS[number])) {
        return parsed
      }
    }
  } catch {
    // Ignore localStorage errors
  }
  return 20 // Default
}

// Role badge configuration with colors
export const ROLE_BADGE_CONFIG: Record<string, { bg: string; text: string; darkBg: string; darkText: string }> = {
  SUPER_ADMIN: {
    bg: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    text: 'text-status-danger-700 dark:text-status-danger-300',
    darkBg: 'dark:bg-status-danger-900/30',
    darkText: 'dark:text-status-danger-400',
  },
  ADMIN: {
    bg: 'bg-category-100 dark:bg-category-900/30',
    text: 'text-category-700 dark:text-category-300',
    darkBg: 'dark:bg-category-900/30',
    darkText: 'dark:text-category-400',
  },
  STAFF: {
    bg: 'bg-earth-100 dark:bg-earth-800/30',
    text: 'text-lsc-rose dark:text-lsc-rose-light',
    darkBg: 'dark:bg-earth-800/30',
    darkText: 'dark:text-lsc-rose-light',
  },
  PATRON: {
    bg: 'bg-status-success-100 dark:bg-status-success-900/30',
    text: 'text-status-success-700 dark:text-status-success-300',
    darkBg: 'dark:bg-status-success-900/30',
    darkText: 'dark:text-status-success-400',
  },
  CHILD: {
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    text: 'text-status-warning-700 dark:text-status-warning-300',
    darkBg: 'dark:bg-status-warning-900/30',
    darkText: 'dark:text-status-warning-400',
  },
  BOOKMOBILE: {
    bg: 'bg-teal-100 dark:bg-teal-900/30',
    text: 'text-teal-700 dark:text-teal-300',
    darkBg: 'dark:bg-teal-900/30',
    darkText: 'dark:text-teal-400',
  },
  HOME_DELIVERY: {
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    text: 'text-status-warning-700 dark:text-status-warning-300',
    darkBg: 'dark:bg-status-warning-900/30',
    darkText: 'dark:text-status-warning-400',
  },
}

// Avatar background colors based on user ID
// Per-hue minimal correction: lightest shade pair whose primary (white-text-
// bearing, i.e. lighter/light-theme) shade clears 4.5:1 against white.
// rose/pink/fuchsia/violet/indigo/earth/category/success/danger clear 4.5:1
// already at -600; sky/cyan/teal/emerald/lime/warning need -700 (see
// scripts/contrast-check.mjs for computed ratios).
export const AVATAR_COLORS = [
  'bg-rose-600 dark:bg-rose-700',
  'bg-pink-600 dark:bg-pink-700',
  'bg-fuchsia-600 dark:bg-fuchsia-700',
  'bg-category-600 dark:bg-category-700',
  'bg-violet-600 dark:bg-violet-700',
  'bg-indigo-600 dark:bg-indigo-700',
  'bg-earth-600 dark:bg-earth-700',
  'bg-sky-700 dark:bg-sky-800',
  'bg-cyan-700 dark:bg-cyan-800',
  'bg-teal-700 dark:bg-teal-800',
  'bg-emerald-700 dark:bg-emerald-800',
  'bg-status-success-600 dark:bg-status-success-700',
  'bg-lime-700 dark:bg-lime-800',
  'bg-status-warning-700 dark:bg-status-warning-800',
  'bg-status-warning-700 dark:bg-status-warning-800',
  'bg-status-danger-600 dark:bg-status-danger-700',
]

// Get user initials
export const getUserInitials = (firstName: string | null | undefined, lastName: string | null | undefined, email: string): string => {
  if (firstName && lastName) {
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
  }
  if (firstName) {
    return firstName.charAt(0).toUpperCase()
  }
  if (lastName) {
    return lastName.charAt(0).toUpperCase()
  }
  if (email) {
    return email.charAt(0).toUpperCase()
  }
  return '?'
}

// Get consistent avatar color based on user ID
export const getAvatarColor = (userId: number): string => {
  return AVATAR_COLORS[userId % AVATAR_COLORS.length] || 'bg-earth-700 dark:bg-earth-800'
}
