/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * PR #999: covers the "event is full → join waitlist" branch added to
 * RegistrationModal. The form re-uses the same fields but the submit goes to
 * the new /events/{id}/waitlist endpoint and the success screen reports the
 * patron's queue position.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RegistrationModal from '../RegistrationModal'

const mocks = vi.hoisted(() => ({
  registerForEvent: vi.fn(),
  joinEventWaitlist: vi.fn(),
  setUserEmail: vi.fn(),
  addRegistration: vi.fn(),
}))

vi.mock('@/api/events-api', () => ({
  registerForEvent: mocks.registerForEvent,
  joinEventWaitlist: mocks.joinEventWaitlist,
}))

vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ phone: '555-0100' }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      // Match real i18n shape: (key, params) -> ICU interpolate the key's
      // template against params; (key, fallbackString) -> fallback verbatim.
      // The real impl looks up the key in translations/en.json; the mock
      // hardcodes the small set of keys this test cares about.
      const TEMPLATES: Record<string, string> = {
        'waitlist.success.bodyWithPosition':
          'You are #{{position}} on the waitlist for {{title}}. We will email you if a spot opens.',
      }
      if (typeof paramsOrFallback === 'object' && paramsOrFallback !== null) {
        let out = TEMPLATES[key] ?? key
        for (const [k, v] of Object.entries(paramsOrFallback)) {
          out = out.replace(new RegExp(`{{${k}}}`, 'g'), String(v))
        }
        return out
      }
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      return key
    },
  }),
}))

vi.mock('@/contexts/PersonalizationContext', () => ({
  usePersonalization: () => ({
    setUserEmail: mocks.setUserEmail,
    addRegistration: mocks.addRegistration,
  }),
}))

const FULL_EVENT = {
  id: 42,
  title: 'Sold Out Storytime',
  description: 'Wildly popular.',
  start_time: '2030-01-01T15:00:00Z',
  end_time: null,
  location: 'Main Branch',
  is_virtual: false,
  audience: null,
  category: null,
  tags: null,
  max_attendees: 10,
  registration_required: true,
  registration_count: 10,
  spots_remaining: 0,
  image_url: null,
  is_featured: false,
  series_id: null,
  series_name: null,
  created_at: '2026-01-01T00:00:00Z',
  average_rating: null,
  review_count: 0,
  photos_will_be_taken: false,
}

function renderModal() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <RegistrationModal event={FULL_EVENT} onClose={() => {}} />
    </QueryClientProvider>,
  )
}

describe('RegistrationModal — waitlist branch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Join Waitlist" button when spots_remaining === 0', () => {
    renderModal()
    // The submit button label switches to the waitlist string.
    const btn = screen.getByRole('button', { name: /waitlist/i })
    expect(btn).toBeTruthy()
  })

  it('submits to joinEventWaitlist (not registerForEvent) and shows position', async () => {
    mocks.joinEventWaitlist.mockResolvedValueOnce({
      id: 7,
      event_id: 42,
      email: 'ada@example.com',
      position: 3,
      status: 'waiting',
      created_at: '2026-05-20T12:00:00Z',
      cancel_token: 'tok',
    })

    renderModal()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/Full Name/i), 'Ada Lovelace')
    await user.type(screen.getByLabelText(/Email Address/i), 'ada@example.com')
    await user.click(screen.getByRole('button', { name: /waitlist/i }))

    await waitFor(() => {
      expect(mocks.joinEventWaitlist).toHaveBeenCalledTimes(1)
    })
    expect(mocks.registerForEvent).not.toHaveBeenCalled()
    expect(mocks.joinEventWaitlist).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ email: 'ada@example.com' }),
    )
    // Position reaches the success body.
    await waitFor(() => {
      expect(screen.getByText(/#3/)).toBeTruthy()
    })
  })
})
