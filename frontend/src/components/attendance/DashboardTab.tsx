/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck, Users, TrendingUp, BarChart3, Hash, RefreshCw, Loader2 } from 'lucide-react'
import { getAttendanceDashboard, type AttendanceDashboard } from '../../api/attendance-api'
import { useTranslation } from '@/i18n'
import { AGE_RANGES, METHOD_LABELS } from './attendance-data'
import { StatusBadge } from './StatusBadge'

export function DashboardTab() {
  const { t } = useTranslation();
  const { data: dashboard, isLoading } = useQuery<AttendanceDashboard>({
    queryKey: ['attendance-dashboard'],
    queryFn: getAttendanceDashboard,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" size={32} />
      </div>
    )
  }

  if (!dashboard) {
    return <p className="text-lsc-dark/70 dark:text-lsc-cream/70 py-8 text-center">{t('attendanceTracking.noDataAvailableYet')}</p>
  }

  const stats = [
    { label: "Today's Sessions", value: dashboard.today_sessions, icon: <CalendarCheck size={20} /> },
    { label: "Today's Attendance", value: dashboard.today_total_attendance, icon: <Users size={20} /> },
    { label: 'This Week', value: dashboard.week_total_attendance, icon: <TrendingUp size={20} /> },
    { label: 'This Month', value: dashboard.month_total_attendance, icon: <BarChart3 size={20} /> },
    { label: 'Avg per Event', value: dashboard.avg_attendance_per_event, icon: <Hash size={20} /> },
    { label: 'Repeat Rate', value: `${dashboard.repeat_attendee_rate}%`, icon: <RefreshCw size={20} /> },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700"
          >
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs mb-1">
              {stat.icon}
              {stat.label}
            </div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Check-In Methods (30 days)</h3>
          {Object.entries(dashboard.method_distribution).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(dashboard.method_distribution)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([method, count]) => {
                  const total = Object.values(dashboard.method_distribution).reduce(
                    (a, b) => (a as number) + (b as number), 0
                  ) as number
                  const pct = total > 0 ? Math.round(((count as number) / total) * 100) : 0
                  return (
                    <div key={method}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {METHOD_LABELS[method] || method}
                        </span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {count as number} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full bg-lsc-cream dark:bg-earth-700 rounded-full h-2">
                        <div
                          className="bg-earth-500 h-2 rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
            </div>
          ) : (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.noCheckInDataYet')}</p>
          )}
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Age Distribution (30 days)</h3>
          {Object.entries(dashboard.age_distribution).length > 0 ? (
            <div className="space-y-2">
              {AGE_RANGES.filter(({ value }) => dashboard.age_distribution[value])
                .map(({ value, label }) => {
                  const count = dashboard.age_distribution[value] || 0
                  const total = Object.values(dashboard.age_distribution).reduce(
                    (a, b) => (a as number) + (b as number), 0
                  ) as number
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={value}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full bg-lsc-cream dark:bg-earth-700 rounded-full h-2">
                        <div
                          className="bg-status-success-500 h-2 rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
            </div>
          ) : (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.noAttendanceDataYet')}</p>
          )}
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
        <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Recent Sessions</h3>
        {dashboard.recent_sessions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lsc-dark/70 dark:text-lsc-cream/70 border-b dark:border-earth-700">
                  <th className="py-2 pr-4">Session</th>
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4 text-right">Attendance</th>
                  <th className="py-2 text-right">Cost/Person</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_sessions.map((s) => (
                  <tr key={s.id as number} className="border-b dark:border-earth-700 last:border-0">
                    <td className="py-2 pr-4 font-medium text-lsc-dark dark:text-lsc-cream">
                      {s.session_name as string}
                    </td>
                    <td className="py-2 pr-4 text-lsc-dark/70 dark:text-lsc-cream/70">{s.session_date as string}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={s.status as string} />
                    </td>
                    <td className="py-2 pr-4 text-right font-medium text-lsc-dark dark:text-lsc-cream">
                      {s.effective_total as number}
                    </td>
                    <td className="py-2 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                      {(s.cost_per_attendee as number | null) != null ? `$${s.cost_per_attendee}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.noSessionsYetCreateYour')}</p>
        )}
      </div>
    </div>
  )
}
