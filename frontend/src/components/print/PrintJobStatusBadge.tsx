/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useTranslation } from '@/i18n'
/**
 * Print Job Status Badge
 *
 * Displays the status of a print job with appropriate color coding and messaging.
 * Used in queue lists and detail views to quickly convey job state.
 */


// ==================== Types ====================

export type PrintJobStatus = 'pending' | 'ready' | 'released' | 'failed'

interface PrintJobStatusBadgeProps {
  /** The status to display */
  status: PrintJobStatus
  /** Optional CSS class name */
  className?: string
  /** Whether to show label text (default: true) */
  showLabel?: boolean
  /** Whether to show icon (default: true) */
  showIcon?: boolean
  /** Custom size variant (default: 'md') */
  size?: 'sm' | 'md' | 'lg'
}

// ==================== Status Configuration ====================

interface StatusConfig {
  label: string
  color: string
  bgColor: string
  borderColor: string
  icon: string
  description: string
}

// ==================== Component ====================

export default function PrintJobStatusBadge({
  status,
  className = '',
  showLabel = true,
  showIcon = true,
  size = 'md',
}: PrintJobStatusBadgeProps) {
  const { t } = useTranslation()

  const statusConfig: Record<PrintJobStatus, StatusConfig> = useMemo(() => ({
    pending: {
      label: 'Pending',
      color: 'text-status-warning-700 dark:text-status-warning-300',
      bgColor: 'bg-status-warning-50 dark:bg-status-warning-900/20',
      borderColor: 'border-status-warning-200 dark:border-status-warning-800',
      icon: '⏳',
      description: t('components.print.printJobStatusBadge.waitingToBePrinted'),
    },
    ready: {
      label: 'Ready',
      color: 'text-status-success-700 dark:text-status-success-300',
      bgColor: 'bg-status-success-50 dark:bg-status-success-900/20',
      borderColor: 'border-status-success-200 dark:border-status-success-800',
      icon: '✓',
      description: 'Ready for pickup',
    },
    released: {
      label: 'Released',
      color: 'text-lsc-rose dark:text-lsc-rose-light',
      bgColor: 'bg-earth-50 dark:bg-earth-800/20',
      borderColor: 'border-lsc-border dark:border-earth-700',
      icon: '→',
      description: 'Released for pickup',
    },
    failed: {
      label: 'Failed',
      color: 'text-status-danger-700 dark:text-status-danger-300',
      bgColor: 'bg-status-danger-50 dark:bg-status-danger-900/20',
      borderColor: 'border-status-danger-200 dark:border-status-danger-800',
      icon: '✕',
      description: 'Print job failed',
    },
  }), [t])

  const config = statusConfig[status]

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-3 text-base',
  }

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-lg border ${sizeClasses[size]} ${config.bgColor} ${config.borderColor} ${config.color} ${className}`}
      title={config.description}
    >
      {showIcon && <span className="font-bold">{config.icon}</span>}
      {showLabel && <span className="font-semibold">{config.label}</span>}
    </div>
  )
}

export type { StatusConfig }
