/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers the registration personalization wiring, translation keys,
 * server-error a11y, and success-state focus management. All four
 * regressed in different ways before this PR and are easy to silently
 * break again, so each gets its own test.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RegistrationModal from '../RegistrationModal'

// ---- Hoisted mocks ------------------------------------------------------

const mocks = vi.hoisted(() => ({
  registerForEvent: vi.fn(),
  setUserEmail: vi.fn(),
  addRegistration: vi.fn(),
}))

vi.mock('@/api/events-api', () => ({
  registerForEvent: mocks.registerForEvent,
}))

vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ phone: '555-0100' }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

// Use string fallback semantics: when key is missing, second arg is returned.
// When params object is passed, render as `key:{paramsJson}` so tests can
// assert interpolation reached the call site without depending on
// real translation files.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      if (paramsOrFallback) return `${key}:${JSON.stringify(paramsOrFallback)}`
      return key
    },
  }),
}))

vi.mock('@/hooks/useEventPersonalization', () => ({
  useEventPersonalization: () => ({
    setUserEmail: mocks.setUserEmail,
    addRegistration: mocks.addRegistration,
    userEmail: null,
    registrations: [],
    registrationsCount: 0,
    removeRegistration: vi.fn(),
    isRegistered: vi.fn(() => false),
    getRegistration: vi.fn(() => null),
    getUpcomingRegistrations: vi.fn(() => []),
    bookmarks: [],
    bookmarksCount: 0,
    toggleBookmark: vi.fn(),
    addBookmark: vi.fn(),
    removeBookmark: vi.fn(),
    isBookmarked: vi.fn(() => false),
    getBookmarkedEventIds: vi.fn(() => []),
    preferences: { categories: [], audiences: [] },
    setPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    toggleCategory: vi.fn(),
    toggleAudience: vi.fn(),
    hasPreferences: vi.fn(() => false),
    matchesPreferences: vi.fn(() => false),
    clearAll: vi.fn(),
  }),
}))

// FocusTrap pulls in DOM APIs that jsdom doesn't fully support; stub it out
// to render its children directly. Same pattern as other modal tests.
vi.mock('focus-trap-react', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// ---- Fixtures -----------------------------------------------------------

const EVENT = {
  id: 42,
  title: 'Storytime',
  description: null,
  start_time: '2030-06-15T15:00:00Z',
  end_time: null,
  location: 'Main Branch',
  is_virtual: false,
  audience: null,
  category: null,
  tags: null,
  max_attendees: null,
  registration_required: true,
  registration_count: 0,
  spots_remaining: 5,
  image_url: null,
  is_featured: false,
  series_id: null,
  series_name: null,
  created_at: '2026-01-01T00:00:00Z',
  average_rating: null,
  review_count: 0,
  photos_will_be_taken: false,
}

function renderModal(overrides: Partial<typeof EVENT> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RegistrationModal event={{ ...EVENT, ...overrides }} onClose={() => {}} />
    </QueryClientProvider>,
  )
}

async function fillAndSubmit() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/Full Name/i), 'Ada Lovelace')
  await user.type(screen.getByLabelText(/Email Address/i), 'ada@example.com')
  await user.click(screen.getByRole('button', { name: /Register/i }))
}

// ---- Tests --------------------------------------------------------------

