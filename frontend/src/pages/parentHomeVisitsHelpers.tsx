/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { format } from 'date-fns'
import {
  Calendar,
  Check,
  CheckCircle,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import type { ReactNode } from 'react'
import type { HomeVisitStatus } from '@/api/parent-onboarding-api'

export type StatusConfigEntry = {
  color: string
  icon: ReactNode
  /** A short, non-color cue (geometric shape glyph or punctuation) that lets
   *  the badge stay distinguishable in monochrome / forced-colors mode. */
  monoCue: string
}

export const STATUS_CONFIG: Record<HomeVisitStatus, StatusConfigEntry> = {
  scheduled: {
    color:
      'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    icon: <Calendar aria-hidden="true" className="w-3.5 h-3.5" />,
    monoCue: '○',
  },
  confirmed: {
    color:
      'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    icon: <Check aria-hidden="true" className="w-3.5 h-3.5" strokeWidth={3} />,
    monoCue: '✓',
  },
  completed: {
    color:
      'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    icon: <CheckCircle aria-hidden="true" className="w-3.5 h-3.5" />,
    monoCue: '✓✓',
  },
  cancelled: {
    color:
      'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    icon: <XCircle aria-hidden="true" className="w-3.5 h-3.5" />,
    monoCue: '✕',
  },
  rescheduled: {
    color:
      'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    icon: <RefreshCw aria-hidden="true" className="w-3.5 h-3.5" />,
    monoCue: '↻',
  },
}

export function getStatusConfig(status: string): StatusConfigEntry {
  return STATUS_CONFIG[status as HomeVisitStatus] ?? STATUS_CONFIG.scheduled
}

export function todayLocalYMD(): string {
  return format(new Date(), 'yyyy-MM-dd')
}
