/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getSuccessMetrics } from '@/api/program-planning-api'
import { BarChart3, Download, LayoutGrid, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import { PROGRAM_TYPES } from '../constants'
import { parseDate } from '@/utils/format-utils'

function SuccessMetricsTab() {
  const { t } = useTranslation();
  const [programType, setProgramType] = useState('')
  const [view, setView] = useState<'table' | 'matrix'>('table')

  const { data: metricsData, isLoading } = useQuery({
    queryKey: ['success-metrics', programType],
    queryFn: () => getSuccessMetrics(clean({
      program_type: programType || undefined,
      limit: 20,
    })),
  })

  const downloadMetricsCSV = () => {
    if (!metricsData) return
    const summary = metricsData.summary as Record<string, number> | null
    const headers = ['Program', 'Date', 'Attendance', 'Target', 'Rate (%)', 'Budget ($)', 'Cost/Person ($)', 'Rating', 'Recommend Repeat']
    const rows: string[][] = [headers]
    if (summary) {
      rows.push([
        'SUMMARY',
        '',
        String(summary.average_attendance ?? ''),
        '',
        '',
        '',
        '',
        '',
        String(summary.programs_recommended_repeat ?? ''),
      ])
    }
    for (const p of metricsData.programs) {
      rows.push([
        p.program_title,
        p.program_date,
        p.attendance != null ? String(p.attendance) : '',
        p.target_attendance != null ? String(p.target_attendance) : '',
        p.attendance_rate != null ? String(p.attendance_rate) : '',
        p.total_spent != null ? String(p.total_spent) : '',
        p.cost_per_attendee != null ? String(p.cost_per_attendee) : '',
        p.overall_rating ?? '',
        p.recommend_repeat != null ? (p.recommend_repeat ? 'Yes' : 'No') : '',
      ])
    }
    const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `program-metrics-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const renderMatrix = () => {
    if (!metricsData?.programs.length) return null
    const eligible = metricsData.programs.filter(p => p.attendance_rate != null && p.cost_per_attendee != null)
    if (eligible.length < 2) {
      return (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <LayoutGrid className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Need at least 2 programs with attendance rate and cost data for the matrix view.</p>
        </div>
      )
    }
    const rates = eligible.map(p => p.attendance_rate!).sort((a, b) => a - b)
    const costs = eligible.map(p => p.cost_per_attendee!).sort((a, b) => a - b)
    const median = (arr: number[]): number => {
      const mid = Math.floor(arr.length / 2)
      return arr.length % 2 ? arr[mid]! : (arr[mid - 1]! + arr[mid]!) / 2
    }
    const medianRate = median(rates)!
    const medianCost = median(costs)!

    const quadrants = {
      stars: eligible.filter(p => p.attendance_rate! >= medianRate && p.cost_per_attendee! <= medianCost),
      expensiveHits: eligible.filter(p => p.attendance_rate! >= medianRate && p.cost_per_attendee! > medianCost),
      tryMarketing: eligible.filter(p => p.attendance_rate! < medianRate && p.cost_per_attendee! <= medianCost),
      retire: eligible.filter(p => p.attendance_rate! < medianRate && p.cost_per_attendee! > medianCost),
    }

    const quadrantStyle = "rounded-lg p-4 min-h-[140px]"
    const titleStyle = "font-semibold text-sm mb-2"
    const listStyle = "text-xs space-y-1"

    return (
      <div>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-3 text-center">
          Median attendance rate: {medianRate}% &middot; Median cost/person: ${medianCost.toFixed(2)}
        </p>
        <div className="grid grid-cols-2 gap-3">
          {/* Top-left: Expensive Hits (high attendance, high cost) */}
          <div className={`${quadrantStyle} bg-status-warning-50 dark:bg-status-warning-900/30 border border-status-warning-200 dark:border-status-warning-800`}>
            <p className={`${titleStyle} text-status-warning-800 dark:text-status-warning-200`}>Expensive Hits</p>
            <ul className={`${listStyle} text-status-warning-700 dark:text-status-warning-300`}>
              {quadrants.expensiveHits.length ? quadrants.expensiveHits.map(p => (
                <li key={p.program_id}>{p.program_title} ({p.attendance_rate}%, ${p.cost_per_attendee})</li>
              )) : <li className="italic opacity-60">None</li>}
            </ul>
          </div>
          {/* Top-right: Stars (high attendance, low cost) */}
          <div className={`${quadrantStyle} bg-status-success-50 dark:bg-status-success-900/30 border border-status-success-200 dark:border-status-success-800`}>
            <p className={`${titleStyle} text-status-success-800 dark:text-status-success-200`}>Stars &mdash; Repeat These</p>
            <ul className={`${listStyle} text-status-success-700 dark:text-status-success-300`}>
              {quadrants.stars.length ? quadrants.stars.map(p => (
                <li key={p.program_id}>{p.program_title} ({p.attendance_rate}%, ${p.cost_per_attendee})</li>
              )) : <li className="italic opacity-60">None</li>}
            </ul>
          </div>
          {/* Bottom-left: Consider Retiring (low attendance, high cost) */}
          <div className={`${quadrantStyle} bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-800`}>
            <p className={`${titleStyle} text-status-danger-800 dark:text-status-danger-200`}>Consider Retiring</p>
            <ul className={`${listStyle} text-status-danger-700 dark:text-status-danger-300`}>
              {quadrants.retire.length ? quadrants.retire.map(p => (
                <li key={p.program_id}>{p.program_title} ({p.attendance_rate}%, ${p.cost_per_attendee})</li>
              )) : <li className="italic opacity-60">None</li>}
            </ul>
          </div>
          {/* Bottom-right: Try Better Marketing (low attendance, low cost) */}
          <div className={`${quadrantStyle} bg-status-info-50 dark:bg-status-info-900/30 border border-status-info-200 dark:border-status-info-800`}>
            <p className={`${titleStyle} text-status-info-800 dark:text-status-info-200`}>Try Better Marketing</p>
            <ul className={`${listStyle} text-status-info-700 dark:text-status-info-300`}>
              {quadrants.tryMarketing.length ? quadrants.tryMarketing.map(p => (
                <li key={p.program_id}>{p.program_title} ({p.attendance_rate}%, ${p.cost_per_attendee})</li>
              )) : <li className="italic opacity-60">None</li>}
            </ul>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70">
          <p className="text-right">High Cost &larr;</p>
          <p>&rarr; Low Cost</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Success Metrics Comparison
        </h2>
        <div className="flex items-center gap-2">
          {metricsData?.programs.length ? (
            <button
              onClick={downloadMetricsCSV}
              className="bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg px-3 py-2 flex items-center gap-1.5 text-sm hover:opacity-80 transition-opacity"
            >
              <Download className="w-4 h-4" />
              Download CSV
            </button>
          ) : null}
          <select
            value={programType}
            onChange={e => setProgramType(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Types</option>
            {PROGRAM_TYPES.map(t => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary */}
      {metricsData?.summary && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">Total Programs</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {(metricsData.summary as Record<string, number>).total_programs ?? 0}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">Avg Attendance</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {(metricsData.summary as Record<string, number>).average_attendance ?? '---'}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">Recommended Repeat</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {(metricsData.summary as Record<string, number>).programs_recommended_repeat ?? 0}
            </p>
          </div>
        </div>
      )}

      {/* View Toggle */}
      {metricsData?.programs.length ? (
        <div className="flex gap-1 mb-4">
          <button
            onClick={() => setView('table')}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition-colors ${
              view === 'table'
                ? 'bg-earth-200 dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium'
                : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-earth-100 dark:hover:bg-earth-700'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Table
          </button>
          <button
            onClick={() => setView('matrix')}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1.5 transition-colors ${
              view === 'matrix'
                ? 'bg-earth-200 dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium'
                : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-earth-100 dark:hover:bg-earth-700'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
            Matrix
          </button>
        </div>
      ) : null}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600 dark:text-earth-200" />
        </div>
      ) : !metricsData?.programs.length ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <BarChart3 className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('programPlanning.noCompletedProgramsWithMetrics')}</p>
        </div>
      ) : view === 'matrix' ? (
        renderMatrix()
      ) : (
        <div className="overflow-x-auto bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="text-left p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Program</th>
                <th className="text-left p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Date</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Attendance</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Target</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Rate</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Budget</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Cost/Person</th>
                <th className="text-center p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Rating</th>
                <th className="text-center p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Repeat?</th>
              </tr>
            </thead>
            <tbody>
              {metricsData.programs.map(p => (
                <tr key={p.program_id} className="border-b border-earth-100 dark:border-earth-700 last:border-0">
                  <td className="p-3 text-lsc-dark dark:text-lsc-cream font-medium">{p.program_title}</td>
                  <td className="p-3 text-lsc-dark/70 dark:text-lsc-cream/70">{parseDate(p.program_date)?.toLocaleDateString() ?? '-'}</td>
                  <td className="p-3 text-right text-lsc-dark dark:text-lsc-cream">{p.attendance ?? '---'}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{p.target_attendance ?? '---'}</td>
                  <td className="p-3 text-right">
                    {p.attendance_rate != null ? (
                      <span className={p.attendance_rate >= 80 ? 'text-status-success-700 dark:text-status-success-300' : p.attendance_rate >= 50 ? 'text-status-warning-700 dark:text-status-warning-300' : 'text-status-danger-700 dark:text-status-danger-300'}>
                        {p.attendance_rate}%
                      </span>
                    ) : '---'}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {p.total_spent != null ? `$${p.total_spent}` : '---'}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {p.cost_per_attendee != null ? `$${p.cost_per_attendee}` : '---'}
                  </td>
                  <td className="p-3 text-center">
                    {p.overall_rating ? (
                      <span className={`px-2 py-0.5 rounded-full text-xs ${
                        p.overall_rating === 'excellent' ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' :
                        p.overall_rating === 'good' ? 'bg-earth-100 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80' :
                        'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200'
                      }`}>
                        {p.overall_rating}
                      </span>
                    ) : '---'}
                  </td>
                  <td className="p-3 text-center">
                    {p.recommend_repeat != null ? (p.recommend_repeat ? 'Yes' : 'No') : '---'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default SuccessMetricsTab
