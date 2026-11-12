/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle, AlertTriangle, AlertCircle, Info } from 'lucide-react'

type ComplianceStatus = 'compliant' | 'attention' | 'action-required' | 'info'

interface ComplianceStatusBadgeProps {
  status: ComplianceStatus
  className?: string
}

const CONFIG: Record<ComplianceStatus, { icon: typeof CheckCircle; label: string; ariaLabel: string; classes: string }> = {
  compliant: {
    icon: CheckCircle,
    label: 'Compliant',
    ariaLabel: 'No issues found',
    classes: 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800',
  },
  attention: {
    icon: AlertTriangle,
    label: 'Needs attention',
    ariaLabel: 'Some items need review',
    classes: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
  },
  'action-required': {
    icon: AlertCircle,
    label: 'Action required',
    ariaLabel: 'Urgent items need immediate attention',
    classes: 'bg-status-danger-50 text-status-danger-700 border-status-danger-200 dark:bg-status-danger-900/20 dark:text-status-danger-300 dark:border-status-danger-800',
  },
  info: {
    icon: Info,
    label: 'Informational',
    ariaLabel: 'No action needed, view only',
    classes: 'bg-earth-50 text-earth-600 border-lsc-border dark:bg-earth-800/30 dark:text-earth-300 dark:border-earth-700',
  },
}

export type { ComplianceStatus }

export function ComplianceStatusBadge({ status, className = '' }: ComplianceStatusBadgeProps) {
  const { icon: Icon, label, ariaLabel, classes } = CONFIG[status]
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
