/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Leaf, TrendingDown, TrendingUp, BarChart3, Loader2 } from 'lucide-react'
import api from '@/lib/api-client'
import { getCurrentLocale } from '@/i18n'

interface MonthlyData {
  month: string
  total_bytes: number
  total_requests: number
  total_co2_grams: number
  avg_co2_per_request: number
}

interface SectionData {
  section: string
  total_bytes: number
  total_requests: number
  total_co2_grams: number
}

export function CarbonMetricsCard() {
  const [monthly, setMonthly] = useState<MonthlyData[]>([])
  const [sections, setSections] = useState<SectionData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.get<{ months: MonthlyData[] }>('/carbon-metrics/admin/summary?months=6'),
      api.get<{ sections: SectionData[] }>('/carbon-metrics/admin/breakdown?days=30'),
    ]).then(([monthlyRes, sectionsRes]) => {
      if (monthlyRes.status === 'fulfilled') setMonthly(monthlyRes.value.months)
      if (sectionsRes.status === 'fulfilled') setSections(sectionsRes.value.sections)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Leaf className="w-5 h-5 text-status-success-600" />
          <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">Carbon Footprint</h3>
        </div>
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/30" />
        </div>
      </div>
    )
  }

  const currentMonth = monthly[monthly.length - 1]
  const prevMonth = monthly[monthly.length - 2]
  const trend = currentMonth && prevMonth
    ? ((currentMonth.total_co2_grams - prevMonth.total_co2_grams) / prevMonth.total_co2_grams) * 100
    : null
  const totalSections = sections.reduce((sum, s) => sum + s.total_co2_grams, 0)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Leaf className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
          <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">Carbon Footprint</h3>
        </div>
        {trend !== null && (
          <div className={`flex items-center gap-1 text-xs font-medium ${trend <= 0 ? 'text-status-success-600' : 'text-status-danger-600'}`}>
            {trend <= 0 ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
            {Math.abs(trend).toFixed(1)}% vs last month
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {currentMonth ? (currentMonth.total_co2_grams / 1000).toFixed(2) : '0'}
          </p>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">kg CO2 this month</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {currentMonth ? currentMonth.avg_co2_per_request.toFixed(3) : '0'}
          </p>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">g per page view</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {currentMonth ? currentMonth.total_requests.toLocaleString() : '0'}
          </p>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">requests this month</p>
        </div>
      </div>

      {sections.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" />
            <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">By section (30 days)</span>
          </div>
          <div className="space-y-2">
            {sections.slice(0, 5).map((s) => {
              const pct = totalSections > 0 ? (s.total_co2_grams / totalSections) * 100 : 0
              return (
                <div key={s.section} className="flex items-center gap-2">
                  <span className="text-xs w-16 text-lsc-dark/60 dark:text-lsc-cream/60 capitalize">
                    {s.section}
                  </span>
                  <div className="flex-1 h-2 bg-earth-100 dark:bg-earth-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-status-success-500 dark:bg-status-success-400 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs w-12 text-right text-lsc-dark/60 dark:text-lsc-cream/60">
                    {pct.toFixed(0)}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {monthly.length > 1 && (
        <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">6-month trend</span>
          <div className="flex items-end gap-1 h-12 mt-2">
            {monthly.map((m, i) => {
              const max = Math.max(...monthly.map(x => x.total_co2_grams))
              const height = max > 0 ? (m.total_co2_grams / max) * 100 : 0
              return (
                <div
                  key={i}
                  className="flex-1 bg-status-success-200 dark:bg-status-success-800 rounded-t"
                  style={{ height: `${Math.max(height, 4)}%` }}
                  title={`${new Date(m.month).toLocaleDateString(getCurrentLocale(), { month: 'short' })}: ${(m.total_co2_grams / 1000).toFixed(2)}kg`}
                />
              )
            })}
          </div>
        </div>
      )}

      {monthly.length === 0 && sections.length === 0 && (
        <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 text-center py-4">
          Data collection in progress. Metrics will appear after the first aggregation cycle.
        </p>
      )}
    </div>
  )
}
