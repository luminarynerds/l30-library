/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Mail, Share2 } from 'lucide-react'
import { useTone } from '@/contexts/ToneContext'
import type { InFlight } from '@/api/staff-api/marketing-dashboard'

interface Props {
  data: InFlight
}

export default function MarketingInFlight({ data }: Props) {
  const { formatDeadline } = useTone()
  const nl = data.newsletter
  const sq = data.social_queue

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">In flight</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Newsletter card */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Mail className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/70">Newsletter</p>
          </div>
          {nl.id ? (
            <>
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">{nl.name}</p>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mt-0.5">
                {nl.status === 'scheduled' && nl.scheduled_for
                  ? `Scheduled ${formatDeadline(nl.scheduled_for)}`
                  : 'Draft'}
              </p>
              <div className="mt-3">
                <div className="flex items-center justify-between text-[11px] text-lsc-dark/50 dark:text-lsc-cream/50 mb-1">
                  <span>Sections</span>
                  <span>{Math.round(nl.section_progress)}%</span>
                </div>
                <div className="h-1.5 bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-lsc-rose dark:bg-lsc-rose-light rounded-full transition-all"
                    style={{ width: `${nl.section_progress}%` }}
                  />
                </div>
              </div>
              <Link
                to="/staff/marketing-hub"
                className="inline-block mt-3 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Continue draft
              </Link>
            </>
          ) : (
            <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">No draft in progress</p>
          )}
        </div>

        {/* Social queue card */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Share2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/70">Social queue</p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">Scheduled</span>
              <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{sq.scheduled_count}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">Drafts</span>
              <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{sq.draft_count}</span>
            </div>
          </div>
          <Link
            to="/staff/marketing-hub"
            className="inline-block mt-3 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            View queue
          </Link>
        </div>
      </div>
    </div>
  )
}
