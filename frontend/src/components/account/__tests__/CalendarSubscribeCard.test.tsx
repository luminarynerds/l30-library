/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalendarSubscribeCard } from '../CalendarSubscribeCard'

// Mock fetchApi -- the card calls fetchApi('/me/calendar/token', { method: 'POST' })
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
}))

// Mock react-hot-toast -- the card calls toast.error / toast.success
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// Mock the i18n hook to return the default value passed as the 2nd arg.
// L30 i18n's t() accepts (key, stringDefault) and returns the default when
// no translation is registered. We mirror that here.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

import { fetchApi } from '@/lib/api-client'
const mockFetchApi = fetchApi as unknown as ReturnType<typeof vi.fn>

describe('CalendarSubscribeCard', () => {
  beforeEach(() => {
    mockFetchApi.mockReset()
    // happy-dom (unlike jsdom) already implements navigator.clipboard as a
    // getter-only accessor backed by a real object, so replacing the whole
    // property throws. Spy on the existing writeText method instead.
    vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the get-calendar-link button initially', () => {
    render(<CalendarSubscribeCard />)
    expect(
      screen.getByRole('button', { name: /get calendar link/i })
    ).toBeInTheDocument()
  })

  it('mints a token and shows the webcal URL on button click', async () => {
    const user = userEvent.setup()
    mockFetchApi.mockResolvedValueOnce({
      url: 'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc',
    })

    render(<CalendarSubscribeCard />)
    await user.click(screen.getByRole('button', { name: /get calendar link/i }))

    expect(mockFetchApi).toHaveBeenCalledWith('/me/calendar/token', {
      method: 'POST',
    })

    await waitFor(() => {
      expect(
        screen.getByDisplayValue(
          'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc'
        )
      ).toBeInTheDocument()
    })

    // Google + Apple subscribe links are rendered with the webcal URL embedded.
    const google = screen.getByRole('link', { name: /add to google calendar/i })
    expect(google).toHaveAttribute(
      'href',
      `https://calendar.google.com/calendar/u/0/r?cid=${encodeURIComponent(
        'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc'
      )}`
    )
    const apple = screen.getByRole('link', { name: /add to apple calendar/i })
    expect(apple).toHaveAttribute(
      'href',
      'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc'
    )
  })

  it('copies the URL to clipboard on Copy click', async () => {
    const user = userEvent.setup()
    mockFetchApi.mockResolvedValueOnce({
      url: 'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc',
    })

    render(<CalendarSubscribeCard />)
    await user.click(screen.getByRole('button', { name: /get calendar link/i }))
    await waitFor(() => screen.getByDisplayValue(/^webcal:\/\//))

    // Accessible name comes from aria-label ("Copy URL"), not the visible "Copy" text.
    await user.click(screen.getByRole('button', { name: /copy url/i }))
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      'webcal://l30.org/api/v1/me/calendar.ics?token=42.abc'
    )
  })
})
