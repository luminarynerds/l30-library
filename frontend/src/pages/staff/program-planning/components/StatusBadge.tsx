/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
function StatusBadge({ status, colorMap }: { status: string; colorMap?: Record<string, string> }) {
  const defaultColors: Record<string, string> = {
    confirmed: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
    completed: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
    received: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
    on_hand: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
    paid: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
    pending: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
    requested: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
    needed: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
    ordered: 'bg-status-info-100 text-status-info-700 dark:bg-status-info-900 dark:text-status-info-200',
    declined: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
    no_show: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
    overdue: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
    unavailable: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
    cancelled: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
  }
  const colors = { ...defaultColors, ...colorMap }
  const cls = colors[status] ?? 'bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-200'
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export default StatusBadge
