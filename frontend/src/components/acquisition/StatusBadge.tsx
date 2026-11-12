/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Send,
  PackageCheck,
  Package,
  Ban
} from 'lucide-react'

export type POStatus =
  | 'draft'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'submitted'
  | 'partially_received'
  | 'received'
  | 'cancelled'

interface StatusConfig {
  label: string
  bgColor: string
  textColor: string
  darkBgColor: string
  darkTextColor: string
  icon: React.ElementType
}

const STATUS_CONFIG: Record<POStatus, StatusConfig> = {
  draft: {
    label: 'Draft',
    bgColor: 'bg-earth-100 dark:bg-earth-700',
    textColor: 'text-lsc-dark/70 dark:text-lsc-cream/70',
    darkBgColor: 'dark:bg-earth-800',
    darkTextColor: 'dark:text-earth-300',
    icon: FileText
  },
  pending_approval: {
    label: 'Pending Approval',
    bgColor: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    textColor: 'text-status-warning-700 dark:text-status-warning-300',
    darkBgColor: 'dark:bg-status-warning-900/30',
    darkTextColor: 'dark:text-status-warning-400',
    icon: Clock
  },
  approved: {
    label: 'Approved',
    bgColor: 'bg-earth-100 dark:bg-earth-800/30',
    textColor: 'text-lsc-rose dark:text-lsc-rose-light',
    darkBgColor: 'dark:bg-earth-800/30',
    darkTextColor: 'dark:text-lsc-rose-light',
    icon: CheckCircle
  },
  rejected: {
    label: 'Rejected',
    bgColor: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    textColor: 'text-status-danger-700 dark:text-status-danger-300',
    darkBgColor: 'dark:bg-status-danger-900/30',
    darkTextColor: 'dark:text-status-danger-400',
    icon: XCircle
  },
  submitted: {
    label: 'Submitted',
    bgColor: 'bg-category-100 dark:bg-category-900/30',
    textColor: 'text-category-700 dark:text-category-300',
    darkBgColor: 'dark:bg-category-900/30',
    darkTextColor: 'dark:text-category-400',
    icon: Send
  },
  partially_received: {
    label: 'Partially Received',
    bgColor: 'bg-cyan-100 dark:bg-cyan-900/30',
    textColor: 'text-cyan-700 dark:text-cyan-300',
    darkBgColor: 'dark:bg-cyan-900/30',
    darkTextColor: 'dark:text-cyan-400',
    icon: PackageCheck
  },
  received: {
    label: 'Received',
    bgColor: 'bg-status-success-100 dark:bg-status-success-900/30',
    textColor: 'text-status-success-700 dark:text-status-success-300',
    darkBgColor: 'dark:bg-status-success-900/30',
    darkTextColor: 'dark:text-status-success-400',
    icon: Package
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-earth-200 dark:bg-earth-600',
    textColor: 'text-lsc-dark/70 dark:text-lsc-cream/70',
    darkBgColor: 'dark:bg-earth-700',
    darkTextColor: 'dark:text-earth-300',
    icon: Ban
  }
}

interface StatusBadgeProps {
  status: POStatus | string
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  className?: string
}

export default function StatusBadge({
  status,
  size = 'md',
  showIcon = true,
  className = ''
}: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase().replace(/ /g, '_') as POStatus
  const config = STATUS_CONFIG[normalizedStatus] || STATUS_CONFIG.draft
  const Icon = config.icon

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2'
  }

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4'
  }

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full
        ${config.bgColor} ${config.textColor}
        ${config.darkBgColor} ${config.darkTextColor}
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {showIcon && <Icon className={iconSizes[size]} aria-hidden="true" />}
      {config.label}
    </span>
  )
}

// Export status configuration for use in other components
export { STATUS_CONFIG }
export type { StatusConfig }
