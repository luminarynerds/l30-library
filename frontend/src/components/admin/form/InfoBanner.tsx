/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Info, AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react'

export type BannerTone = 'info' | 'warning' | 'danger' | 'success'

const TONE_STYLES: Record<BannerTone, { wrap: string; icon: React.ElementType; iconColor: string }> = {
  info: {
    wrap: 'bg-earth-50 dark:bg-earth-900/20 border-lsc-border dark:border-earth-800 text-earth-800 dark:text-earth-200',
    icon: Info,
    iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
  },
  warning: {
    wrap: 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800 text-status-warning-800 dark:text-status-warning-200',
    icon: AlertTriangle,
    iconColor: 'text-status-warning-600 dark:text-status-warning-400',
  },
  danger: {
    wrap: 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800 text-status-danger-800 dark:text-status-danger-200',
    icon: AlertCircle,
    iconColor: 'text-status-danger-600 dark:text-status-danger-400',
  },
  success: {
    wrap: 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800 text-status-success-800 dark:text-status-success-200',
    icon: CheckCircle2,
    iconColor: 'text-status-success-600 dark:text-status-success-400',
  },
}

export interface InfoBannerProps {
  tone?: BannerTone
  children: React.ReactNode
  icon?: React.ElementType
}

export function InfoBanner({
  tone = 'info',
  icon,
  children,
}: InfoBannerProps): React.ReactElement {
  const style = TONE_STYLES[tone]
  const Icon = icon ?? style.icon
  return (
    <div className={`border rounded-lg p-4 flex gap-3 ${style.wrap}`}>
      <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${style.iconColor}`} aria-hidden="true" />
      <div className="text-sm">{children}</div>
    </div>
  )
}
