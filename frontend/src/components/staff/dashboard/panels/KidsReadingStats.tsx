/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTone } from '@/contexts/ToneContext'
import type { KidsReadingStats as ReadingStatsType } from '@/api/staff-api/kids-dashboard'

interface Props {
  stats: ReadingStatsType
}

export default function KidsReadingStats({ stats }: Props) {
  const { showCountBadges } = useTone()

  const cells = [
    { label: 'Active reading programs', value: stats.active_program_count },
    { label: 'Total enrollments', value: stats.total_enrollments },
  ]

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Reading programs</p>
      <div className="grid grid-cols-2 gap-3">
        {cells.map(c => (
          <div key={c.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mb-1">{c.label}</p>
            <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
              {showCountBadges ? c.value : c.value > 0 ? 'Active' : '--'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
