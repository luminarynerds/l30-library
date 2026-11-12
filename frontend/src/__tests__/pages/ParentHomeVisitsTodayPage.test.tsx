/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { loadLanguage } from '@/i18n/translations'

// --- Sentry ---------------------------------------------------------------
vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

// --- Shell pass-through ---------------------------------------------------
vi.mock('@/components/shells/AdminShell', () => ({
  AdminShell: ({ children, title }: { title?: string; children: React.ReactNode }) => (
    <div data-testid="admin-shell">
      {title ? <h1 data-testid="admin-shell-title">{title}</h1> : null}
      {children}
    </div>
  ),
}))

// --- Lazy map: avoid loading the real Leaflet module in jsdom -------------
// The page uses React.lazy() to import the map. Vitest+jsdom can't load
// Leaflet's CSS via the import statement and would error. The stub keeps
// the test focused on page-level behavior (cards, sort, modal, sr-only
// list), which is what we actually care about here.
vi.mock('../../components/parent-onboarding/DayPlanMap', () => ({
  default: ({ stops }: { stops: Array<{ visit_id: number }> }) => (
    <div data-testid="day-plan-map-stub">map-{stops.length}</div>
  ),
}))

// --- i18n real-loader -----------------------------------------------------
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, fallback?: string, params?: Record<string, unknown>) =>
        actual.getTranslation(key, 'en', params) ?? fallback ?? key,
      language: 'en',
      isRTL: false,
    }),
  }
})

// --- PII log: assert this is called on render -----------------------------
const piiLogMock = vi.fn()
vi.mock('@/hooks/usePiiAccessLog', () => ({
  usePiiAccessLog: () => piiLogMock,
}))

// --- API surface ---------------------------------------------------------
const getDayPlanMock = vi.fn()
const setSortMock = vi.fn()
const setNotesMock = vi.fn()
const geocodeMock = vi.fn()
vi.mock('@/api/parent-onboarding-api', () => ({
  getHomeVisitDayPlan: (...args: unknown[]) => getDayPlanMock(...args),
  setHomeVisitDayPlanSort: (...args: unknown[]) => setSortMock(...args),
  setHomeVisitAccessNotes: (...args: unknown[]) => setNotesMock(...args),
  geocodeHomeVisit: (...args: unknown[]) => geocodeMock(...args),
}))

import ParentHomeVisitsTodayPage from '@/pages/ParentHomeVisitsTodayPage'

function makeStop(overrides: Record<string, unknown> = {}) {
  return {
    visit_id: 1,
    sort_index: 1,
    scheduled_time: '09:30',
    patron_id: 100,
    patron_name: 'Smith family',
    address: '123 Main St',
    lat: 39.91,
    lng: -83.81,
    purpose: 'intake',
    status: 'scheduled',
    access_notes: null,
    leg_from_previous: null,
    manual_order: false,
    ...overrides,
  }
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/staff/parent-onboarding/home-visits/today']}>
        <ParentHomeVisitsTodayPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  // Per feedback_l30_vitest_i18n_no_preload, English keys aren't loaded by
  // default in the test harness; this surface asserts translated text.
  await loadLanguage('en')
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ParentHomeVisitsTodayPage', () => {
  it('renders one card per stop and writes one PII row per unique patron', async () => {
    const stops = [
      makeStop({ visit_id: 1, patron_id: 100, scheduled_time: '09:30' }),
      makeStop({ visit_id: 2, patron_id: 100, scheduled_time: '11:00' }), // same patron
      makeStop({ visit_id: 3, patron_id: 200, scheduled_time: '13:00' }),
    ]
    getDayPlanMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops,
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: [],
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('day-plan-stop-1')).toBeInTheDocument()
    })
    expect(screen.getByTestId('day-plan-stop-2')).toBeInTheDocument()
    expect(screen.getByTestId('day-plan-stop-3')).toBeInTheDocument()

    // 2 unique patron ids (100 + 200), so 2 PII rows -- not 3.
    expect(piiLogMock).toHaveBeenCalledTimes(2)
    expect(piiLogMock.mock.calls[0]![0]!.patronId).toBe(100)
    expect(piiLogMock.mock.calls[1]![0]!.patronId).toBe(200)
  })

  it('shows the no-geocode badge for stops with null lat/lng', async () => {
    getDayPlanMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops: [makeStop({ visit_id: 1, lat: null, lng: null })],
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: ['no_geocode_for_visit_1'],
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Couldn't locate this address/i)).toBeInTheDocument()
    })
  })

  it('reorders cards via sort button and calls PATCH', async () => {
    const stops = [
      makeStop({ visit_id: 10, patron_id: 100, scheduled_time: '09:00' }),
      makeStop({ visit_id: 20, patron_id: 200, scheduled_time: '11:00' }),
    ]
    getDayPlanMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops,
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: [],
    })
    setSortMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops: [stops[1], stops[0]].map((s, i) => ({ ...s, sort_index: i + 1, manual_order: true })),
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: [],
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('day-plan-stop-1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('sort-down-1'))

    await waitFor(() => {
      // Position 2 (i.e. moving the first stop to index 2 = 1-indexed).
      expect(setSortMock).toHaveBeenCalledWith(10, 2)
    })
  })

  it('opens the edit-notes modal and saves through the API', async () => {
    const stops = [
      makeStop({ visit_id: 1, patron_id: 100, scheduled_time: '09:30' }),
    ]
    getDayPlanMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops,
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: [],
    })
    setNotesMock.mockResolvedValue({
      has_steps: true,
      has_elevator: false,
      multi_floor: false,
      dog_on_premises: false,
      needs_interpreter: false,
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByTestId('day-plan-stop-1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /edit access notes/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    // Toggle the "Steps to entrance" checkbox.
    fireEvent.click(screen.getByLabelText(/steps to entrance/i))
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      expect(setNotesMock).toHaveBeenCalledWith(100, expect.objectContaining({ has_steps: true }))
    })
  })

  it('always emits an sr-only ordered list of stops independent of the map', async () => {
    const stops = [makeStop({ visit_id: 1, patron_name: 'Smith family' })]
    getDayPlanMock.mockResolvedValue({
      date: '2026-05-25',
      visitor_id: 99,
      stops,
      total_drive_minutes: 0,
      total_distance_km: 0,
      warnings: [],
    })

    renderPage()

    await waitFor(() => {
      // sr-only list has aria-label = "Day plan stops" (the srListLabel key).
      const srLists = screen.getAllByLabelText(/day plan stops/i)
      // Both the visible ol and the sr-only ol carry the same label; ensure
      // at least one is sr-only.
      expect(srLists.some((el) => el.className.includes('sr-only'))).toBe(true)
    })
  })
})
