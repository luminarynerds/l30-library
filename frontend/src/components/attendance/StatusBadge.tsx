/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    closed: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    finalized: 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70',
  }
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] || styles.finalized}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}
