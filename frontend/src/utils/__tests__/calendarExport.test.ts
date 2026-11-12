/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { generateICalEvent, generateICalFeed } from '../calendarExport'
import { createMockEvent } from '@/__tests__/helpers/testHelpers'

describe('calendarExport — VALARM reminders (events review enhancement #4)', () => {
  const event = createMockEvent({
    id: 1,
    title: 'Storytime',
    start_time: '2026-08-01T18:00:00Z',
    end_time: '2026-08-01T19:00:00Z',
  })

  it('omits VALARM by default', () => {
    expect(generateICalEvent(event)).not.toContain('BEGIN:VALARM')
  })

  it('embeds a 1-day and a 1-hour VALARM when alarms is enabled', () => {
    const ics = generateICalEvent(event, { alarms: true })
    expect(ics.match(/BEGIN:VALARM/g)).toHaveLength(2)
    expect(ics).toContain('TRIGGER:-P1D')
    expect(ics).toContain('TRIGGER:-PT1H')
    expect(ics).toContain('ACTION:DISPLAY')
  })

  it('places the VALARM blocks inside the VEVENT', () => {
    const ics = generateICalEvent(event, { alarms: true })
    expect(ics.indexOf('BEGIN:VEVENT')).toBeLessThan(ics.indexOf('BEGIN:VALARM'))
    expect(ics.lastIndexOf('END:VALARM')).toBeLessThan(ics.indexOf('END:VEVENT'))
  })

  it('never adds VALARM to the multi-event feed', () => {
    expect(generateICalFeed([event])).not.toContain('BEGIN:VALARM')
  })
})
