/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

// Mock i18n so we don't need loadLanguage('en'). The page calls t(key, fallback)
// for its static copy; mimic the real translator's untranslated-key behavior by
// returning the fallback when given one so assertions can match visible English.
vi.mock('@/i18n', () => ({
  getCurrentLocale: () => 'en-US',
  useTranslation: () => ({
    t: (key: string, fallback?: string) => (typeof fallback === 'string' ? fallback : key),
  }),
}))

// BoardMeetingsPage uses useBranding(); stub to a minimal value so the
// cadence footer can render without a real BrandingProvider.
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ library_name: 'Test Library' }),
}))

// react-router-dom: stub useSearchParams to a controllable mock so individual
// tests can simulate `?year=YYYY`. Default = empty params.
const mockSearchParams = { value: new URLSearchParams() }
vi.mock('react-router-dom', () => ({
  useSearchParams: () => [mockSearchParams.value, vi.fn()],
}))

// The page fetches /board/meetings on mount via the shared api client.
// Mock to return our fixtures so we control minutes_approved per-card.
const mockGet = vi.fn()
vi.mock('../../api/api', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}))
vi.mock('../../api/board-api', () => ({
  searchMeetings: vi.fn().mockResolvedValue({ results: [], total: 0 }),
}))

// ActiveCommentPeriodBanner fetches its own data; stub it out.
vi.mock('../../components/board/ActiveCommentPeriodBanner', () => ({
  default: () => null,
}))

// Sentry import in the page uses dynamic-ish lazy module; stub captureException.
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

import BoardMeetingsPage from './BoardMeetingsPage'
import { searchMeetings } from '../../api/board-api'
import type { BoardMeeting as ApiBoardMeeting } from '../../api/board-api'

const mockSearchMeetings = vi.mocked(searchMeetings)

const baseMeeting: Omit<ApiBoardMeeting, 'id'> & { agenda_preview: never[] } = {
  meeting_type: 'regular',
  title: '',
  description: null,
  scheduled_date: '',
  start_time: null,
  end_time: null,
  location: null,
  is_virtual: false,
  virtual_meeting_url: null,
  is_cancelled: false,
  cancellation_reason: null,
  quorum_met: null,
  minutes_approved: false,
  public_comment_enabled: true,
  public_comment_instructions: null,
  accessibility_info: null,
  has_executive_session: false,
  executive_session_reason: null,
  notice_lead_days_required: 3,
  notice_status: 'pending',
  notice_posted_at: null,
  notice_posted_by_id: null,
  notice_posting_locations: [],
  notice_document_id: null,
  agenda_published_at: null,
  agenda_published_by_id: null,
  created_at: '2026-01-01T00:00:00Z',
  created_by_id: 1,
  updated_at: null,
  agenda_preview: [],
}

