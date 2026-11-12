/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { clsx } from '../../utils/helpers'

export type StatusTone =
  | 'neutral'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'muted'

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: 'bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-200',
  success: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  warning: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  danger: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  info: 'bg-earth-50 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
  muted: 'bg-earth-50 text-earth-600 dark:bg-earth-800/50 dark:text-earth-400',
}

export interface StatusBadgeProps {
  label: string
  tone?: StatusTone
  icon?: React.ElementType
  size?: 'sm' | 'md'
}

export function StatusBadge({
  label,
  tone = 'neutral',
  icon: Icon,
  size = 'md',
}: StatusBadgeProps): React.ReactElement {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full font-medium',
        TONE_CLASSES[tone],
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
      )}
    >
      {Icon && <Icon className="h-3 w-3" aria-hidden="true" />}
      {label}
    </span>
  )
}
