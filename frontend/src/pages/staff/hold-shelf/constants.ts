/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const esc = (str: string): string =>
  (str || "").replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c] || c
  )

export const getUrgencyColor = (daysUntilExpiry: number | null): string => {
  if (daysUntilExpiry === null) return "text-lsc-dark/70 dark:text-lsc-cream/70"
  if (daysUntilExpiry <= 0) return "text-status-danger-600 dark:text-status-danger-400"
  if (daysUntilExpiry === 1) return "text-status-warning-600"
  if (daysUntilExpiry <= 3) return "text-status-warning-600"
  return "text-status-success-600 dark:text-status-success-400"
}

export const getUrgencyLabel = (daysUntilExpiry: number | null): string => {
  if (daysUntilExpiry === null) return "Unknown"
  if (daysUntilExpiry < 0) return "Expired"
  if (daysUntilExpiry === 0) return "Today"
  if (daysUntilExpiry === 1) return "Tomorrow"
  return `${daysUntilExpiry} days`
}
