import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const formatReleaseDate = (d: string | null, isExact: boolean): string => {
  if (!d) return "TBA"
  const date = new Date(d)
  if (!isExact) return date.getFullYear().toString()
  return date.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })
}

export const getStatusBadgeClass = (status: string): string => {
  const styles: Record<string, string> = {
    new: "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light",
    owned: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400",
    on_order: "bg-lsc-cream text-lsc-rose dark:bg-lsc-dark/30 dark:text-lsc-rose-light",
  }
  return styles[status] || "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
}

export const getAgeBadgeClass = (age: string | null | undefined, dark = true): string => {
  if (!age) {
    return dark
      ? "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
      : "bg-earth-100 text-lsc-dark/70 dark:text-lsc-cream/70"
  }
  if (age === "child") {
    return dark
      ? "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400"
      : "bg-status-success-100 text-status-success-700"
  }
  if (age === "teen") {
    return dark
      ? "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light"
      : "bg-earth-100 text-lsc-rose"
  }
  return dark
    ? "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
    : "bg-earth-100 text-lsc-dark/70 dark:text-lsc-cream/70"
}

export const daysUntil = (dateStr: string | null): number | null => {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}
