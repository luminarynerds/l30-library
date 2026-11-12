/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
const colorClasses = {
  accent: 'bg-earth-100 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30 dark:text-lsc-rose-light',
  success: 'bg-status-success-100 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-400',
  warning: 'bg-status-warning-100 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  danger: 'bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400',
}

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  color?: 'accent' | 'success' | 'warning' | 'danger'
  trend?: number
}

export function StatCard({
  title,
  value,
  icon: Icon,
  color = 'accent',
  trend,
}: StatCardProps): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{value}</p>
          {trend !== undefined && (
            <p className={`text-xs mt-1 ${trend >= 0 ? 'text-status-success-600' : 'text-status-danger-600'}`}>
              {trend >= 0 ? '+' : ''}{trend.toFixed(1)}% from last month
            </p>
          )}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}