describe('BoardMeetingsPage cards', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockSearchMeetings.mockReset()
    mockSearchMeetings.mockResolvedValue({ results: [], total: 0, skip: 0, limit: 50 })
    mockSearchParams.value = new URLSearchParams()
  })

  it('renders the View Minutes link when minutes_approved=true and the disabled pending badge when false', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 1,
        title: 'Past Meeting Approved',
        scheduled_date: '2025-12-17T23:00:00Z',
        minutes_approved: true,
      },
      {
        ...baseMeeting,
        id: 2,
        title: 'Past Meeting Pending',
        scheduled_date: '2026-04-15T22:00:00Z',
        minutes_approved: false,
      },
      {
        ...baseMeeting,
        id: 3,
        title: 'Upcoming Meeting',
        scheduled_date: '2099-01-01T00:00:00Z',
        minutes_approved: null,
      },
    ])

    render(<BoardMeetingsPage />)

    const approvedLink = await screen.findByRole('link', {
      name: /view minutes for past meeting approved/i,
    })
    expect(approvedLink).toHaveAttribute('href', '/board/meetings/1')

    expect(
      screen.getByLabelText(/minutes pending board approval/i),
    ).toBeInTheDocument()

    // Upcoming card must NOT render the View Minutes link.
    expect(
      screen.queryByRole('link', { name: /view minutes for upcoming meeting/i }),
    ).toBeNull()
  })

  it('renders the default public-comment instructions when the field is null', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 10,
        title: 'Meeting With Null Instructions',
        scheduled_date: '2099-02-01T00:00:00Z',
        minutes_approved: null,
        public_comment_instructions: null,
      },
    ])

    render(<BoardMeetingsPage />)

    expect(
      await screen.findByText(/three minutes per speaker/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/how to comment:/i)).toBeInTheDocument()
  })

  it('renders the populated public-comment instructions verbatim when provided', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 11,
        title: 'Meeting With Custom Instructions',
        scheduled_date: '2099-03-01T00:00:00Z',
        minutes_approved: null,
        public_comment_instructions: 'Submit comments via the online form.',
      },
    ])

    render(<BoardMeetingsPage />)

    expect(
      await screen.findByText(/submit comments via the online form/i),
    ).toBeInTheDocument()
    // The default fallback must NOT also appear.
    expect(screen.queryByText(/three minutes per speaker/i)).toBeNull()
  })

  it('does not render the Has Recording filter checkbox', async () => {
    mockGet.mockResolvedValue([])
    render(<BoardMeetingsPage />)
    // Wait for initial load to settle.
    await screen.findByRole('heading', { name: /board meetings/i })
    expect(screen.queryByLabelText(/has recording/i)).toBeNull()
  })

  it('shows generic cadence copy (no hardcoded weekday claim)', async () => {
    mockGet.mockResolvedValue([])
    render(<BoardMeetingsPage />)
    await screen.findByRole('heading', { name: /meeting information/i })
    expect(
      screen.getByText(/held monthly at/i),
    ).toBeInTheDocument()
    // A tenant's board picks its own day; product copy must not claim one.
    expect(screen.queryByText(/wednesday|tuesday|monday|thursday/i)).toBeNull()
    expect(screen.queryByText(/6:00 PM/i)).toBeNull()
  })

  it('renders upcoming meetings in ascending date order (next meeting first) regardless of API order', async () => {
    // API returns scheduled_date DESC; June 16 must NOT render before May 20.
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 9,
        title: 'June Regular Meeting',
        scheduled_date: '2099-06-16T22:00:00Z',
      },
      {
        ...baseMeeting,
        id: 8,
        title: 'May Regular Meeting',
        scheduled_date: '2099-05-20T22:00:00Z',
      },
      {
        ...baseMeeting,
        id: 10,
        title: 'May Special Meeting',
        scheduled_date: '2099-05-08T21:00:00Z',
      },
    ])
    render(<BoardMeetingsPage />)
    const upcomingSection = await screen.findByRole('region', { name: /^upcoming meetings$/i })
    const titles = within(upcomingSection).getAllByRole('heading', { level: 3 })
    const meetingTitles = titles
      .map((h) => h.textContent || '')
      .filter((t) => t.includes('Meeting'))
    expect(meetingTitles).toEqual([
      'May Special Meeting',
      'May Regular Meeting',
      'June Regular Meeting',
    ])
  })
})

