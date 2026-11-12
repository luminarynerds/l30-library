/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({ settings: { reduceMotion: false }, updateSetting: vi.fn() }),
}))

import ThisWeekStrip from '../ThisWeekStrip'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import type { Event } from '@/api/api'

function wrap(node: React.ReactNode) {
  return (
    <MemoryRouter>
      <BrandingProvider>
        <I18nProvider>{node}</I18nProvider>
      </BrandingProvider>
    </MemoryRouter>
  )
}

function makeEvent(partial: Partial<Event> & { id: number; start_time: string; title: string }): Event {
  return {
    description: null,
    end_time: null,
    location: null,
    is_virtual: false,
    audience: partial.audience ?? null,
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
    created_at: new Date().toISOString(),
    average_rating: null,
    review_count: 0,
    ...partial,
  } as Event
}

function dayKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function atLocalTime(daysFromToday: number, hour: number, minute: number): string {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + daysFromToday)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

describe('ThisWeekStrip', () => {
  beforeEach(() => {
    vi.useRealTimers()
  })

  it('renders 7 day columns anchored at today', () => {
    render(wrap(<ThisWeekStrip events={[]} />))
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    for (let i = 0; i < 7; i++) {
      const d = new Date(today)
      d.setDate(d.getDate() + i)
      expect(screen.getByTestId(`day-column-${dayKey(d)}`)).toBeInTheDocument()
    }
  })

  it('shows up to 3 chips per day with "+N more" overflow', () => {
    const events: Event[] = [
      makeEvent({ id: 1, title: 'Alpha', start_time: atLocalTime(0, 9, 0) }),
      makeEvent({ id: 2, title: 'Bravo', start_time: atLocalTime(0, 10, 0) }),
      makeEvent({ id: 3, title: 'Charlie', start_time: atLocalTime(0, 11, 0) }),
      makeEvent({ id: 4, title: 'Delta', start_time: atLocalTime(0, 12, 0) }),
      makeEvent({ id: 5, title: 'Echo', start_time: atLocalTime(0, 13, 0) }),
    ]
    render(wrap(<ThisWeekStrip events={events} />))
    expect(screen.getByRole('link', { name: /Alpha/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Bravo/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Charlie/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Delta/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Echo/ })).not.toBeInTheDocument()
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const overflow = screen.getByTestId(`day-overflow-${dayKey(today)}`)
    expect(overflow.textContent).toContain('+2')
  })

  it('renders chips as <a> with /events/detail/{id} href', () => {
    const events: Event[] = [
      makeEvent({ id: 42, title: 'Xylophone', start_time: atLocalTime(1, 14, 0) }),
    ]
    render(wrap(<ThisWeekStrip events={events} />))
    const link = screen.getByRole('link', { name: /Xylophone/ })
    expect(link.getAttribute('href')).toBe('/events/detail/42')
  })

  it('renders a <time datetime> element on each chip', () => {
    const start = atLocalTime(2, 15, 30)
    const events: Event[] = [makeEvent({ id: 7, title: 'Yarn', start_time: start })]
    const { container } = render(wrap(<ThisWeekStrip events={events} />))
    const timeEl = container.querySelector('time[datetime]')
    expect(timeEl).not.toBeNull()
    expect(timeEl?.getAttribute('datetime')).toBe(start)
  })

  it('empty day exposes a keyboard-operable button that scrolls to the filters', async () => {
    const user = userEvent.setup()
    const scrollIntoView = vi.fn()
    const fakeRef = { current: { scrollIntoView } as unknown as HTMLElement }
    render(wrap(<ThisWeekStrip events={[]} scrollTargetRef={fakeRef} />))
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const col = screen.getByTestId(`day-column-${dayKey(today)}`)
    // A real <button> (not a click-only <section>) — keyboard-operable by default.
    const browseBtn = within(col).getByRole('button')
    await user.click(browseBtn)
    expect(scrollIntoView).toHaveBeenCalled()
  })

  it('renders skeleton when isLoading', () => {
    render(wrap(<ThisWeekStrip events={[]} isLoading />))
    expect(screen.getByTestId('this-week-strip-skeleton')).toBeInTheDocument()
  })

  it('each day is a region with an aria-label', () => {
    render(wrap(<ThisWeekStrip events={[]} />))
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const col = screen.getByTestId(`day-column-${dayKey(today)}`)
    expect(col.tagName).toBe('SECTION')
    expect(col.getAttribute('aria-label')).toBeTruthy()
  })
})
