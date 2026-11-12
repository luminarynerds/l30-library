/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BarChart3 } from 'lucide-react'
import { t } from '@/i18n'
import { formatMinutes, type SystemStats } from './model'

interface StatsTabProps {
  stats: SystemStats | null
  days: number
  onDaysChange: (days: number) => void
}

export function StatsTab({ stats, days, onDaysChange }: StatsTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          value={days}
          onChange={event => onDaysChange(Number(event.target.value))}
          aria-label={t('aria.staffComputers.statsDateRange', 'Stats date range')}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>
      {stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Reservations', value: stats.total_reservations, color: 'text-lsc-dark dark:text-lsc-cream' },
            { label: 'Completed Sessions', value: stats.total_completed_sessions, color: 'text-status-success-700 dark:text-status-success-400' },
            { label: 'No-Shows', value: stats.no_show_count, color: 'text-status-danger-700 dark:text-status-danger-400' },
            { label: 'Cancelled', value: stats.cancelled_reservations, color: 'text-status-warning-700 dark:text-status-warning-400' },
            { label: 'Avg Session', value: `${stats.average_session_minutes}m`, color: 'text-status-info-700 dark:text-status-info-400' },
            { label: 'Total Time Used', value: formatMinutes(stats.total_minutes_used), color: 'text-lsc-dark dark:text-lsc-cream' },
            { label: 'Cardholder Sessions', value: stats.cardholders_sessions, color: 'text-lsc-dark dark:text-lsc-cream' },
            { label: 'Guest Sessions', value: stats.guest_sessions, color: 'text-category-700 dark:text-category-400' },
            { label: 'Auto No-Shows', value: stats.auto_no_shows ?? 0, color: 'text-status-warning-700 dark:text-status-warning-400' },
            { label: 'Auto Logouts', value: stats.auto_logouts ?? 0, color: 'text-status-warning-700 dark:text-status-warning-400' },
          ].map(stat => (
            <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No usage data available</p>
        </div>
      )}
    </div>
  )
}