describe('BoardMeetingsPage UX pack additions', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockSearchMeetings.mockReset()
    mockSearchMeetings.mockResolvedValue({ results: [], total: 0, skip: 0, limit: 50 })
    mockSearchParams.value = new URLSearchParams()
  })

  it('renders "Agenda posted" badge when agenda_published_at is set, and "Agenda pending" pill when upcoming + null', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 20,
        title: 'Agenda Posted Upcoming',
        scheduled_date: '2099-07-01T22:00:00Z',
        agenda_published_at: '2099-06-28T10:00:00Z',
      },
      {
        ...baseMeeting,
        id: 21,
        title: 'Agenda Pending Upcoming',
        scheduled_date: '2099-08-01T22:00:00Z',
        agenda_published_at: null,
      },
      {
        ...baseMeeting,
        id: 22,
        title: 'Past With No Agenda',
        scheduled_date: '2024-01-01T22:00:00Z',
        agenda_published_at: null,
      },
    ])
    render(<BoardMeetingsPage />)
    expect(
      await screen.findByRole('link', { name: /view agenda for agenda posted upcoming/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText(/agenda pending; typically posted 72 hours before/i),
    ).toBeInTheDocument()
    // Past meeting with null agenda gets no pill.
    const pastCard = screen.getByText('Past With No Agenda').closest('div')
    expect(pastCard).not.toBeNull()
    expect(within(pastCard!).queryByText(/agenda pending/i)).toBeNull()
  })

  it('renders the public notice provenance caption when notice_posted_at / locations are populated', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 30,
        title: 'Properly Noticed Meeting',
        scheduled_date: '2099-09-01T22:00:00Z',
        notice_posted_at: '2099-08-25T14:00:00Z',
        notice_posting_locations: [
          { location: 'Library lobby' },
          { location: 'City Hall bulletin board' },
        ],
      },
    ])
    render(<BoardMeetingsPage />)
    const caption = await screen.findByText(/public notice posted/i)
    expect(caption.textContent).toMatch(/library lobby/i)
    expect(caption.textContent).toMatch(/city hall bulletin board/i)
  })

  it('renders "Notice not yet posted" badge when an upcoming meeting is within lead-days and notice is missing', async () => {
    const soon = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 1 day out
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 40,
        title: 'Imminent Unnoticed',
        scheduled_date: soon,
        notice_lead_days_required: 3,
        notice_posted_at: null,
        notice_posting_locations: [],
      },
    ])
    render(<BoardMeetingsPage />)
    expect(
      await screen.findByLabelText(/public notice not yet posted/i),
    ).toBeInTheDocument()
  })

  it('groups past meetings by year in collapsible details, most recent year open by default', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 50,
        title: '2026 Past Meeting',
        scheduled_date: '2026-01-15T22:00:00Z',
      },
      {
        ...baseMeeting,
        id: 51,
        title: '2025 Past Meeting',
        scheduled_date: '2025-12-15T22:00:00Z',
      },
      {
        ...baseMeeting,
        id: 52,
        title: '2024 Past Meeting',
        scheduled_date: '2024-06-15T22:00:00Z',
      },
    ])
    render(<BoardMeetingsPage />)
    const pastSection = await screen.findByRole('region', { name: /^past meetings$/i })
    // One <details> per year; verify all three rendered as collapsible groups.
    const summaries = pastSection.querySelectorAll('summary')
    expect(summaries).toHaveLength(3)
    expect(summaries[0]?.textContent).toMatch(/2026/)
    expect(summaries[1]?.textContent).toMatch(/2025/)
    expect(summaries[2]?.textContent).toMatch(/2024/)
    // 2026 group is open by default → the card inside is rendered.
    expect(screen.getByText('2026 Past Meeting')).toBeInTheDocument()
  })

  it('opens the year matching ?year= URL param', async () => {
    mockSearchParams.value = new URLSearchParams('year=2024')
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 60,
        title: '2026 Past Meeting',
        scheduled_date: '2026-01-15T22:00:00Z',
      },
      {
        ...baseMeeting,
        id: 61,
        title: '2024 Past Meeting',
        scheduled_date: '2024-06-15T22:00:00Z',
      },
    ])
    render(<BoardMeetingsPage />)
    await screen.findByRole('region', { name: /^past meetings$/i })
    // The 2024 <details> should be `open`; its title is rendered.
    const card2024 = screen.getByText('2024 Past Meeting')
    const details2024 = card2024.closest('details')
    expect(details2024).not.toBeNull()
    expect(details2024).toHaveAttribute('open')
    // The 2026 <details> should not be open.
    const card2026 = screen.getByText('2026 Past Meeting').closest('details')
    expect(card2026?.hasAttribute('open')).toBe(false)
  })

  it('renders the next-meeting hero with countdown, CTAs and Add-to-calendar link', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 70,
        title: 'June Hero Meeting',
        scheduled_date: '2099-06-16T22:00:00Z',
        start_time: '2099-06-16T22:00:00Z',
        location: 'Main Branch',
      },
    ])
    render(<BoardMeetingsPage />)
    const hero = await screen.findByRole('region', { name: /^next meeting$/i })
    expect(within(hero).getByText('June Hero Meeting')).toBeInTheDocument()
    expect(within(hero).getByText(/in \d+ days/i)).toBeInTheDocument()
    expect(
      within(hero).getByRole('link', { name: /add to calendar/i }),
    ).toHaveAttribute('href', expect.stringContaining('/board/meetings/calendar.ics'))
    // Read agenda is disabled when agenda_published_at is null.
    expect(
      within(hero).getByLabelText(/read agenda: agenda not yet posted/i),
    ).toBeInTheDocument()
    expect(
      within(hero).getByRole('link', { name: /how to speak at a meeting/i }),
    ).toHaveAttribute('href', '#how-to-speak')
  })

  it('omits the hero when no upcoming meetings exist', async () => {
    mockGet.mockResolvedValue([
      {
        ...baseMeeting,
        id: 80,
        title: 'Already Past',
        scheduled_date: '2024-01-01T22:00:00Z',
      },
    ])
    render(<BoardMeetingsPage />)
    await screen.findByRole('heading', { name: /board meetings/i })
    expect(screen.queryByRole('region', { name: /^next meeting$/i })).toBeNull()
  })

  it('always renders the persistent How to speak module with anchor and 3 steps', async () => {
    mockGet.mockResolvedValue([])
    render(<BoardMeetingsPage />)
    const heading = await screen.findByRole('heading', { name: /how to speak at a meeting/i })
    const section = heading.closest('section')
    expect(section).not.toBeNull()
    expect(section).toHaveAttribute('id', 'how-to-speak')
    expect(within(section!).getByText(/sign in at the door/i)).toBeInTheDocument()
    expect(within(section!).getByText(/you'll have 3 minutes/i)).toBeInTheDocument()
    expect(within(section!).getByText(/recorded in the minutes/i)).toBeInTheDocument()
  })
})

