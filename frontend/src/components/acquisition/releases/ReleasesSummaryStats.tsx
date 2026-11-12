/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Calendar, Clock, TrendingUp } from "lucide-react"

interface Props {
  total: number
  thisWeek: number
  thisMonth: number
  highDemand: number
  newOnly: number
}

export default function ReleasesSummaryStats({ total, thisWeek, thisMonth, highDemand, newOnly }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <BookOpen aria-hidden="true" className="w-4 h-4" />
          Total Upcoming
        </div>
        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{total}</p>
      </div>
      <div className="bg-earth-50 dark:bg-earth-800/20 rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-lsc-rose dark:text-lsc-rose-light">
          <Clock aria-hidden="true" className="w-4 h-4" />
          This Week
        </div>
        <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light mt-1">{thisWeek}</p>
      </div>
      <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-status-success-600 dark:text-status-success-400">
          <Calendar aria-hidden="true" className="w-4 h-4" />
          This Month
        </div>
        <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-300 mt-1">{thisMonth}</p>
      </div>
      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-lsc-rose">
          <TrendingUp aria-hidden="true" className="w-4 h-4" />
          High Demand
        </div>
        <p className="text-2xl font-bold text-lsc-rose mt-1">{highDemand}</p>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{newOnly} not in library</p>
      </div>
    </div>
  )
}
