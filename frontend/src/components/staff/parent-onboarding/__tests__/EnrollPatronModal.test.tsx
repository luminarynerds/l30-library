/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

// Echo translation keys so we can assert on key paths rather than
// locale-rendered text (L30 vitest setup doesn't preload i18n).
const { tEcho } = vi.hoisted(() => ({
  tEcho: (key: string, opts?: Record<string, unknown>) =>
    opts ? `${key}|${JSON.stringify(opts)}` : key,
}))
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: tEcho }),
  // Modal.tsx uses the bare `t` export, not the hook; expose both.
  t: tEcho,
}))

vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))

const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))
vi.mock('react-hot-toast', () => ({
  default: { success: toastSuccess, error: toastError },
}))

const { enrollMock, searchMock } = vi.hoisted(() => ({
  enrollMock: vi.fn(),
  searchMock: vi.fn(),
}))
vi.mock('@/api/parent-onboarding-api', () => ({
  enrollPatronInGroup: enrollMock,
}))
vi.mock('@/api/staff-api/patrons', () => ({
  searchPatronsSuggestions: searchMock,
}))

const { authUser, authToken } = vi.hoisted(() => ({
  authUser: { role: 'staff' as string },
  authToken: 'tok',
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: authUser, token: authToken }),
}))

// Modal uses focus-trap-react which needs at least one focusable element on
// mount; stub it out for testing simplicity.
vi.mock('focus-trap-react', () => ({
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import { EnrollPatronModal } from '../EnrollPatronModal'

const group = {
  id: 12,
  name: 'Tuesday Crew',
  group_type: 'first_time_parents' as const,
  max_members: 10,
  current_members: 5,
  is_active: true,
  created_at: '2026-01-01',
}

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

beforeEach(() => {
  enrollMock.mockReset()
  searchMock.mockReset()
  toastSuccess.mockReset()
  toastError.mockReset()
  authUser.role = 'staff'
})

describe('EnrollPatronModal', () => {
  it('disables submit until a patron is selected', async () => {
    render(
      wrap(
        <EnrollPatronModal group={group} isOpen={true} onClose={() => {}} />,
      ),
    )
    const submit = await screen.findByTestId('enroll-submit')
    expect(submit).toBeDisabled()
  })

  it('hides override toggle for non-admin even when the group is full', async () => {
    authUser.role = 'staff'
    const fullGroup = { ...group, current_members: 10, max_members: 10 }
    render(
      wrap(
        <EnrollPatronModal
          group={fullGroup}
          isOpen={true}
          onClose={() => {}}
        />,
      ),
    )
    expect(
      screen.queryByTestId('enroll-override-section'),
    ).not.toBeInTheDocument()
  })

  it('shows override toggle for admin when the group is full', async () => {
    authUser.role = 'admin'
    const fullGroup = { ...group, current_members: 10, max_members: 10 }
    render(
      wrap(
        <EnrollPatronModal
          group={fullGroup}
          isOpen={true}
          onClose={() => {}}
        />,
      ),
    )
    expect(
      await screen.findByTestId('enroll-override-section'),
    ).toBeInTheDocument()
  })

  it('capacity readout reflects available spots when group has room', async () => {
    render(
      wrap(
        <EnrollPatronModal
          group={{ ...group, current_members: 3, max_members: 10 }}
          isOpen={true}
          onClose={() => {}}
        />,
      ),
    )
    const readout = await screen.findByTestId('enroll-capacity-readout')
    expect(readout.textContent).toMatch(/capacityAvailable/)
    expect(readout.textContent).toMatch(/"current":3/)
    expect(readout.textContent).toMatch(/"available":7/)
  })

  it('capacity readout shows full-group + waitlist warning when full', async () => {
    render(
      wrap(
        <EnrollPatronModal
          group={{ ...group, current_members: 10, max_members: 10 }}
          isOpen={true}
          onClose={() => {}}
        />,
      ),
    )
    const readout = await screen.findByTestId('enroll-capacity-readout')
    expect(readout.textContent).toMatch(/capacityFull/)
  })

  it('success toast key matches successWaitlist when backend returns waitlisted', async () => {
    searchMock.mockResolvedValue([
      { id: 99, first_name: 'Maria', last_name: 'L', email: 'm@x', role: 'patron', library_card_number: 'P9' },
    ])
    enrollMock.mockResolvedValue({
      id: 1, group_id: 12, patron_id: 99, status: 'waitlisted',
      joined_date: '2026-05-18', consent_note_recorded: false,
      capacity_overridden: false,
    })
    render(
      wrap(
        <EnrollPatronModal group={group} isOpen={true} onClose={() => {}} />,
      ),
    )
    const input = await screen.findByTestId('enroll-patron-input')
    fireEvent.change(input, { target: { value: 'Ma' } })
    // Wait for debounced search + results to appear.
    const result = await screen.findByTestId('enroll-patron-result', {}, { timeout: 1500 })
    fireEvent.click(result)
    const submit = await screen.findByTestId('enroll-submit')
    fireEvent.click(submit)
    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalled()
    })
    const msg = toastSuccess.mock.calls[0]?.[0] as string
    expect(msg).toMatch(
      /parentOnboarding\.connectionGroups\.enroll\.successWaitlist/,
    )
  })

  it('success toast key matches successActive when backend returns active', async () => {
    searchMock.mockResolvedValue([
      { id: 100, first_name: 'Jo', last_name: 'B', email: 'j@x', role: 'patron', library_card_number: 'P10' },
    ])
    enrollMock.mockResolvedValue({
      id: 2, group_id: 12, patron_id: 100, status: 'active',
      joined_date: '2026-05-18', consent_note_recorded: true,
      capacity_overridden: false,
    })
    render(
      wrap(
        <EnrollPatronModal group={group} isOpen={true} onClose={() => {}} />,
      ),
    )
    const input = await screen.findByTestId('enroll-patron-input')
    fireEvent.change(input, { target: { value: 'Jo' } })
    const result = await screen.findByTestId('enroll-patron-result', {}, { timeout: 1500 })
    fireEvent.click(result)
    const submit = await screen.findByTestId('enroll-submit')
    fireEvent.click(submit)
    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalled()
    })
    const msg = toastSuccess.mock.calls[0]?.[0] as string
    expect(msg).toMatch(
      /parentOnboarding\.connectionGroups\.enroll\.successActive/,
    )
  })
})
