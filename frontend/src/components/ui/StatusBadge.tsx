/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { LucideIcon } from 'lucide-react'
import { CheckCircle2, AlertCircle, XCircle, Info, MinusCircle } from 'lucide-react'

export type StatusVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export interface StatusBadgeProps {
  variant: StatusVariant
  children: React.ReactNode
  icon?: LucideIcon
  size?: 'sm' | 'md'
  className?: string
}

const defaultIcons: Record<StatusVariant, LucideIcon> = {
  success: CheckCircle2,
  warning: AlertCircle,
  danger: XCircle,
  info: Info,
  neutral: MinusCircle,
}

const variantClasses: Record<StatusVariant, string> = {
  success: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200',
  warning: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200',
  danger:  'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  info:    'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-200',
  neutral: 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80',
}

export function StatusBadge({
  variant,
  children,
  icon,
  size = 'sm',
  className = '',
}: StatusBadgeProps): React.ReactElement {
  const Icon = icon ?? defaultIcons[variant]

  const sizeClasses =
    size === 'md'
      ? 'px-3 py-1.5 text-sm'
      : 'px-2.5 py-1 text-xs'

  const iconSizeClass = size === 'md' ? 'w-3.5 h-3.5' : 'w-3 h-3'

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClasses} ${variantClasses[variant]} ${className}`}
    >
      <Icon className={iconSizeClass} aria-hidden="true" />
      {children}
    </span>
  )
}
