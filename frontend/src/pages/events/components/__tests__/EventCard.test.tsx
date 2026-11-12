/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EventCard (patron) — a11y hardening + registration pill + age range + affordances.
 *
 * Co-located with the component at frontend/src/pages/events/components/EventCard.tsx.
 * The legacy file at frontend/src/__tests__/components/events/EventCard.test.tsx
 * targets a different (orphan) EventCard and is intentionally left untouched.
 *
 * Mocks follow the in-file useTranslation mock pattern from LexileBadge.test.tsx —
 * avoids the I18nProvider/Branding/QueryClient stack used by EventsPageContent
 * tests since we're testing one component in isolation.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { createMockEvent } from '@/__tests__/helpers/testHelpers'
import type { Event } from '@/api/api'

// ---- Mocks (module-level, must precede component import) ------------------

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      // Mirror the production t(): a string 2nd arg is the fallback.
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      const params = paramsOrFallback || {}
      // Provide just the keys the component reads — anything else falls back to key.
      switch (key) {
        case 'events.registered': return "You're registered"
        case 'events.dropIn': return 'Drop-in'
        case 'events.registrationOpen': return 'Open'
        case 'events.fullJoinWaitlist': return 'Full — join waitlist'
        case 'events.agesRange': return `Ages ${params.min}–${params.max}`
        case 'events.agesMin': return `Ages ${params.min}+`
        case 'events.agesMax': return `Ages up to ${params.max}`
        case 'events.affordances.label': return 'Accessibility features'
        case 'events.affordances.wheelchair': return 'Wheelchair accessible'
        case 'events.affordances.asl': return 'ASL provided'
        case 'events.affordances.captioning': return 'Captioning provided'
        case 'events.affordances.sensory': return 'Sensory-friendly'
        case 'events.affordances.largePrint': return 'Large print available'
        case 'events.register': return 'Register'
        case 'events.waitlist': return 'Join Waitlist'
        case 'events.registerFor': return `Register for ${params.title}`
        case 'events.waitlistFor': return `Join waitlist for ${params.title}`
        case 'events.dropInAria': return 'Drop-in event, no registration required'
        case 'events.registrationOpenAria': return 'Registration open'
        case 'events.fullJoinWaitlistAria': return 'This event is full. Join the waitlist.'
        default: return key
      }
    },
    language: 'en',
    isRTL: false,
  }),
}))

vi.mock('@/pages/events/hooks/useCountdown', () => ({
  useCountdown: () => ({ upcomingStart: null }),
}))

vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    settings: { quietMode: false, noFOMO: false, noUrgentLanguage: false },
    updateSetting: vi.fn(),
  }),
}))

vi.mock('@/components/ShareButton', () => ({
  default: () => <button type="button" aria-label="Share">share</button>,
}))

vi.mock('./QuickViewPopover', () => ({
  default: () => null,
}))

vi.mock('./EventImagePlaceholder', () => ({
  default: () => <div data-testid="event-image-placeholder" />,
}))

import EventCard from '../EventCard'

// ---- Helpers --------------------------------------------------------------

function renderCard(event: Event, overrides: Partial<Parameters<typeof EventCard>[0]> = {}) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <EventCard
        event={event}
        onRegister={vi.fn()}
        onClick={vi.fn()}
        {...overrides}
      />
    </MemoryRouter>,
  )
}

// ---- Tests ----------------------------------------------------------------

describe('EventCard — a11y hardening', () => {
  it('title is rendered as a single <h3> (no duplicate heading levels)', () => {
    const event = createMockEvent({ id: 42, title: 'Friday Storytime' })
    renderCard(event)

    const h3s = screen.getAllByRole('heading', { level: 3 })
    expect(h3s).toHaveLength(1)
    expect(h3s[0]).toHaveTextContent('Friday Storytime')

    // No h4 with the same text (the documented duplicate-heading defect).
    expect(screen.queryByRole('heading', { level: 4, name: 'Friday Storytime' })).toBeNull()
  })

  it('renders <time> elements with ISO8601 datetime attributes on start_time', () => {
    const event = createMockEvent({ id: 1, start_time: '2026-06-15T14:30:00Z' })
    const { container } = renderCard(event)

    // Multiple <time> elements (date badge + inline time row); each must carry datetime.
    const times = container.querySelectorAll('time')
    expect(times.length).toBeGreaterThanOrEqual(2)
    times.forEach((t) => {
      expect(t.getAttribute('datetime')).toBe('2026-06-15T14:30:00Z')
    })
  })

  it('title is wrapped in a router Link to /events/detail/{id}, not a div with click handler', () => {
    const event = createMockEvent({ id: 99, title: 'Linkable Event' })
    renderCard(event)

    const link = screen.getByRole('link', { name: 'Linkable Event' })
    expect(link).toHaveAttribute('href', '/events/detail/99')

    // The outer card no longer claims article role + tabindex.
    expect(screen.queryByRole('article')).toBeNull()
  })
})

