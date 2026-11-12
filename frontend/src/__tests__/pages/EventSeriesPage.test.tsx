/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ReactNode } from 'react'
import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { getTranslation } from '@/i18n/translations'

import EventSeriesPage from '@/pages/EventSeriesPage'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

// TurnstileWidget (rendered inside the bulk-register form) calls useTranslation()
// from '@/i18n', which throws "useTranslation must be used within I18nProvider"
// when there's no I18nProvider in the tree — this page's test Wrapper doesn't
// include one. That throw unmounts the whole render (no error boundary here),
// which is why the header/CTA assertions were timing out even though the page
// itself renders plain English strings. Resolve through the real en dictionary
// so any t(key, fallback) call behaves like production.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) =>
      typeof paramsOrFallback === 'string'
        ? getTranslation(key, 'en', undefined, paramsOrFallback)
        : getTranslation(key, 'en', paramsOrFallback),
  }),
}))

vi.mock('@/hooks/usePageMeta', () => ({
  usePageMeta: vi.fn(),
}))

const mockFetch = vi.fn()
;(globalThis as unknown as { fetch: typeof fetch }).fetch = mockFetch

function buildWrapper(queryClient: QueryClient, initialPath: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrandingProvider>
          <I18nProvider>
            <MemoryRouter initialEntries={[initialPath]}>
              <Routes>
                <Route path="/events/series/:seriesId" element={children} />
              </Routes>
            </MemoryRouter>
          </I18nProvider>
        </BrandingProvider>
      </QueryClientProvider>
    )
  }
}

function jsonOk(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as unknown as Response
}

const seriesPayload = {
  series_id: 'tech-help-tuesday',
  series_name: 'Tech Help Tuesday',
  description: 'Drop in for weekly tech support.',
  category: 'education',
  audience: 'adults',
  min_age: null,
  max_age: null,
  presenters: null,
  recurrence_summary: '4 upcoming sessions through Jun 30, 2026',
  upcoming_count: 4,
  occurrences: [
    {
      event_id: 101,
      start_time: '2026-06-02T18:00:00Z',
      end_time: '2026-06-02T19:00:00Z',
      location: 'Main branch',
      is_published: true,
      max_attendees: null,
      spots_remaining: null,
      registration_required: true,
    },
    {
      event_id: 102,
      start_time: '2026-06-09T18:00:00Z',
      end_time: '2026-06-09T19:00:00Z',
      location: 'Main branch',
      is_published: true,
      max_attendees: 10,
      spots_remaining: 3,
      registration_required: true,
    },
  ],
}

describe('EventSeriesPage', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('renders the series header, occurrences list, and the bulk CTA', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/events/series/tech-help-tuesday') && !url.endsWith('/register')) {
        return Promise.resolve(jsonOk(seriesPayload))
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const Wrapper = buildWrapper(client, '/events/series/tech-help-tuesday')

    render(<EventSeriesPage />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /tech help tuesday/i, level: 1 })).toBeInTheDocument()
    })
    expect(screen.getByText(/4 upcoming sessions/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /register for all 4 sessions/i }),
    ).toBeInTheDocument()
    expect(screen.getAllByText(/main branch/i).length).toBeGreaterThanOrEqual(2)
  })

  it('fires the bulk-register mutation with the series id on submit', async () => {
    const registerResponse = {
      series_id: 'tech-help-tuesday',
      series_name: 'Tech Help Tuesday',
      total_upcoming: 4,
      registered_count: 4,
      already_registered_count: 0,
      waitlisted_count: 0,
      failed_count: 0,
      outcomes: [],
    }

    mockFetch.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/events/series/tech-help-tuesday/register')) {
        expect(init?.method).toBe('POST')
        const body = JSON.parse(init?.body as string)
        expect(body.patron_email).toBe('caregiver@example.com')
        return Promise.resolve(jsonOk(registerResponse))
      }
      if (url.includes('/events/series/tech-help-tuesday')) {
        return Promise.resolve(jsonOk(seriesPayload))
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    })

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const Wrapper = buildWrapper(client, '/events/series/tech-help-tuesday')
    const user = userEvent.setup()

    render(<EventSeriesPage />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /tech help tuesday/i, level: 1 })).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText(/^name$/i), 'A Caregiver')
    await user.type(screen.getByLabelText(/^email$/i), 'caregiver@example.com')
    await user.click(screen.getByRole('button', { name: /register for all 4 sessions/i }))

    await waitFor(() => {
      expect(screen.getByText(/you are registered for the series/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/4 new registrations/i)).toBeInTheDocument()
  })

  it('renders an error state when the series 404s', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail: 'Series not found' }),
      text: () => Promise.resolve(''),
    } as unknown as Response)

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const Wrapper = buildWrapper(client, '/events/series/missing')

    render(<EventSeriesPage />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /series not found/i })).toBeInTheDocument()
  })
})
