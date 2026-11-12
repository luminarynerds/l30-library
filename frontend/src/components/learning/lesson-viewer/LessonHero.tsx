/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, Clock } from 'lucide-react'

interface Props {
  title: string
  estimatedMinutes: number | null
  sensoryNotes: string | null
}

export function LessonHero({ title, estimatedMinutes, sensoryNotes }: Props) {
  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {title}
        </h1>
        <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {estimatedMinutes && (
            <span className="flex items-center gap-1">
              <Clock aria-hidden="true" className="w-4 h-4" />~{estimatedMinutes} min
            </span>
          )}
        </div>
      </div>

      {sensoryNotes && (
        <div className="flex items-start gap-3 bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-800 text-lsc-rose dark:text-lsc-rose-light px-4 py-3 rounded-xl mb-6">
          <AlertTriangle aria-hidden="true" className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div>
            <strong className="font-medium">Sensory Note:</strong> {sensoryNotes}
          </div>
        </div>
      )}
    </>
  )
}
