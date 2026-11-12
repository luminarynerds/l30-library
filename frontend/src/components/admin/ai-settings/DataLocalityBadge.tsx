/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Lock, Cloud } from 'lucide-react'

type Locality = 'local' | 'cloud' | 'mixed'

interface DataLocalityBadgeProps {
  locality: Locality
  className?: string
}

const CONFIG: Record<Locality, { icon: typeof Lock; label: string; ariaLabel: string; classes: string }> = {
  local: {
    icon: Lock,
    label: 'Runs locally',
    ariaLabel: 'All data stays on your server',
    classes: 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800',
  },
  cloud: {
    icon: Cloud,
    label: 'Uses cloud API',
    ariaLabel: 'Some data is sent to an external service',
    classes: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
  },
  mixed: {
    icon: Cloud,
    label: 'Mixed',
    ariaLabel: 'Some features use a cloud API, others run locally',
    classes: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
  },
}

export function DataLocalityBadge({ locality, className = '' }: DataLocalityBadgeProps) {
  const { icon: Icon, label, ariaLabel, classes } = CONFIG[locality]
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded-full ${classes} ${className}`}
      aria-label={ariaLabel}
      role="status"
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {label}
    </span>
  )
}
