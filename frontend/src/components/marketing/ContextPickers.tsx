/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Calendar } from 'lucide-react'
import type { ProgramSummary, EventSummary } from '@/api/marketing-hub-api'

interface ContextPickersProps {
  selectedProgramId: number | undefined
  setSelectedProgramId: (id: number | undefined) => void
  selectedEventId: number | undefined
  setSelectedEventId: (id: number | undefined) => void
  programs: ProgramSummary[]
  events: EventSummary[]
  t: (key: string) => string
}

export default function ContextPickers({
  selectedProgramId, setSelectedProgramId,
  selectedEventId, setSelectedEventId,
  programs, events, t,
}: ContextPickersProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          <BookOpen className="w-4 h-4 inline mr-1" aria-hidden="true" />
          Reading Program (optional)
        </label>
        <select
          value={selectedProgramId ?? ''}
          onChange={(e) => setSelectedProgramId(e.target.value ? Number(e.target.value) : undefined)}
          className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">{t('components.marketing.aIContentGenerator.noneNoProgramContext')}</option>
          {programs.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.program_type})
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          <Calendar className="w-4 h-4 inline mr-1" aria-hidden="true" />
          Event (optional)
        </label>
        <select
          value={selectedEventId ?? ''}
          onChange={(e) => setSelectedEventId(e.target.value ? Number(e.target.value) : undefined)}
          className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">{t('components.marketing.aIContentGenerator.noneNoEventContext')}</option>
          {events.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}{e.start_time ? ` - ${new Date(e.start_time).toLocaleDateString()}` : ''}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
