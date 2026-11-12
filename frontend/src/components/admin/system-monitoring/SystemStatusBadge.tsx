/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle, AlertTriangle, XCircle, Settings } from 'lucide-react'

type SystemStatus = 'healthy' | 'degraded' | 'down' | 'configured' | 'unknown'

interface SystemStatusBadgeProps {
  status: SystemStatus
  label?: string | undefined
  className?: string
}

const CONFIG: Record<SystemStatus, { icon: typeof CheckCircle; label: string; ariaLabel: string; classes: string }> = {
  healthy: {
    icon: CheckCircle,
    label: 'Healthy',
    ariaLabel: 'System status: Healthy',
    classes: 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800',
  },
  degraded: {
    icon: AlertTriangle,
    label: 'Degraded',
    ariaLabel: 'System status: Degraded',
    classes: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
  },
  down: {
    icon: XCircle,
    label: 'Down',
    ariaLabel: 'System status: Down',
    classes: 'bg-status-danger-50 text-status-danger-700 border-status-danger-200 dark:bg-status-danger-900/20 dark:text-status-danger-300 dark:border-status-danger-800',
  },
  configured: {
    icon: Settings,
    label: 'Configured',
    ariaLabel: 'System status: Configured',
    classes: 'bg-earth-50 text-earth-600 border-lsc-border dark:bg-earth-800/30 dark:text-earth-300 dark:border-earth-700',
  },
  unknown: {
    icon: AlertTriangle,
    label: 'Unknown',
    ariaLabel: 'System status: Unknown',
    classes: 'bg-earth-50 text-earth-600 border-lsc-border dark:bg-earth-800/30 dark:text-earth-300 dark:border-earth-700',
  },
}

export type { SystemStatus }

export function SystemStatusBadge({ status, label: customLabel, className = '' }: SystemStatusBadgeProps) {
  const config = CONFIG[status]
  const { icon: Icon, ariaLabel, classes } = config
  const displayLabel = customLabel || config.label
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded-full ${classes} ${className}`}
      aria-label={ariaLabel}
      role="status"
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {displayLabel}
    </span>
  )
}