describe('BoardMeetingsPage complete result access', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockSearchMeetings.mockReset()
    mockSearchMeetings.mockResolvedValue({ results: [], total: 0, skip: 0, limit: 50 })
    mockSearchParams.value = new URLSearchParams()
  })

  it('loads every default archive page so an older ?year remains directly accessible', async () => {
    mockSearchParams.value = new URLSearchParams('year=2020')
    const recentMeetings = Array.from({ length: 50 }, (_, index) => ({
      ...baseMeeting,
      id: 1000 + index,
      title: `Recent archive meeting ${index + 1}`,
      scheduled_date: `2025-${String((index % 12) + 1).padStart(2, '0')}-15T22:00:00Z`,
    }))
    const olderMeetings = Array.from({ length: 5 }, (_, index) => ({
      ...baseMeeting,
      id: 2000 + index,
      title: `Older 2020 meeting ${index + 1}`,
      scheduled_date: `2020-0${index + 1}-15T22:00:00Z`,
    }))
    mockGet
      .mockResolvedValueOnce(recentMeetings)
      .mockResolvedValueOnce(olderMeetings)

    render(<BoardMeetingsPage />)

    expect(await screen.findByText('Older 2020 meeting 5')).toBeInTheDocument()
    expect(mockGet).toHaveBeenNthCalledWith(1, expect.stringContaining('limit=50&skip=0'))
    expect(mockGet).toHaveBeenNthCalledWith(2, expect.stringContaining('limit=50&skip=50'))
    const olderDetails = screen.getByText('Older 2020 meeting 1').closest('details')
    expect(olderDetails).toHaveAttribute('open')
    expect(within(olderDetails!).getByText(/5 meetings/i)).toBeInTheDocument()
  })

  it('stops when a backend page repeats instead of rendering duplicate meetings', async () => {
    const repeatedPage = Array.from({ length: 50 }, (_, index) => ({
      ...baseMeeting,
      id: 5000 + index,
      title: `Repeated archive meeting ${index + 1}`,
      scheduled_date: '2025-01-15T22:00:00Z',
    }))
    mockGet
      .mockResolvedValueOnce(repeatedPage)
      .mockResolvedValueOnce(repeatedPage)
      .mockResolvedValueOnce([])

    render(<BoardMeetingsPage />)

    expect(await screen.findByText('Repeated archive meeting 1')).toBeInTheDocument()
    expect(screen.getAllByText('Repeated archive meeting 1')).toHaveLength(1)
  })

  it('loads search results beyond 50 and keeps shown and total counts accurate', async () => {
    mockGet.mockResolvedValue([])
    const firstPage = Array.from({ length: 50 }, (_, index) => ({
      ...baseMeeting,
      id: 3000 + index,
      title: `Budget meeting ${index + 1}`,
      scheduled_date: '2025-01-15T22:00:00Z',
    }))
    const secondPage = Array.from({ length: 5 }, (_, index) => ({
      ...baseMeeting,
      id: 4000 + index,
      title: `Budget meeting ${index + 51}`,
      scheduled_date: '2024-01-15T22:00:00Z',
    }))
    mockSearchMeetings
      .mockResolvedValueOnce({ results: firstPage, total: 55, skip: 0, limit: 50 })
      .mockResolvedValueOnce({ results: secondPage, total: 55, skip: 50, limit: 50 })

    render(<BoardMeetingsPage />)
    const searchInput = await screen.findByRole('textbox', {
      name: /searchMeetingsByTitleDescription2/i,
    })
    fireEvent.change(searchInput, { target: { value: 'budget' } })

    expect(await screen.findByText('Showing 50 of 55 meetings')).toBeInTheDocument()
    expect(mockSearchMeetings).toHaveBeenCalledWith({ q: 'budget', skip: 0, limit: 50 })

    fireEvent.click(screen.getByRole('button', { name: /load more meetings/i }))

    expect(await screen.findByText('Budget meeting 55')).toBeInTheDocument()
    expect(screen.getByText('Showing 55 of 55 meetings')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /load more meetings/i })).toBeNull()
    await waitFor(() => {
      expect(mockSearchMeetings).toHaveBeenLastCalledWith({ q: 'budget', skip: 50, limit: 50 })
    })
  })
})
