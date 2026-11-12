/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { CalendarDays } from "lucide-react"
import { getCurrentLocale } from '@/i18n'

const LIBRARY_TIMEZONE = "America/New_York"

function getParts(): { weekday: string; month: string; day: string; year: string } {
  const now = new Date()
  const weekday = now.toLocaleDateString(getCurrentLocale(), { weekday: "long", timeZone: LIBRARY_TIMEZONE })
  const month = now.toLocaleDateString(getCurrentLocale(), { month: "short", timeZone: LIBRARY_TIMEZONE })
  const day = now.toLocaleDateString(getCurrentLocale(), { day: "numeric", timeZone: LIBRARY_TIMEZONE })
  const year = now.toLocaleDateString(getCurrentLocale(), { year: "numeric", timeZone: LIBRARY_TIMEZONE })
  return { weekday, month, day, year }
}

export default function TodayCard(): React.ReactElement {
  const [parts, setParts] = useState(getParts)

  useEffect(() => {
    const id = setInterval(() => setParts(getParts()), 60_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div
      role="region"
      aria-label="Today"
      className="rounded-xl bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 p-4 flex items-center gap-3"
    >
      <div className="shrink-0 w-12 h-12 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
        <CalendarDays className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-earth-600 dark:text-earth-400 uppercase tracking-wider">
          Today
        </p>
        <p className="text-base font-serif font-bold text-lsc-dark dark:text-lsc-cream truncate">
          {parts.weekday}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {parts.month} {parts.day}, {parts.year}
        </p>
      </div>
    </div>
  )
}
