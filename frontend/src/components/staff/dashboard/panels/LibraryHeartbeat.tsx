/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Activity } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/services/dashboardApi'

interface PulseData {
  checkouts: number
  returns: number
  overdue: number
  activePatrons: number
}

export default function LibraryHeartbeat() {
  const { data } = useQuery<PulseData>({
    queryKey: ['staff-dashboard', 'library-heartbeat'],
    queryFn: async () => {
      const [comp, patrons, circ] = await Promise.all([
        dashboardApi.getComparisonStats(),
        dashboardApi.getActivePatrons(),
        dashboardApi.getCirculationSnapshot(),
      ])
      return {
        checkouts: comp.checkouts_today,
        returns: comp.returns_today,
        overdue: circ.overdue_items,
        activePatrons: patrons.active_today,
      }
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  if (!data) return null

  const stats = [
    { value: data.checkouts, label: 'Checked out' },
    { value: data.returns, label: 'Returned' },
    { value: data.overdue, label: 'Overdue' },
    { value: data.activePatrons, label: 'Patrons today' },
  ]

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-soft-sm">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-lsc-rose" />
        <h4 className="text-xs font-semibold text-earth-600 dark:text-earth-400 uppercase tracking-wider">
          Library Pulse
        </h4>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => (
          <div key={s.label}>
            <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{s.value}</div>
            <div className="text-xs text-earth-600 dark:text-earth-300">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
