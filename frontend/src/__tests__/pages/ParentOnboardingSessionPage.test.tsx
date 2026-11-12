/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { loadLanguage } from '@/i18n/translations'

// Stub the Sentry lazy wrapper so we can introspect captureException args.
const captureExceptionMock = vi.fn()
vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: (...args: unknown[]) => captureExceptionMock(...args),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

// StaffLayout requires AuthContext + Preferences + sidebar config to render.
// Replace it with a pass-through so this test focuses on the page-level
// behavior (shell wrapping, labels, scrubbed Sentry calls) rather than the
// full staff chrome.
vi.mock('@/components/staff/StaffLayout', () => ({
  StaffLayout: ({
    title,
    children,
  }: {
    title?: string
    children: React.ReactNode
  }) => (
    <div data-testid="staff-layout">
      {title ? <div data-testid="staff-layout-title">{title}</div> : null}
      {children}
    </div>
  ),
}))

// Use the real i18n module but in English.
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown>) =>
        actual.getTranslation(key, 'en', params),
      language: 'en',
      isRTL: false,
    }),
  }
})

// Mock the API surface so the page never hits the network.
const getSessionMock = vi.fn()
const updateSessionMock = vi.fn()
const completeSessionMock = vi.fn()
vi.mock('@/api/parent-onboarding-api', () => ({
  getSession: (id: number) => getSessionMock(id),
  updateSession: (id: number, data: unknown) => updateSessionMock(id, data),
  completeSession: (id: number, data: unknown) => completeSessionMock(id, data),
}))

import ParentOnboardingSessionPage, {
  scrubPatronError,
} from '@/pages/ParentOnboardingSessionPage'

beforeAll(async () => {
  await loadLanguage('en')
})

beforeEach(() => {
  captureExceptionMock.mockReset()
  getSessionMock.mockReset()
  updateSessionMock.mockReset()
  completeSessionMock.mockReset()
})

const baseSession = {
  id: 42,
  patron_id: 7,
  staff_id: null,
  branch_id: 1,
  status: 'scheduled',
  scheduled_at: '2026-06-01T00:00:00Z',
  completed_at: null,
  baby_age_months: null,
  languages_spoken: [],
  family_situation_notes: 'existing notes',
  needs_identified: [],
  services_referred: [],
  welcome_packet_id: null,
}

