/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { listTemplates, getMarketingReminders, getSuccessMetrics } from '@/api/program-planning-api'
import { BookOpen, Bell, Clock, Target } from 'lucide-react'

function QuickStats() {
  const { data: templates } = useQuery({
    queryKey: ['program-templates', '', true],
    queryFn: () => listTemplates({ active_only: true }),
    staleTime: 60_000,
  })

  const { data: reminders } = useQuery({
    queryKey: ['marketing-reminders', 7],
    queryFn: () => getMarketingReminders(7),
    staleTime: 60_000,
  })

  const { data: metrics } = useQuery({
    queryKey: ['success-metrics'],
    queryFn: () => getSuccessMetrics({ limit: 100 }),
    staleTime: 60_000,
  })

  const overdueCount = reminders?.filter(r => new Date(r.due_date) <= new Date()).length ?? 0

  const stats = [
    { label: 'Templates', value: templates?.length ?? 0, icon: BookOpen, color: 'text-lsc-rose dark:text-lsc-rose-light' },
    { label: 'Upcoming Reminders', value: reminders?.length ?? 0, icon: Bell, color: 'text-status-warning-600' },
    { label: 'Overdue Tasks', value: overdueCount, icon: Clock, color: 'text-status-danger-500' },
    { label: 'Programs Tracked', value: metrics?.programs?.length ?? 0, icon: Target, color: 'text-status-success-600' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map(stat => (
        <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-1">
            <stat.icon className={`w-4 h-4 ${stat.color}`} />
            <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">
              {stat.label}
            </span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
        </div>
      ))}
    </div>
  )
}

export default QuickStats
