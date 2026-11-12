/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BarChart3, Download } from 'lucide-react'

interface Props {
  onRegenerateStats: () => void
  onExport: (type: string) => void
}

export function ReportsTab({ onRegenerateStats, onExport }: Props) {
  return (
    <div className="space-y-4">
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        <button
          onClick={onRegenerateStats}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose transition-colors text-left"
        >
          <BarChart3 className="w-8 h-8 text-lsc-rose mb-3" />
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Regenerate Statistics</h4>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Recalculate outreach statistics for a specific period
          </p>
        </button>

        {[
          { key: 'partners', label: 'Export Partners', desc: 'Download partner data as CSV' },
          { key: 'visits', label: 'Export Visits', desc: 'Download visit data as CSV' },
          { key: 'checkouts', label: 'Export Checkouts', desc: 'Download bulk checkout data as CSV' },
          { key: 'deposits', label: 'Export Deposits', desc: 'Download deposit data as CSV' },
          { key: 'cards', label: 'Export Inst. Cards', desc: 'Download institutional card data as CSV' },
        ].map((item) => (
          <button
            key={item.key}
            onClick={() => onExport(item.key)}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose transition-colors text-left"
          >
            <Download className="w-8 h-8 text-lsc-rose mb-3" />
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{item.label}</h4>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
