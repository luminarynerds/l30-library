/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vite/client" />
/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import UpcomingProgramsStrip from './UpcomingProgramsStrip'
import type { Event } from '@/api/events-api'

// Minimal t() stub: string fallback returned directly; object params substitute
// both {{key}} and {key} patterns into the key (mirrors real getTranslation
// logic). Known i18n keys for spots-left use single-brace {count} syntax.
const KNOWN_KEYS: Record<string, string> = {
  'home.whatsHappening.spotsLeft': '{count} spots left',
}

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      const template = KNOWN_KEYS[key] ?? key
      if (paramsOrFallback && typeof paramsOrFallback === 'object') {
        return Object.entries(paramsOrFallback).reduce(
          (acc, [k, val]) =>
            acc.replace(`{{${k}}}`, String(val)).replace(`{${k}}`, String(val)),
          template,
        )
      }
      return template
    },
  }),
}))

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 1,
    title: 'Test Event',
    description: null,
    start_time: '2026-06-15T14:00:00+00:00',
    end_time: null,
    location: 'Main Library',
    is_virtual: false,
    audience: 'Adults',
    category: null,
    tags: null,
    max_attendees: null,
    registration_required: false,
    registration_count: 0,
    spots_remaining: null,
    image_url: null,
    is_featured: false,
    series_id: null,
    series_name: null,
    created_at: '2026-01-01T00:00:00+00:00',
    average_rating: null,
    review_count: 0,
    ...overrides,
  }
}

function renderStrip(events: Event[]) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <UpcomingProgramsStrip events={events} />
    </MemoryRouter>,
  )
}

describe('UpcomingProgramsStrip card anatomy', () => {
  it('renders nothing when events is null', () => {
    const { container } = render(
      <MemoryRouter>
        <UpcomingProgramsStrip events={null} />
      </MemoryRouter>,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when events is empty', () => {
    const { container } = render(
      <MemoryRouter>
        <UpcomingProgramsStrip events={[]} />
      </MemoryRouter>,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders at most 3 cards', () => {
    const events = [1, 2, 3, 4].map((n) => makeEvent({ id: n, title: `Event ${n}` }))
    renderStrip(events)
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('each card has all 5 slots present', () => {
    const event = makeEvent({
      start_time: '2026-06-15T14:00:00+00:00',
      audience: 'Teens',
      location: 'Teen Room',
      registration_required: false,
    })
    renderStrip([event])
    const card = screen.getByRole('article')

    // Slot 1: time element with datetime attribute
    const timeEl = within(card).getByRole('time') as HTMLElement
    expect(timeEl).toBeInTheDocument()
    expect(timeEl).toHaveAttribute('datetime', '2026-06-15T14:00:00+00:00')

    // Slot 2: heading
    expect(within(card).getByRole('heading', { level: 3 })).toHaveTextContent('Test Event')

    // Slot 3: audience tag
    expect(within(card).getByText('Teens')).toBeInTheDocument()

    // Slot 4: location
    expect(within(card).getByText('Teen Room')).toBeInTheDocument()

    // Slot 5: registration status (drop-in because registration_required is false)
    expect(within(card).getByText('Drop in, no registration')).toBeInTheDocument()
  })

  it('shows "All ages" when audience is null', () => {
    renderStrip([makeEvent({ audience: null })])
    expect(screen.getByText('All ages')).toBeInTheDocument()
  })

  it('falls back to branch_name when location is null', () => {
    renderStrip([makeEvent({ location: null, branch_name: 'Elmdale Branch' })])
    expect(screen.getByText('Elmdale Branch')).toBeInTheDocument()
  })

  it('falls back to "Main Library" when both location and branch_name are null', () => {
    renderStrip([makeEvent({ location: null, branch_name: undefined })])
    expect(screen.getByText('Main Library')).toBeInTheDocument()
  })

  it('shows "Registration required" when required and spots_remaining is null', () => {
    renderStrip([makeEvent({ registration_required: true, spots_remaining: null })])
    expect(screen.getByText('Registration required')).toBeInTheDocument()
  })

  it('shows spots remaining count when registration required and spots available', () => {
    renderStrip([makeEvent({ registration_required: true, spots_remaining: 7 })])
    expect(screen.getByText('7 spots left')).toBeInTheDocument()
  })

  it('shows "Full" when registration required and spots_remaining is 0', () => {
    renderStrip([makeEvent({ registration_required: true, spots_remaining: 0 })])
    expect(screen.getByText('Full')).toBeInTheDocument()
  })

  it('shows drop-in when registration_required is false regardless of spots', () => {
    renderStrip([makeEvent({ registration_required: false, spots_remaining: 5 })])
    expect(screen.getByText('Drop in, no registration')).toBeInTheDocument()
  })
})

describe('UpcomingProgramsStrip time correctness', () => {
  it('time element shows the event start_time, not current wall-clock time', () => {
    // Use a fixed date far in the past so there is zero chance the rendered
    // time matches the current wall clock.
    const event = makeEvent({ start_time: '2026-03-01T09:30:00+00:00' })
    renderStrip([event])

    const timeEl = screen.getByRole('time')
    // datetime attr must be the event's ISO string, not a dynamic value
    expect(timeEl).toHaveAttribute('datetime', '2026-03-01T09:30:00+00:00')

    // The rendered text must NOT match the current time (which would indicate
    // new Date() / Date.now() is being formatted instead of start_time).
    const nowTime = new Date().toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    })
    // "9:30 AM" (UTC) should not equal the current wall-clock minute
    expect(timeEl.textContent).not.toBe(nowTime)
  })

  it('formatProgramDate reads start_time field, not a live clock', () => {
    // Render two events with DIFFERENT start times and confirm they display
    // different times -- a live clock would make them identical within a test run.
    const events = [
      makeEvent({ id: 1, title: 'Morning', start_time: '2026-06-15T08:00:00+00:00' }),
      makeEvent({ id: 2, title: 'Evening', start_time: '2026-06-15T19:00:00+00:00' }),
    ]
    renderStrip(events)
    const timeEls = screen.getAllByRole('time')
    expect(timeEls).toHaveLength(2)
    expect(timeEls[0]!.getAttribute('datetime')).toBe('2026-06-15T08:00:00+00:00')
    expect(timeEls[1]!.getAttribute('datetime')).toBe('2026-06-15T19:00:00+00:00')
    // The text content of each <time> element should differ
    expect(timeEls[0]!.textContent).not.toBe(timeEls[1]!.textContent)
  })
})
