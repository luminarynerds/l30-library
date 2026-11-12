/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Sparkles, Check } from 'lucide-react'
import { useTone } from '@/contexts/ToneContext'
import type { NeedsPromoProgram } from '@/api/staff-api/marketing-dashboard'

interface Props {
  programs: NeedsPromoProgram[]
}

export default function MarketingNeedsPromo({ programs }: Props) {
  const { formatDeadline, showUrgencyColors } = useTone()

  if (programs.length === 0) return null

  const unpromoted = programs.filter(p => !p.has_marketing_campaign)

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">
        Upcoming programs
        {unpromoted.length > 0 && (
          <span className={`ml-1 ${showUrgencyColors ? 'text-status-warning-600 dark:text-status-warning-400' : ''}`}>
            ({unpromoted.length} need promo)
          </span>
        )}
      </p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {programs.map(p => (
          <div key={p.id} className="flex items-center gap-3 px-4 py-3">
            <div className="w-16 flex-shrink-0">
              <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/70">
                {formatDeadline(p.program_date)}
              </p>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">{p.title}</p>
              <p className="text-[11px] text-lsc-dark/50 dark:text-lsc-cream/50">{p.audience} {p.location ? `-- ${p.location}` : ''}</p>
            </div>
            <div className="flex-shrink-0">
              {p.has_marketing_campaign ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-status-success-600 dark:text-status-success-400">
                  <Check className="w-3 h-3" aria-hidden="true" />
                  Promoted
                </span>
              ) : (
                <Link
                  to="/staff/marketing-hub"
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  <Sparkles className="w-3 h-3" aria-hidden="true" />
                  Generate
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