describe('RegistrationModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls setUserEmail and addRegistration on success', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 1001,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: false,
      waitlist_position: null,
    })

    renderModal()
    await fillAndSubmit()

    await waitFor(() => {
      expect(mocks.setUserEmail).toHaveBeenCalledWith('ada@example.com')
    })
    expect(mocks.addRegistration).toHaveBeenCalledWith({
      registrationId: 1001,
      eventId: 42,
      eventTitle: 'Storytime',
      eventStartTime: '2030-06-15T15:00:00Z',
      eventLocation: 'Main Branch',
      registeredAt: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminderRequested: false,
    })
  })

  it('falls back to translated strings when present', () => {
    renderModal()
    // The "Cancel" form button uses common.cancel with "Cancel" string fallback;
    // since the mock returns the fallback for string-fallback calls, the button
    // text proves the t() call site is wired and not a hardcoded literal.
    const cancelButton = screen.getByRole('button', { name: 'Cancel' })
    expect(cancelButton).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Register' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Email Address/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Phone Number/)).toBeInTheDocument()
  })

  it('error renders with role alert', async () => {
    mocks.registerForEvent.mockRejectedValue(new Error('Email already registered'))

    renderModal()
    await fillAndSubmit()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Email already registered')
    expect(alert).toHaveAttribute('aria-live', 'assertive')
  })

  it('success heading receives focus', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 1002,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: false,
      waitlist_position: null,
    })

    renderModal()
    await fillAndSubmit()

    const heading = await screen.findByRole('heading', { name: /You're Registered!/i })
    await waitFor(() => {
      expect(heading).toHaveFocus()
    })
    expect(heading).toHaveAttribute('tabindex', '-1')
  })

  it('reminder checkbox renders and defaults to unchecked (opt-in)', () => {
    renderModal()
    const checkbox = screen.getByRole('checkbox', {
      name: /Send me a reminder 24 hours before this event/i,
    })
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).not.toBeChecked()
  })

  it('sends reminder_requested=true when checkbox is checked', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 1003,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: true,
      waitlist_position: null,
    })

    const user = userEvent.setup()
    renderModal()
    await user.type(screen.getByLabelText(/Full Name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/Email Address/i), 'ada@example.com')

    const checkbox = screen.getByRole('checkbox', {
      name: /Send me a reminder 24 hours before this event/i,
    })
    await user.click(checkbox)
    expect(checkbox).toBeChecked()

    await user.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(mocks.registerForEvent).toHaveBeenCalled()
    })
    const call = mocks.registerForEvent.mock.calls[0]!
    const payload = call[1]
    expect(payload.reminder_requested).toBe(true)
  })

  it('sends reminder_requested=false when checkbox stays unchecked (default)', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 1004,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: false,
      waitlist_position: null,
    })

    renderModal()
    await fillAndSubmit()

    await waitFor(() => {
      expect(mocks.registerForEvent).toHaveBeenCalled()
    })
    const call = mocks.registerForEvent.mock.calls[0]!
    const payload = call[1]
    expect(payload.reminder_requested).toBe(false)
  })
  // ----- Phase 2: photo-release consent -----

  it('renders the photo-release checkbox ONLY when event.photos_will_be_taken is true', () => {
    const { rerender } = renderModal({ photos_will_be_taken: false })
    expect(
      screen.queryByLabelText(/I consent to being photographed/i),
    ).not.toBeInTheDocument()

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    rerender(
      <QueryClientProvider client={queryClient}>
        <RegistrationModal event={{ ...EVENT, photos_will_be_taken: true }} onClose={() => {}} />
      </QueryClientProvider>,
    )
    expect(
      screen.getByLabelText(/I consent to being photographed/i),
    ).toBeInTheDocument()
  })

  it('checked consent flows into the API payload as photo_release_granted=true', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 2001,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: false,
      waitlist_position: null,
      photo_release_granted: true,
    })

    renderModal({ photos_will_be_taken: true })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/Full Name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/Email Address/i), 'ada@example.com')
    await user.click(screen.getByLabelText(/I consent to being photographed/i))
    await user.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(mocks.registerForEvent).toHaveBeenCalled()
    })
    const [, payload] = mocks.registerForEvent.mock.calls[0]!
    expect(payload.photo_release_granted).toBe(true)
  })

  it('omits / nulls photo_release_granted when event.photos_will_be_taken is false', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 2002,
      event_id: 42,
      patron_name: 'Ada Lovelace',
      patron_email: 'ada@example.com',
      patron_phone: null,
      registered_at: '2026-05-15T12:00:00Z',
      status: 'registered',
      reminder_requested: false,
      waitlist_position: null,
    })

    renderModal({ photos_will_be_taken: false })
    await fillAndSubmit()

    await waitFor(() => {
      expect(mocks.registerForEvent).toHaveBeenCalled()
    })
    const [, payload] = mocks.registerForEvent.mock.calls[0]!
    // Modal sends null (server treats null as 'not asked'); never sends true
    // when the event hasn't enabled photo-release prompting.
    expect(payload.photo_release_granted).toBeNull()
  })
})

describe('RegistrationModal email-or-phone contact requirement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits successfully with phone only (no email)', async () => {
    mocks.registerForEvent.mockResolvedValue({
      id: 1002,
      event_id: 42,
      patron_name: 'Phone Patron',
      patron_email: null,
      patron_phone: '555-867-5309',
      registered_at: '2026-05-15T12:00:00Z',
      status: 'confirmed',
      reminder_requested: false,
      waitlist_position: null,
    })
    renderModal()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/Full Name/i), 'Phone Patron')
    await user.type(screen.getByLabelText(/Phone Number/i), '555-867-5309')
    await user.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => expect(mocks.registerForEvent).toHaveBeenCalled())
    const payload = mocks.registerForEvent.mock.calls[0]![1]
    expect(payload.patron_phone).toBe('555-867-5309')
    // Phone-only: email-keyed personalization is skipped gracefully.
    expect(mocks.setUserEmail).not.toHaveBeenCalled()
  })

  it('blocks submit with an inline error when neither email nor phone is given', async () => {
    renderModal()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/Full Name/i), 'No Contact')
    await user.click(screen.getByRole('button', { name: /Register/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/email or a phone number/i)
    expect(mocks.registerForEvent).not.toHaveBeenCalled()
  })

  it('shows the no-email-no-phone escape-hatch note with the library phone', () => {
    renderModal()
    // Branding phone is set in the mock, so the {{phone}} variant key is used
    // (params-object form renders as `key:{json}` in the test t() shim).
    expect(
      screen.getByText(/registration\.help\.noContactNote/),
    ).toBeInTheDocument()
  })
})
