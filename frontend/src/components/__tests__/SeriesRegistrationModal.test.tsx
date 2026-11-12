/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers SeriesRegistrationModal (events review enhancement #3): the form
 * renders for a series, submission posts to registerForSeries, and the
 * success view reports each occurrence's outcome.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMockEvent } from '@/__tests__/helpers/testHelpers'
import SeriesRegistrationModal from '../SeriesRegistrationModal'

// ---- Hoisted mocks ------------------------------------------------------

const mocks = vi.hoisted(() => ({
  registerForSeries: vi.fn(),
  setUserEmail: vi.fn(),
  addRegistration: vi.fn(),
}))

vi.mock('@/api/events-api', () => ({
  registerForSeries: mocks.registerForSeries,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

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
  }),
}))

vi.mock('focus-trap-react', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Turnstile: a button the test clicks to supply a verification token,
// keeping the submit button's enabled state deterministic.
vi.mock('@/components/TurnstileWidget', () => ({
  TurnstileWidget: ({ onVerify }: { onVerify: (token: string) => void }) => (
    <button type="button" onClick={() => onVerify('test-token')}>
      mock-verify
    </button>
  ),
}))

// ---- Fixtures -----------------------------------------------------------

const seriesEvents = [
  createMockEvent({ id: 1, title: 'Week One', start_time: '2026-08-01T18:00:00Z', registration_required: true }),
  createMockEvent({ id: 2, title: 'Week Two', start_time: '2026-08-08T18:00:00Z', registration_required: true }),
]

function renderModal() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <SeriesRegistrationModal
        seriesId="s1"
        seriesName="Story Series"
        seriesEvents={seriesEvents}
        onClose={() => {}}
      />
    </QueryClientProvider>,
  )
}

async function fillAndSubmit() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/Full Name/i), 'Ada Lovelace')
  await user.type(screen.getByLabelText(/Email Address/i), 'ada@example.com')
  await user.click(screen.getByRole('button', { name: 'mock-verify' }))
  await user.click(screen.getByRole('button', { name: /register for all sessions/i }))
}

// ---- Tests --------------------------------------------------------------

describe('SeriesRegistrationModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the series registration form', () => {
    renderModal()
    expect(screen.getByText('Story Series')).toBeInTheDocument()
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /register for all sessions/i })).toBeInTheDocument()
  })

  it('posts to registerForSeries and shows a per-occurrence outcome list', async () => {
    mocks.registerForSeries.mockResolvedValue({
      series_id: 's1',
      series_name: 'Story Series',
      total_upcoming: 2,
      registered_count: 2,
      already_registered_count: 0,
      waitlisted_count: 0,
      failed_count: 0,
      outcomes: [
        { event_id: 1, start_time: '2026-08-01T18:00:00Z', status: 'registered', registration_id: 101, waitlist_position: null, error: null },
        { event_id: 2, start_time: '2026-08-08T18:00:00Z', status: 'registered', registration_id: 102, waitlist_position: null, error: null },
      ],
    })

    renderModal()
    await fillAndSubmit()

    await waitFor(() => {
      expect(mocks.registerForSeries).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({ patron_email: 'ada@example.com', patron_name: 'Ada Lovelace' }),
      )
    })
    // Both occurrences confirmed → two "Registered" badges in the outcome list.
    await waitFor(() => {
      expect(screen.getAllByText('Registered')).toHaveLength(2)
    })
    // Each confirmed occurrence is mirrored into client-side personalization.
    expect(mocks.setUserEmail).toHaveBeenCalledWith('ada@example.com')
    expect(mocks.addRegistration).toHaveBeenCalledTimes(2)
  })

  it('reports a drop-in occurrence the backend could not register', async () => {
    mocks.registerForSeries.mockResolvedValue({
      series_id: 's1',
      series_name: 'Story Series',
      total_upcoming: 2,
      registered_count: 1,
      already_registered_count: 0,
      waitlisted_count: 0,
      failed_count: 1,
      outcomes: [
        { event_id: 1, start_time: '2026-08-01T18:00:00Z', status: 'registered', registration_id: 101, waitlist_position: null, error: null },
        { event_id: 2, start_time: '2026-08-08T18:00:00Z', status: 'error', registration_id: null, waitlist_position: null, error: 'Event does not require registration' },
      ],
    })

    renderModal()
    await fillAndSubmit()

    await waitFor(() => {
      expect(screen.getByText('Registered')).toBeInTheDocument()
    })
    expect(screen.getByText('No registration needed')).toBeInTheDocument()
    // The failed/drop-in occurrence is not mirrored into personalization.
    expect(mocks.addRegistration).toHaveBeenCalledTimes(1)
  })
})
