/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { buildEventIcs, downloadEventIcs } from './ics'
import type { Event } from '@/api/api'

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 101,
    title: 'Summer Reading Kickoff',
    description: 'Come celebrate the start of summer reading.',
    start_time: '2026-06-01T18:00:00Z',
    end_time: '2026-06-01T19:30:00Z',
    location: 'Main Branch, Room A',
    is_virtual: false,
    virtual_link: null,
    audience: null,
    category: 'Programs',
    event_language: null,
    tags: null,
    max_attendees: null,
    registration_required: false,
    registration_count: 0,
    spots_remaining: null,
    image_url: null,
    is_featured: false,
    series_id: null,
    series_name: null,
    created_at: '2026-05-01T00:00:00Z',
    average_rating: null,
    review_count: 0,
    branch_id: null,
    branch_name: 'Main Branch',
    accessibility_notes: null,
    wheelchair_accessible: undefined,
    asl_provided: undefined,
    ...overrides,
  } as Event
}

describe('buildEventIcs', () => {
  it('wraps a normal timed event in VCALENDAR/VEVENT with correct DTSTART/DTEND/SUMMARY/UID', () => {
    const ics = buildEventIcs(makeEvent(), { domain: 'library.example' })

    expect(ics).toContain('BEGIN:VCALENDAR')
    expect(ics).toContain('BEGIN:VEVENT')
    expect(ics).toContain('DTSTART:20260601T180000Z')
    expect(ics).toContain('DTEND:20260601T193000Z')
    expect(ics).toContain('SUMMARY:Summer Reading Kickoff')
    expect(ics).toContain('UID:event-101@library.example')
    expect(ics).toContain('END:VEVENT')
    expect(ics).toContain('END:VCALENDAR')
  })

  it('produces a stable UID across repeated calls for the same event', () => {
    const event = makeEvent()
    const first = buildEventIcs(event, { domain: 'library.example' })
    const second = buildEventIcs(event, { domain: 'library.example' })

    const uidOf = (block: string) => block.match(/UID:([^\r\n]+)/)?.[1]
    expect(uidOf(first)).toBe(uidOf(second))
    expect(uidOf(first)).toBe('event-101@library.example')
  })

  it('defaults to a 1-hour block and omits LOCATION/DESCRIPTION/CATEGORIES when an event has no end_time, description, location, or category', () => {
    const event = makeEvent({
      end_time: null,
      description: null,
      location: null,
      branch_name: null,
      category: null,
    })
    const ics = buildEventIcs(event)

    expect(ics).toContain('DTSTART:20260601T180000Z')
    expect(ics).toContain('DTEND:20260601T190000Z') // start + 1h
    expect(ics).not.toContain('LOCATION:')
    expect(ics).not.toContain('DESCRIPTION:')
    expect(ics).not.toContain('CATEGORIES:')
  })

  it('falls back to branch_name for LOCATION when location is blank', () => {
    const ics = buildEventIcs(makeEvent({ location: '  ', branch_name: 'East Branch' }))
    expect(ics).toContain('LOCATION:East Branch')
  })

  it('escapes commas, semicolons, and newlines per RFC 5545', () => {
    const ics = buildEventIcs(
      makeEvent({
        title: 'Story Time; Ages 3-5, and up',
        description: 'Line one\nLine two, with a semicolon; here',
      })
    )

    expect(ics).toContain('SUMMARY:Story Time\\; Ages 3-5\\, and up')
    expect(ics).toContain('DESCRIPTION:Line one\\nLine two\\, with a semicolon\\; here')
    // Raw unescaped separators should not leak into the output.
    expect(ics).not.toMatch(/SUMMARY:Story Time; Ages/)
  })

  it('escapes backslashes before adding new escape backslashes', () => {
    const ics = buildEventIcs(makeEvent({ title: 'C:\\Users\\books' }))
    expect(ics).toContain('SUMMARY:C:\\\\Users\\\\books')
  })
})

describe('downloadEventIcs', () => {
  let createObjectURLSpy: ReturnType<typeof vi.spyOn>
  let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>
  let clickSpy: ReturnType<typeof vi.fn<() => void>>

  beforeEach(() => {
    createObjectURLSpy = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:mock-url')
    revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    clickSpy = vi.fn<() => void>()
    const realCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreateElement(tag)
      if (tag === 'a') el.click = clickSpy
      return el
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('triggers a download with a .ics filename derived from the event title', () => {
    downloadEventIcs(makeEvent({ title: 'Summer Reading Kickoff!' }))

    expect(createObjectURLSpy).toHaveBeenCalledTimes(1)
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')
  })

  it('sanitizes non-alphanumeric characters out of the filename', () => {
    // Self-contained: restore the outer beforeEach's spy first so this
    // test's createElement override wraps the true native implementation,
    // not another mock (double-wrapping a vi.fn() spy recurses).
    vi.restoreAllMocks()
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    let downloadName = ''
    const realCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreateElement(tag)
      if (tag === 'a') {
        el.click = vi.fn()
        Object.defineProperty(el, 'download', {
          set(value: string) {
            downloadName = value
          },
          get() {
            return downloadName
          },
        })
      }
      return el
    })

    downloadEventIcs(makeEvent({ title: 'Story Time: Ages 3-5, & up!' }))

    expect(downloadName).toBe('Story-Time-Ages-3-5-up.ics')
  })
})