describe('EventCard — registration status pill', () => {
  it('renders the "Registered" pill when isRegistered is true', () => {
    const event = createMockEvent({ registration_required: true, spots_remaining: 5 })
    renderCard(event, { isRegistered: true })

    const pill = screen.getByTestId('event-registration-pill')
    expect(pill).toHaveTextContent("You're registered")
    expect(pill).toHaveAttribute('aria-label', "You're registered")
  })

  it('renders the "Drop-in" pill when registration is not required', () => {
    const event = createMockEvent({ registration_required: false, spots_remaining: null })
    renderCard(event)

    const pill = screen.getByTestId('event-registration-pill')
    expect(pill).toHaveTextContent('Drop-in')
    expect(pill).toHaveAttribute('aria-label', 'Drop-in event, no registration required')
  })

  it('renders the "Full — join waitlist" pill when spots_remaining is 0', () => {
    const event = createMockEvent({ registration_required: true, spots_remaining: 0, max_attendees: 30, registration_count: 30 })
    renderCard(event)

    const pill = screen.getByTestId('event-registration-pill')
    expect(pill).toHaveTextContent(/Full.*join waitlist/i)
    expect(pill).toHaveAttribute('aria-label', 'This event is full. Join the waitlist.')
  })

  it('renders the "Open" pill when registration is required and spots remain', () => {
    const event = createMockEvent({ registration_required: true, spots_remaining: 5 })
    renderCard(event)

    const pill = screen.getByTestId('event-registration-pill')
    expect(pill).toHaveTextContent('Open')
    expect(pill).toHaveAttribute('aria-label', 'Registration open')
  })
})

describe('EventCard — age range', () => {
  it('renders "Ages {min}–{max}" when both bounds are set', () => {
    const event = createMockEvent({ min_age: 5, max_age: 12, audience: 'children' })
    renderCard(event)
    expect(screen.getByText('Ages 5–12')).toBeInTheDocument()
    // When age range is present, the bare audience string should NOT also render.
    expect(screen.queryByText('children')).toBeNull()
  })

  it('renders "Ages {min}+" when only min_age is set', () => {
    const event = createMockEvent({ min_age: 18, max_age: null, audience: 'adults' })
    renderCard(event)
    expect(screen.getByText('Ages 18+')).toBeInTheDocument()
  })

  it('renders "Ages up to {max}" when only max_age is set', () => {
    const event = createMockEvent({ min_age: null, max_age: 5, audience: 'children' })
    renderCard(event)
    expect(screen.getByText('Ages up to 5')).toBeInTheDocument()
  })

  it('falls back to audience string when neither bound is set', () => {
    const event = createMockEvent({ min_age: null, max_age: null, audience: 'teens' })
    renderCard(event)
    expect(screen.getByText('teens')).toBeInTheDocument()
  })
})

describe('EventCard — accessibility affordances', () => {
  it('renders an icon for each affordance that is true (with aria-label)', () => {
    const event = createMockEvent({
      wheelchair_accessible: true,
      asl_provided: true,
      captioning_provided: true,
      sensory_friendly: false,
      large_print_available: true,
    })
    renderCard(event)

    const row = screen.getByRole('list', { name: 'Accessibility features' })
    expect(within(row).getByLabelText('Wheelchair accessible')).toBeInTheDocument()
    expect(within(row).getByLabelText('ASL provided')).toBeInTheDocument()
    expect(within(row).getByLabelText('Captioning provided')).toBeInTheDocument()
    expect(within(row).getByLabelText('Large print available')).toBeInTheDocument()
    // sensory_friendly is false — must NOT render.
    expect(within(row).queryByLabelText('Sensory-friendly')).toBeNull()
  })

  it('renders nothing if no affordance is true', () => {
    const event = createMockEvent({
      wheelchair_accessible: false,
      asl_provided: false,
      captioning_provided: false,
      sensory_friendly: false,
      large_print_available: false,
    })
    renderCard(event)
    expect(screen.queryByRole('list', { name: 'Accessibility features' })).toBeNull()
  })
})

describe('EventCard — tag chips', () => {
  it('renders each tag as a real button, not role="listitem"', () => {
    const event = createMockEvent({ id: 7, title: 'Tagged Event', tags: ['stem', 'craft'] })
    renderCard(event)
    // Tag chips are clickable filters. If one still carried role="listitem"
    // (which overrides the button role) these queries would fail.
    expect(screen.getByRole('button', { name: 'stem' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'craft' })).toBeInTheDocument()
  })
})

describe('EventCard — "What to expect" disclosure (events review enhancement #2)', () => {
  it('renders structured sensory descriptors when staff set them', () => {
    const event = createMockEvent({ lighting: 'dim', noise_level: 'quiet', crowd_size: 'small' })
    renderCard(event)
    expect(screen.getByText('What to expect')).toBeInTheDocument()
    // The mock t() returns the raw value for the unknown vocab key.
    expect(screen.getByText('dim')).toBeInTheDocument()
    expect(screen.getByText('quiet')).toBeInTheDocument()
    expect(screen.getByText('small')).toBeInTheDocument()
  })

  it('renders the disclosure for accessibility_notes alone', () => {
    const event = createMockEvent({
      lighting: null,
      noise_level: null,
      crowd_size: null,
      quiet_space_available: false,
      accessibility_notes: 'Side entrance has a ramp.',
    })
    renderCard(event)
    expect(screen.getByText('What to expect')).toBeInTheDocument()
    expect(screen.getByText('Side entrance has a ramp.')).toBeInTheDocument()
  })

  it('renders the quiet-space line when quiet_space_available is true', () => {
    const event = createMockEvent({
      lighting: null,
      noise_level: null,
      crowd_size: null,
      quiet_space_available: true,
      accessibility_notes: null,
    })
    renderCard(event)
    expect(screen.getByText('A quiet space is available')).toBeInTheDocument()
  })

  it('does not render the disclosure when no sensory info is present', () => {
    const event = createMockEvent({
      lighting: null,
      noise_level: null,
      crowd_size: null,
      quiet_space_available: false,
      accessibility_notes: null,
    })
    renderCard(event)
    expect(screen.queryByText('What to expect')).toBeNull()
  })
})
