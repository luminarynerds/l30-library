/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type React from 'react'

// Mock `@/i18n` so useTranslation resolves outside the I18nProvider.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    // Return the fallback (2nd arg) so the test can match human-readable text
    // rather than dotted i18n keys (memory: feedback_l30_vitest_i18n_no_preload).
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

// Org-features context is consumed by HomeVisitSafetyPanel (which is also
// rendered by the page in real usage). Safety panel is OFF in these tests
// so the actions row is the only mutation surface under test.
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: null,
    loading: false,
    refetch: vi.fn(),
    isFeatureEnabled: () => false,
  }),
}))

const confirmFn = vi.fn().mockResolvedValue({})
const completeFn = vi.fn().mockResolvedValue({})
const cancelFn = vi.fn().mockResolvedValue({})
const rescheduleFn = vi.fn().mockResolvedValue({ visit: {}, replacement_visit: {} })
const conflictsFn = vi.fn().mockResolvedValue({ has_conflict: false, conflicting_visits: [] })

vi.mock('@/api/parent-onboarding-api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    '@/api/parent-onboarding-api',
  )
  return {
    ...actual,
    confirmHomeVisit: (...args: unknown[]) => confirmFn(...args),
    completeHomeVisitWithOutcomes: (...args: unknown[]) => completeFn(...args),
    cancelHomeVisit: (...args: unknown[]) => cancelFn(...args),
    rescheduleHomeVisit: (...args: unknown[]) => rescheduleFn(...args),
    checkHomeVisitConflicts: (...args: unknown[]) => conflictsFn(...args),
  }
})

vi.mock('react-hot-toast', () => {
  const fn = vi.fn() as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }
  fn.success = vi.fn()
  fn.error = vi.fn()
  return { default: fn }
})

import { HomeVisitActions } from '../ParentHomeVisitsPage'

function withQuery(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>
}

const baseVisit = {
  id: 7,
  patron_id: 1,
  visitor_id: 2,
  purpose: 'intake' as const,
  status: 'scheduled' as const,
  scheduled_date: '2026-06-01',
  scheduled_time: '10:00',
  follow_up_needed: false,
  created_at: '2026-05-20T00:00:00Z',
}

beforeEach(() => {
  confirmFn.mockReset().mockResolvedValue({})
  completeFn.mockReset().mockResolvedValue({})
  cancelFn.mockReset().mockResolvedValue({})
  rescheduleFn.mockReset().mockResolvedValue({ visit: {}, replacement_visit: {} })
  conflictsFn.mockReset().mockResolvedValue({ has_conflict: false, conflicting_visits: [] })
})

describe('HomeVisitActions', () => {
  it('shows Confirm / Mark complete / Reschedule / Cancel for a scheduled visit', () => {
    render(withQuery(<HomeVisitActions visit={baseVisit} />))
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark complete' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reschedule' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel visit' })).toBeInTheDocument()
  })

  it('hides Confirm for an already-confirmed visit', () => {
    render(withQuery(<HomeVisitActions visit={{ ...baseVisit, status: 'confirmed' }} />))
    expect(screen.queryByRole('button', { name: 'Confirm' })).not.toBeInTheDocument()
    // The other three still apply to confirmed visits.
    expect(screen.getByRole('button', { name: 'Mark complete' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reschedule' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel visit' })).toBeInTheDocument()
  })

  it('renders no action row for a terminal status', () => {
    const { container } = render(
      withQuery(<HomeVisitActions visit={{ ...baseVisit, status: 'completed' }} />),
    )
    expect(container.querySelector('[role="group"]')).toBeNull()
  })

  it('confirm button fires confirmHomeVisit with the visit id', async () => {
    render(withQuery(<HomeVisitActions visit={baseVisit} />))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    await waitFor(() => expect(confirmFn).toHaveBeenCalledWith(7))
  })

  it('cancel modal requires the notify-acknowledged checkbox before submit', async () => {
    render(withQuery(<HomeVisitActions visit={baseVisit} />))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel visit' }))
    // Modal title is rendered.
    expect(await screen.findByText('Cancel visit', { selector: 'h2' })).toBeInTheDocument()

    // Submit button starts disabled because notify checkbox not yet ticked.
    const submit = screen.getByRole('button', { name: 'Cancel this visit' })
    expect(submit).toBeDisabled()

    // Tick the checkbox and submit unlocks.
    const checkbox = screen.getByRole('checkbox', {
      name: /notified the family/i,
    })
    fireEvent.click(checkbox)
    expect(submit).not.toBeDisabled()
  })

  it('complete modal disables submit until outcomes are entered', async () => {
    render(withQuery(<HomeVisitActions visit={baseVisit} />))
    fireEvent.click(screen.getByRole('button', { name: 'Mark complete' }))
    const submit = await screen.findByRole('button', { name: 'Save outcomes' })
    expect(submit).toBeDisabled()

    const textarea = screen.getByLabelText(/^Outcomes\b/i)
    fireEvent.change(textarea, { target: { value: 'Family received intake packet.' } })
    expect(submit).not.toBeDisabled()
  })

  it('reschedule modal disables submit until both date and reason are filled', async () => {
    render(withQuery(<HomeVisitActions visit={baseVisit} />))
    fireEvent.click(screen.getByRole('button', { name: 'Reschedule' }))
    // Modal title confirms the modal opened. After this the buttons named
    // "Reschedule" include both the action-row trigger and the modal submit;
    // find the submit via its type=submit attribute.
    expect(await screen.findByText('Reschedule visit', { selector: 'h2' })).toBeInTheDocument()
    const submitButtons = screen.getAllByRole('button', { name: 'Reschedule' })
    const submit = submitButtons.find(
      (b) => (b as HTMLButtonElement).type === 'submit',
    ) as HTMLButtonElement
    expect(submit).toBeDefined()
    // Both date and reason are required, so submit starts disabled.
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/New date/i), {
      target: { value: '2026-06-15' },
    })
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/Reason for reschedule/i), {
      target: { value: 'Family needs evening slot' },
    })
    expect(submit).not.toBeDisabled()
  })
})
