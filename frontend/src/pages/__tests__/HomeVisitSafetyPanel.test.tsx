/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mock `@/i18n` BEFORE importing the component so its `useTranslation`
// call resolves to a no-op identity function. The real I18nContext throws
// outside an `<I18nProvider>` and the project's vitest setup does not
// preload one (memory: feedback_l30_test_build_env).
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

import { HomeVisitSafetyPanel } from '../ParentHomeVisitsPage'

// Mock the org-features context to flip the safety flag on for these tests.
// The component renders nothing when the flag is off, so flag-off coverage
// is exercised by the "renders nothing when flag is off" case.
let isFeatureEnabledMock = vi.fn().mockReturnValue(true)
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: null,
    loading: false,
    refetch: vi.fn(),
    isFeatureEnabled: (name: string) => isFeatureEnabledMock(name),
  }),
}))

// Mock the API client so the buttons assert against call signatures
// rather than firing real network requests through happy-dom.
const checkinFn = vi.fn().mockResolvedValue({
  visit_id: 7,
  safety_checkin_at: '2026-05-20T16:00:00Z',
  safety_checkout_at: null,
  safety_checkout_due_at: '2026-05-20T17:15:00Z',
  safety_buddy_user_id: 42,
  buddy_warning: null,
})
const checkoutFn = vi.fn().mockResolvedValue({
  visit_id: 7,
  safety_checkin_at: '2026-05-20T16:00:00Z',
  safety_checkout_at: '2026-05-20T16:45:00Z',
  safety_checkout_due_at: '2026-05-20T17:15:00Z',
  safety_buddy_user_id: 42,
  buddy_warning: null,
})
vi.mock('@/api/parent-onboarding-api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    '@/api/parent-onboarding-api',
  )
  return {
    ...actual,
    homeVisitSafetyCheckin: (...args: unknown[]) => checkinFn(...args),
    homeVisitSafetyCheckout: (...args: unknown[]) => checkoutFn(...args),
  }
})

// `react-hot-toast` writes to stdout in happy-dom; silence + intercept.
vi.mock('react-hot-toast', () => {
  const fn = vi.fn() as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }
  fn.success = vi.fn()
  fn.error = vi.fn()
  return { default: fn }
})

function withQuery(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>
}

const baseVisit = {
  id: 7,
  patron_id: 1,
  visitor_id: 2,
  purpose: 'intake' as const,
  status: 'scheduled' as const,
  scheduled_date: '2026-05-20',
  follow_up_needed: false,
  created_at: '2026-05-19T00:00:00Z',
}

describe('HomeVisitSafetyPanel', () => {
  beforeEach(() => {
    checkinFn.mockClear()
    checkoutFn.mockClear()
    isFeatureEnabledMock = vi.fn().mockReturnValue(true)
  })

  it('renders nothing when the feature flag is off', () => {
    isFeatureEnabledMock = vi.fn().mockReturnValue(false)
    const { container } = render(
      withQuery(<HomeVisitSafetyPanel visit={{ ...baseVisit }} />),
    )
    expect(container.textContent).toBe('')
  })

  it('calls the check-in endpoint with the duration in the textbox', async () => {
    render(
      withQuery(<HomeVisitSafetyPanel visit={{ ...baseVisit }} />),
    )

    const input = screen.getByLabelText(/Expected visit duration/i)
    fireEvent.change(input, { target: { value: '90' } })

    fireEvent.click(screen.getByRole('button', { name: /Mark Safe Arrival/i }))

    await waitFor(() => expect(checkinFn).toHaveBeenCalledTimes(1))
    expect(checkinFn).toHaveBeenCalledWith(7, 90)
  })

  it('calls the check-out endpoint after arrival is recorded', async () => {
    render(
      withQuery(
        <HomeVisitSafetyPanel
          visit={{
            ...baseVisit,
            safety_checkin_at: '2026-05-20T16:00:00Z',
            safety_checkout_due_at: '2026-05-20T17:15:00Z',
          }}
        />,
      ),
    )

    fireEvent.click(screen.getByRole('button', { name: /Mark Safe Departure/i }))

    await waitFor(() => expect(checkoutFn).toHaveBeenCalledTimes(1))
    expect(checkoutFn).toHaveBeenCalledWith(7)
  })

  it('renders the overdue badge when due-at has passed and no checkout', () => {
    const overdueDue = new Date(Date.now() - 30 * 60 * 1000).toISOString()
    render(
      withQuery(
        <HomeVisitSafetyPanel
          visit={{
            ...baseVisit,
            safety_checkin_at: '2026-05-20T15:00:00Z',
            safety_checkout_due_at: overdueDue,
          }}
        />,
      ),
    )

    const badge = screen.getByRole('status', { name: /Safety check-out overdue/i })
    expect(badge).toBeTruthy()
    expect(badge.textContent).toMatch(/Check-out overdue/i)
  })
})
