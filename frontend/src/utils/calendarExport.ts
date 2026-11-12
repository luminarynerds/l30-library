/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Calendar Export Utilities
 * Provides functions to generate iCal (.ics) files and Google Calendar links
 */

import type { Event } from '@/api/api'

function formatICalDate(date: Date): string {
  return date.toISOString().replace(/-|:|\.\d{3}/g, '')
}

function formatGoogleDate(date: Date): string {
  return date.toISOString().replace(/-|:|\.\d{3}/g, '')
}

function escapeICalText(text: string): string {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/,/g, '\\,')
    .replace(/;/g, '\\;')
    .replace(/\n/g, '\\n')
}

export interface ICalEventOptions {
  /**
   * When true, embed two VALARM reminders (1 day and 1 hour before the
   * event) in the VEVENT. Opt-in: the patron's calendar app fires them
   * offline, with no notification permissions. Used by the "Remind me"
   * action on registered events.
   */
  alarms?: boolean
  libraryName?: string
}

function buildReminderAlarms(): string[] {
  return [
    'BEGIN:VALARM',
    'TRIGGER:-P1D',
    'ACTION:DISPLAY',
    'DESCRIPTION:Event reminder (1 day before)',
    'END:VALARM',
    'BEGIN:VALARM',
    'TRIGGER:-PT1H',
    'ACTION:DISPLAY',
    'DESCRIPTION:Event reminder (1 hour before)',
    'END:VALARM',
  ]
}

export function generateICalEvent(event: Event, options: ICalEventOptions = {}): string {
  const startDate = new Date(event.start_time)
  const endDate = event.end_time
    ? new Date(event.end_time)
    : new Date(startDate.getTime() + 60 * 60 * 1000) // Default 1 hour duration

  const uid = `event-${event.id}@example.com`
  const created = new Date().toISOString().replace(/-|:|\.\d{3}/g, '')
  const libraryName = options.libraryName?.trim() || 'Library'

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    `PRODID:-//${escapeICalText(libraryName)}//Events//EN`,
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${uid}`,
    `DTSTAMP:${created}`,
    `DTSTART:${formatICalDate(startDate)}`,
    `DTEND:${formatICalDate(endDate)}`,
    `SUMMARY:${escapeICalText(event.title)}`,
  ]

  if (event.description) {
    lines.push(`DESCRIPTION:${escapeICalText(event.description)}`)
  }

  if (event.location) {
    lines.push(`LOCATION:${escapeICalText(event.location)}`)
  }

  if (event.category) {
    lines.push(`CATEGORIES:${escapeICalText(event.category)}`)
  }

  if (options.alarms) {
    lines.push(...buildReminderAlarms())
  }

  lines.push('END:VEVENT', 'END:VCALENDAR')

  return lines.join('\r\n')
}

export function generateICalFeed(
  events: Event[],
  title = 'Library Events',
  options: Pick<ICalEventOptions, 'libraryName'> = {}
): string {
  const now = new Date().toISOString().replace(/-|:|\.\d{3}/g, '')
  const libraryName = options.libraryName?.trim() || 'Library'

  const eventBlocks = events.map(event => {
    const startDate = new Date(event.start_time)
    const endDate = event.end_time
      ? new Date(event.end_time)
      : new Date(startDate.getTime() + 60 * 60 * 1000)

    const lines = [
      'BEGIN:VEVENT',
      `UID:event-${event.id}@example.com`,
      `DTSTAMP:${now}`,
      `DTSTART:${formatICalDate(startDate)}`,
      `DTEND:${formatICalDate(endDate)}`,
      `SUMMARY:${escapeICalText(event.title)}`,
    ]

    if (event.description) {
      lines.push(`DESCRIPTION:${escapeICalText(event.description)}`)
    }
    if (event.location) {
      lines.push(`LOCATION:${escapeICalText(event.location)}`)
    }
    if (event.category) {
      lines.push(`CATEGORIES:${escapeICalText(event.category)}`)
    }

    lines.push('END:VEVENT')
    return lines.join('\r\n')
  })

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    `PRODID:-//${escapeICalText(libraryName)}//Events//EN`,
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    `X-WR-CALNAME:${escapeICalText(title)}`,
    ...eventBlocks,
    'END:VCALENDAR',
  ].join('\r\n')
}

export function downloadICalEvent(event: Event, options: ICalEventOptions = {}): void {
  const icalContent = generateICalEvent(event, options)
  const blob = new Blob([icalContent], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `${event.title.replace(/[^a-zA-Z0-9]/g, '-')}.ics`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function downloadICalFeed(
  events: Event[],
  filename = 'library-events.ics',
  options: Pick<ICalEventOptions, 'libraryName'> = {}
): void {
  const icalContent = generateICalFeed(events, undefined, options)
  const blob = new Blob([icalContent], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function generateGoogleCalendarUrl(event: Event): string {
  const startDate = new Date(event.start_time)
  const endDate = event.end_time
    ? new Date(event.end_time)
    : new Date(startDate.getTime() + 60 * 60 * 1000)

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${formatGoogleDate(startDate)}/${formatGoogleDate(endDate)}`,
  })

  if (event.description) {
    params.set('details', event.description)
  }

  if (event.location) {
    params.set('location', event.location)
  }

  return `https://www.google.com/calendar/render?${params.toString()}`
}

export function generateOutlookCalendarUrl(event: Event): string {
  const startDate = new Date(event.start_time)
  const endDate = event.end_time
    ? new Date(event.end_time)
    : new Date(startDate.getTime() + 60 * 60 * 1000)

  const params = new URLSearchParams({
    path: '/calendar/action/compose',
    rru: 'addevent',
    subject: event.title,
    startdt: startDate.toISOString(),
    enddt: endDate.toISOString(),
  })

  if (event.description) {
    params.set('body', event.description)
  }

  if (event.location) {
    params.set('location', event.location)
  }

  return `https://outlook.live.com/calendar/0/deeplink/compose?${params.toString()}`
}

export function openCalendarService(event: Event, service: 'google' | 'outlook' | 'ical'): void {
  switch (service) {
    case 'google':
      window.open(generateGoogleCalendarUrl(event), '_blank', 'noopener,noreferrer')
      break
    case 'outlook':
      window.open(generateOutlookCalendarUrl(event), '_blank', 'noopener,noreferrer')
      break
    case 'ical':
      downloadICalEvent(event)
      break
  }
}
