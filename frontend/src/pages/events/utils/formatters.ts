/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { getCurrentLanguage } from '@/i18n/translations'
import { t } from '@/i18n'

// Library wall-clock zone. L30 lives in Eastern. Anchored here so every
// /events render shows local time regardless of the viewer's browser tz.
// If we ever expose a server-side tz config, swap this for a runtime read.
export const LIBRARY_TIMEZONE = 'America/New_York'

// Active UI locale for date rendering. Reads the i18n module-level language
// (kept in sync by I18nProvider); components re-render on language change so
// render-time calls always see the fresh value.
export function getDateLocale(): string {
  return getCurrentLanguage()
}

export function formatTime(dateStr: string, locale: string = getDateLocale()): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(locale, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: LIBRARY_TIMEZONE,
  })
}

export function formatFullDate(dateStr: string, locale: string = getDateLocale()): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(locale, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: LIBRARY_TIMEZONE,
  })
}

function formatShortDay(date: Date, locale: string = getDateLocale()): string {
  return date.toLocaleDateString(locale, {
    weekday: 'short',
    timeZone: LIBRARY_TIMEZONE,
  })
}

function formatShortDate(date: Date, locale: string = getDateLocale()): string {
  return date.toLocaleDateString(locale, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: LIBRARY_TIMEZONE,
  })
}

function sameLibraryDay(a: Date, b: Date): boolean {
  // 'en-US' on purpose: output is only compared with itself, never rendered.
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: LIBRARY_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  return fmt.format(a) === fmt.format(b)
}

export function formatDurationMinutes(totalMinutes: number): string {
  if (!Number.isFinite(totalMinutes) || totalMinutes <= 0) return ''
  const minutes = Math.round(totalMinutes)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rem = minutes % 60
  if (rem === 0) return hours === 1 ? '1 hr' : `${hours} hrs`
  return hours === 1 ? `1 hr ${rem} min` : `${hours} hrs ${rem} min`
}

export interface FormatEventDateTimeRangeOptions {
  /** Include short date (e.g. "Fri, May 22") instead of just day name. */
  includeDate?: boolean
}

export function formatEventDateTimeRange(
  startStr: string,
  endStr?: string | null,
  opts: FormatEventDateTimeRangeOptions = {},
): string {
  const start = new Date(startStr)
  if (Number.isNaN(start.getTime())) return ''

  const end = endStr ? new Date(endStr) : null
  const endValid = end && !Number.isNaN(end.getTime())

  // No end -> just day + start time.
  if (!endValid) {
    return `${formatShortDay(start)}, ${formatTime(startStr)}`
  }

  const durationMs = end!.getTime() - start.getTime()
  const durationMin = durationMs / 60000

  // Multi-day event (>= 24h and straddles library-local day boundaries).
  if (durationMin >= 24 * 60 && !sameLibraryDay(start, end!)) {
    return `${formatShortDate(start)} - ${formatShortDate(end!)}`
  }

  // "All-day" heuristic: starts at library-local 00:00 and runs >= 23h.
  // Avoids labeling a normal 9am-5pm event as all-day.
  // 'en-US' on purpose: numeric-hour extraction, never rendered.
  const localHour = Number(
    new Intl.DateTimeFormat('en-US', {
      timeZone: LIBRARY_TIMEZONE,
      hour: 'numeric',
      hourCycle: 'h23',
    }).format(start),
  )
  if (localHour === 0 && durationMin >= 23 * 60) {
    return `${formatShortDate(start)} (all-day)`
  }

  const dayLabel = opts.includeDate ? formatShortDate(start) : formatShortDay(start)
  const duration = formatDurationMinutes(durationMin)
  return duration
    ? `${dayLabel}, ${formatTime(startStr)} (${duration})`
    : `${dayLabel}, ${formatTime(startStr)}`
}

function libraryDayDiff(a: Date, b: Date): number {
  // Whole calendar days between two instants, measured in the library's
  // wall-clock zone (so "Tomorrow" flips at local midnight, not the viewer's).
  // 'en-CA' yields YYYY-MM-DD, which Date.UTC can parse back into a day index.
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: LIBRARY_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const toDayIndex = (d: Date): number => {
    const [y, m, day] = fmt.format(d).split('-').map(Number)
    return Math.floor(Date.UTC(y!, m! - 1, day!) / 86_400_000)
  }
  return toDayIndex(b) - toDayIndex(a)
}

/**
 * Calm, low-arousal label for when an event starts. No countdown, no alarm,
 * no urgency. Returns relative-day phrasing for the near term and an absolute
 * date further out:
 *   - Today        -> "Today, 2:00 PM"
 *   - Tomorrow     -> "Tomorrow, 11:44 AM"
 *   - within ~6d   -> "Fri, 2:00 PM"
 *   - beyond       -> "Fri, Jun 12 · 2:00 PM"
 * Past events fall through to the absolute form.
 */
export function formatCalmStartLabel(startStr: string, locale: string = getDateLocale()): string {
  const start = new Date(startStr)
  if (Number.isNaN(start.getTime())) return ''
  const time = formatTime(startStr, locale)
  const dayDiff = libraryDayDiff(new Date(), start)

  if (dayDiff === 0) return `${t('events.relative.today', 'Today')}, ${time}`
  if (dayDiff === 1) return `${t('events.relative.tomorrow', 'Tomorrow')}, ${time}`
  if (dayDiff > 1 && dayDiff <= 6) return `${formatShortDay(start, locale)}, ${time}`

  // Absolute, with weekday + short date (a middle dot separates date and time).
  return `${formatShortDate(start, locale)} · ${time}`
}

/**
 * Human-readable name for an ISO 639-1 program-language code ("es" ->
 * "Spanish" / "español" depending on the active locale). Falls back to the
 * raw code if Intl can't resolve it (bad/legacy value).
 */
export function formatLanguageName(code: string, locale: string = getDateLocale()): string {
  try {
    return new Intl.DisplayNames([locale], { type: 'language' }).of(code) ?? code
  } catch {
    return code
  }
}