function renderPage(id = '42') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[`/staff/parent-onboarding/sessions/${id}`]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route
            path="/staff/parent-onboarding/sessions/:id"
            element={<ParentOnboardingSessionPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('scrubPatronError', () => {
  it('drops response.data (patron PII) but keeps status, message, endpoint', () => {
    const raw = {
      message: 'Request failed with status code 500',
      response: {
        status: 500,
        config: { url: '/api/v1/parent-onboarding/sessions/42' },
        // Patron PII that MUST NOT reach Sentry
        data: {
          patron_name: 'Joan Q. Patron',
          patron_id: 9001,
          notes: 'Family in crisis, see follow-up',
        },
      },
    }
    const scrubbed = scrubPatronError(raw)
    expect(scrubbed.message).toBe('Request failed with status code 500')
    expect(scrubbed.status).toBe(500)
    expect(scrubbed.endpoint).toBe('/api/v1/parent-onboarding/sessions/42')
    // The scrubbed shape MUST NOT mention patron data.
    const serialized = JSON.stringify(scrubbed)
    expect(serialized).not.toMatch(/patron_name/i)
    expect(serialized).not.toMatch(/Joan/)
    expect(serialized).not.toMatch(/follow-up/i)
  })

  it('returns a safe message for non-object input', () => {
    expect(scrubPatronError(null)).toEqual({ message: 'Unknown error' })
    expect(scrubPatronError('boom').message).toBe('boom')
  })
})

describe('ParentOnboardingSessionPage shell + a11y', () => {
  it('renders inside AdminShell while loading (StaffLayout title visible)', () => {
    // Never-resolving promise to keep the query in loading state.
    getSessionMock.mockReturnValue(new Promise(() => {}))
    renderPage()
    // AdminShell delegates to StaffLayout(title=...). With the StaffLayout
    // passthrough mock the title shows up in [data-testid="staff-layout-title"].
    // The bug was: the loading branch returned a raw <div> with no shell, so
    // staff lost the nav. Assert the title rendered = shell wrapped loading.
    expect(screen.getByTestId('staff-layout-title')).toHaveTextContent(
      /Onboarding Session/i,
    )
  })

  it('renders AdminShell error state when the query fails', async () => {
    getSessionMock.mockRejectedValue(new Error('nope'))
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Failed to load session/i)).toBeInTheDocument(),
    )
  })

  it('wires notes/status labels to their inputs via htmlFor', async () => {
    getSessionMock.mockResolvedValue(baseSession)
    const { default: userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    renderPage()

    // Click Edit to expose the notes/status inputs.
    const editBtn = await screen.findByRole('button', { name: /^edit$/i })
    await user.click(editBtn)

    const notesTextarea = screen.getByLabelText(/^Notes$/i) as HTMLTextAreaElement
    const statusSelect = screen.getByLabelText(/^Status$/i) as HTMLSelectElement

    expect(notesTextarea.id).toBe('session-notes')
    expect(statusSelect.id).toBe('session-status')
  })

  it('Save sends family_situation_notes/status -- not the legacy notes/location fields', async () => {
    getSessionMock.mockResolvedValue(baseSession)
    updateSessionMock.mockResolvedValue(baseSession)
    const { default: userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    renderPage()

    const editBtn = await screen.findByRole('button', { name: /^edit$/i })
    await user.click(editBtn)

    const notesTextarea = screen.getByLabelText(/^Notes$/i) as HTMLTextAreaElement
    await user.clear(notesTextarea)
    await user.type(notesTextarea, 'updated family notes')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    await user.click(saveBtn)

    await waitFor(() => expect(updateSessionMock).toHaveBeenCalledTimes(1))
    // Exact-match: any stray legacy field (notes/location) would fail this.
    expect(updateSessionMock).toHaveBeenCalledWith(42, {
      family_situation_notes: 'updated family notes',
      status: 'scheduled',
    })
  })

  it('Mark Complete sends only family_situation_notes -- not the legacy outcome fields', async () => {
    getSessionMock.mockResolvedValue(baseSession)
    completeSessionMock.mockResolvedValue({ ...baseSession, status: 'completed' })
    const { default: userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    renderPage()

    const completeBtn = await screen.findByRole('button', { name: /complete/i })
    await user.click(completeBtn)

    const outcomesTextarea = screen.getByLabelText(/outcomes/i) as HTMLTextAreaElement
    await user.type(outcomesTextarea, 'Referred to WIC.')

    const markCompleteBtn = screen.getByRole('button', { name: /mark complete/i })
    await user.click(markCompleteBtn)

    await waitFor(() => expect(completeSessionMock).toHaveBeenCalledTimes(1))
    // Exact-match: any stray legacy field (outcomes/resources_provided/
    // referrals_made/follow_up_date) would fail this.
    expect(completeSessionMock).toHaveBeenCalledWith(42, {
      family_situation_notes: 'Referred to WIC.',
    })
  })

  it('captureException receives a scrubbed payload (no response body) on query error', async () => {
    const piiError = {
      message: 'boom',
      response: {
        status: 500,
        config: { url: '/api/v1/parent-onboarding/sessions/42' },
        data: { patron_name: 'Joan Q. Patron' },
      },
    }
    getSessionMock.mockRejectedValue(piiError)
    renderPage()
    await waitFor(() => expect(captureExceptionMock).toHaveBeenCalled())
    const firstArg = captureExceptionMock.mock.calls[0]?.[0]
    expect(JSON.stringify(firstArg)).not.toMatch(/Joan|patron_name/)
    expect(firstArg).toMatchObject({ status: 500 })
  })
})
