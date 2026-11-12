/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FileText, Award } from 'lucide-react'
import { AnimatedCounter } from './DemoAnimations'

export function CommunityValueScene() {
  const valueCategories = [
    { category: 'Books & Media Borrowed', usage: '48,293 items', unitValue: '$15.00 avg retail', totalValue: '$724,395', pct: 60 },
    { category: 'Computer & WiFi Hours', usage: '12,400 hours', unitValue: '$12.00/hr market rate', totalValue: '$148,800', pct: 12 },
    { category: 'Program Attendance', usage: '3,420 attendees', unitValue: '$25.00 equiv. class', totalValue: '$85,500', pct: 7 },
    { category: 'Meeting Room Usage', usage: '890 bookings', unitValue: '$50.00 rental equiv.', totalValue: '$44,500', pct: 4 },
    { category: 'Reference & Research Help', usage: '4,100 sessions', unitValue: '$35.00/consult equiv.', totalValue: '$143,500', pct: 12 },
    { category: 'Digital Resources Access', usage: '6,200 uses', unitValue: '$10.00 subscription equiv.', totalValue: '$62,000', pct: 5 },
  ]

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-rose-500 to-pink-500 rounded-xl p-8 text-white text-center">
        <p className="text-sm uppercase tracking-wider opacity-90 mb-1">Return on Investment</p>
        <div className="text-6xl font-bold mb-2">
          $<AnimatedCounter end={4} duration={1000} />.<AnimatedCounter end={62} duration={1500} />
        </div>
        <p className="text-lg opacity-90">returned for every $1 invested</p>
        <div className="mt-4 flex items-center justify-center gap-8 text-sm">
          <div>
            <div className="text-2xl font-bold">$<AnimatedCounter end={1208} duration={2000} />K</div>
            <div className="opacity-75">Community Value</div>
          </div>
          <div className="text-3xl opacity-50">/</div>
          <div>
            <div className="text-2xl font-bold">$<AnimatedCounter end={260} duration={1500} />K</div>
            <div className="opacity-75">Annual Budget</div>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <FileText className="w-4 h-4 text-rose-700" />
            Value Breakdown by Service
          </h4>
          <span className="text-xs text-earth-600 bg-earth-100 dark:bg-earth-700 px-2 py-1 rounded">FY 2025-2026</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-earth-50 dark:bg-earth-700/50">
              <tr>
                <th className="text-left p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Service</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Usage</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Unit Value</th>
                <th className="text-right p-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Total Value</th>
              </tr>
            </thead>
            <tbody>
              {valueCategories.map((row) => (
                <tr key={row.category} className="border-t border-earth-100 dark:border-earth-700">
                  <td className="p-3 text-lsc-dark dark:text-lsc-cream font-medium">{row.category}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{row.usage}</td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{row.unitValue}</td>
                  <td className="p-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream">{row.totalValue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg p-4 border border-status-warning-200 dark:border-status-warning-800 flex items-start gap-3">
        <Award className="w-5 h-5 text-status-warning-600 shrink-0 mt-0.5" />
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <strong>Board-ready export:</strong> This report can be exported as PDF with one click for grant applications,
          city council presentations, and annual reports. All figures are calculated from actual system usage data.
        </div>
      </div>
    </div>
  )
}
