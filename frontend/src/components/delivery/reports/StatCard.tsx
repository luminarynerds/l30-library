/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TrendingUp, TrendingDown } from "lucide-react"

export function StatCard({
  label,
  value,
  sub,
  icon,
  color = 'text-lsc-dark dark:text-lsc-cream',
  trend,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  color?: string
  trend?: { direction: 'up' | 'down'; value: string }
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">{icon}</div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium ${trend.direction === 'up' ? 'text-status-success-600 dark:text-status-success-400' : 'text-status-danger-600 dark:text-status-danger-400'}`}>
            {trend.direction === 'up' ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {trend.value}
          </div>
        )}
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      {sub && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{sub}</p>}
    </div>
  )
}
