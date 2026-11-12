/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CalendarDays, MapPin, Users } from 'lucide-react'
import { useTone } from '@/contexts/ToneContext'
import type { KidsProgramSummary } from '@/api/staff-api/kids-dashboard'
import { getCurrentLocale } from '@/i18n'

function formatCountdown(dateStr: string): string {
  const target = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diffDays = Math.round((target.getTime() - now.getTime()) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  return `In ${diffDays} days`
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
  program: KidsProgramSummary | null
}

export default function KidsNextProgram({ program }: Props) {
  const { tone, showCountBadges } = useTone()

  if (!program) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-1">Next program</p>
        <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">No upcoming programs scheduled.</p>
      </div>
    )
  }

  const registrationLabel = program.capacity
    ? `${program.registration_count} / ${program.capacity}`
    : `${program.registration_count} registered`

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Next program</p>
        {tone !== 'calm' && (
          <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">
            {formatCountdown(program.program_date)}
          </span>
        )}
      </div>
      <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{program.title}</h3>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="flex items-center gap-1.5">
          <CalendarDays className="w-3.5 h-3.5" aria-hidden="true" />
          {formatDate(program.program_date)} at {formatTime(program.start_time)}
        </span>
        {program.location_name && (
          <span className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
            {program.location_name}
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" aria-hidden="true" />
          {showCountBadges ? registrationLabel : 'Registered'}
        </span>
      </div>
      {program.notes && tone !== 'calm' && (
        <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-2">{program.notes}</p>
      )}
    </div>
  )
}
