/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Client-side single-event iCalendar (.ics) generation for the patron /events
 * surface. Pure browser code — no backend round-trip. One VEVENT per call with
 * title, start/end, location, description, and a stable URL back to the event.
 *
 * A sibling helper (`utils/calendarExport.ts`) builds feed-level exports and
 * Google/Outlook deep links; this module is the per-card "Add to my calendar"
 * path and is the one that embeds a canonical URL line.
 */
import type { Event } from '@/api/api'

export interface IcsOptions {
  libraryName?: string
  domain?: string
}

/** ICS wants UTC stamps as YYYYMMDDTHHMMSSZ. */
function toIcsUtc(date: Date): string {
  return date.toISOString().replace(/[-:]|\.\d{3}/g, '')
}

/**
 * Escape per RFC 5545 §3.3.11: backslash, comma, semicolon, and newlines.
 * Order matters — escape backslashes first so we don't double-escape the
 * escapes we add afterward.
 */
function escapeIcsText(text: string): string {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n')
}

/**
 * Fold lines to 75 octets per RFC 5545 §3.1. Continuation lines start with a
 * single space. We fold on character count (close enough for the ASCII-ish
 * content here) to keep strict parsers happy.
 */
function foldLine(line: string): string {
  if (line.length <= 75) return line
  const parts: string[] = []
  let rest = line
  parts.push(rest.slice(0, 75))
  rest = rest.slice(75)
  while (rest.length > 74) {
    parts.push(' ' + rest.slice(0, 74))
    rest = rest.slice(74)
  }
  if (rest.length > 0) parts.push(' ' + rest)
  return parts.join('\r\n')
}

/** Absolute canonical URL for an event's patron detail page. */
function eventDetailUrl(event: Event): string {
  const path = `/events/detail/${event.id}`
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${path}`
  }
  return path
}

function defaultDomain(): string {
  if (typeof window !== 'undefined' && window.location?.host) {
    return window.location.host
  }
  return 'example.com'
}

export function buildEventIcs(event: Event, options: IcsOptions = {}): string {
  const start = new Date(event.start_time)
  const end = event.end_time
    ? new Date(event.end_time)
    : new Date(start.getTime() + 60 * 60 * 1000) // default 1h when end is unknown
  const libraryName = options.libraryName?.trim() || 'Library'
  const domain = options.domain?.trim() || defaultDomain()

  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    `PRODID:-//${escapeIcsText(libraryName)}//Events//EN`,
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:event-${event.id}@${domain}`,
    `DTSTAMP:${toIcsUtc(new Date())}`,
    `DTSTART:${toIcsUtc(start)}`,
    `DTEND:${toIcsUtc(end)}`,
    `SUMMARY:${escapeIcsText(event.title)}`,
    `URL:${escapeIcsText(eventDetailUrl(event))}`,
  ]

  if (event.description) lines.push(`DESCRIPTION:${escapeIcsText(event.description)}`)
  // Prefer the room/location string; fall back to the hosting branch name.
  const location = event.location?.trim() || event.branch_name?.trim()
  if (location) lines.push(`LOCATION:${escapeIcsText(location)}`)
  if (event.category) lines.push(`CATEGORIES:${escapeIcsText(event.category)}`)

  lines.push('END:VEVENT', 'END:VCALENDAR')

  return lines.map(foldLine).join('\r\n')
}

/** Safe, readable filename stem from the event title. */
function icsFilename(event: Event): string {
  const stem = event.title
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || `event-${event.id}`
  return `${stem}.ics`
}

/** Generate and trigger a download of the event's .ics file. */
export function downloadEventIcs(event: Event, options: IcsOptions = {}): void {
  const blob = new Blob([buildEventIcs(event, options)], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = icsFilename(event)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
