/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, DollarSign, Loader2 } from 'lucide-react'
import { getROIReport, type ROIReport } from '../../api/attendance-api'
import { useTranslation } from '@/i18n'
import { StatCard } from './StatCard'

export function TrendsTab() {
  const { t } = useTranslation();
  const { data: roi, isLoading } = useQuery<ROIReport>({
    queryKey: ['attendance-roi'],
    queryFn: () => getROIReport(),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" size={24} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {roi && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 flex items-center gap-2">
            <DollarSign size={16} />
            ROI Report — {roi.period_label}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard label="Total Events" value={roi.total_events} />
            <StatCard label="Total Attendance" value={roi.total_attendance} />
            <StatCard label="Total Cost" value={`$${roi.total_cost.toLocaleString()}`} />
            <StatCard label="Cost/Attendee" value={`$${roi.cost_per_attendee}`} />
            <StatCard label="Repeat Rate" value={`${roi.repeat_rate}%`} />
          </div>

          {roi.top_programs.length > 0 && (
            <div className="mt-5">
              <h4 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide mb-2">
                Top Programs by Attendance
              </h4>
              <div className="space-y-2">
                {roi.top_programs.slice(0, 5).map((prog, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{prog.name}</span>
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">{prog.attendance}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!roi && (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <TrendingUp size={40} className="mx-auto text-earth-600 dark:text-earth-600 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.noTrendDataAvailableYet')}</p>
        </div>
      )}
    </div>
  )
}
