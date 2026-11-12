/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTone } from '@/contexts/ToneContext'
import type { KidsProgramSummary } from '@/api/staff-api/kids-dashboard'
import { getCurrentLocale } from '@/i18n'

const AUDIENCE_LABELS: Record<string, string> = {
  children: 'KIDS',
  teen: 'TEEN',
  family: 'FAMILY',
  all_ages: 'ALL',
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

function formatTime(timeStr: string): string {
  const [h, m] = timeStr.split(':')
  const hour = parseInt(h ?? '0')
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour
  return `${h12}:${m} ${ampm}`
}

interface Props {
  programs: KidsProgramSummary[]
}

export default function KidsUpcomingPrograms({ programs }: Props) {
  const { showCountBadges } = useTone()

  if (programs.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Upcoming programs</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {programs.map(p => (
          <div key={p.id} className="flex items-center gap-3 px-4 py-3">
            <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 min-w-[120px]">
              {formatDate(p.program_date)}
              <br />
              {formatTime(p.start_time)}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{p.title}</p>
              {p.location_name && (
                <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{p.location_name}</p>
              )}
            </div>
            <span className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark/70 dark:text-lsc-cream/70">
              {AUDIENCE_LABELS[p.audience] ?? p.audience}
            </span>
            {showCountBadges && (
              <span className="text-xs tabular-nums text-lsc-dark/50 dark:text-lsc-cream/50 min-w-[2rem] text-right">
                {p.registration_count}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
