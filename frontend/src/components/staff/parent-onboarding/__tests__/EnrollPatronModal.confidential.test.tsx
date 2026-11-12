/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Confidential-group variant of EnrollPatronModal.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

// Hoisted mock handles let the assertions inspect call args by reference,
// instead of re-importing the mocked module.
const {
  enrollPatronInGroupMock,
  requestToJoinConfidentialGroupMock,
  searchPatronsSuggestionsMock,
} = vi.hoisted(() => ({
  enrollPatronInGroupMock: vi.fn(),
  requestToJoinConfidentialGroupMock: vi.fn(),
  searchPatronsSuggestionsMock: vi.fn(),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))
vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'tok', user: { id: 1, role: 'staff' } }),
}))
vi.mock('@/api/staff-api/patrons', () => ({
  searchPatronsSuggestions: (...args: unknown[]) => searchPatronsSuggestionsMock(...args),
}))
vi.mock('@/api/parent-onboarding-api', () => ({
  enrollPatronInGroup: (...args: unknown[]) => enrollPatronInGroupMock(...args),
  requestToJoinConfidentialGroup: (...args: unknown[]) =>
    requestToJoinConfidentialGroupMock(...args),
}))
vi.mock('@/components/ui/Modal', () => ({
  Modal: ({ children, isOpen }: { children: ReactNode; isOpen: boolean }) =>
    isOpen ? <div>{children}</div> : null,
}))

import { EnrollPatronModal } from '../EnrollPatronModal'

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

const confidentialGroup = {
  id: 2,
  name: 'Teen Parents',
  group_type: 'teen_parents' as const,
  max_members: 8,
  is_active: true,
  topics: [],
  confidential: true,
  confidential_approval_message: 'Staff will reply soon',
  estimated_response_window_hours: 48,
  created_at: '2026-01-01',
}

const nonConfidentialGroup = {
  id: 3,
  name: 'Tuesday Crew',
  group_type: 'general' as const,
  max_members: 8,
  current_members: 2,
  is_active: true,
  topics: [],
  confidential: false,
  created_at: '2026-01-01',
}

const samplePatron = {
  id: 77,
  first_name: 'Pat',
  last_name: 'Roney',
  email: 'pat@example.com',
  library_card_number: 'L0077',
}

beforeEach(() => {
  vi.clearAllMocks()
  searchPatronsSuggestionsMock.mockResolvedValue([samplePatron])
})

afterEach(() => {
  vi.useRealTimers()
})

describe('EnrollPatronModal confidential variant', () => {
  it('mounts the confidential section with the approval message', () => {
    render(
      wrap(
        <EnrollPatronModal
          group={confidentialGroup}
          isOpen={true}
          onClose={() => undefined}
        />,
      ),
    )
    const section = screen.getByTestId('enroll-confidential-section')
    expect(section.textContent || '').toContain('Staff will reply soon')
  })

  it('defaults consent_to_share_contact checkbox to OFF', () => {
    render(
      wrap(
        <EnrollPatronModal
          group={confidentialGroup}
          isOpen={true}
          onClose={() => undefined}
        />,
      ),
    )
    const toggle = screen.getByTestId('enroll-consent-share-toggle') as HTMLInputElement
    expect(toggle.checked).toBe(false)
  })

  // Routing guarantees: the modal must hit the correct API endpoint based on
  // the group's confidential flag. Bypassing the approval queue on a
  // confidential group would defeat the entire confidentiality contract.
  it('routes submit through requestToJoinConfidentialGroup for confidential groups', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    requestToJoinConfidentialGroupMock.mockResolvedValue({
      status: 'pending_approval',
      estimated_response_window_hours: 48,
    })

    render(
      wrap(
        <EnrollPatronModal
          group={confidentialGroup}
          isOpen={true}
          onClose={() => undefined}
        />,
      ),
    )

    const input = screen.getByTestId('enroll-patron-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'pa' } })

    // Debounce is 250ms; advance fake timers + flush awaited search.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(260)
    })

    const result = await screen.findByTestId('enroll-patron-result')
    fireEvent.click(result)

    const submit = screen.getByTestId('enroll-submit') as HTMLButtonElement
    fireEvent.click(submit)

    await waitFor(() => {
      expect(requestToJoinConfidentialGroupMock).toHaveBeenCalledTimes(1)
    })
    expect(requestToJoinConfidentialGroupMock).toHaveBeenCalledWith(
      confidentialGroup.id,
      expect.objectContaining({
        patron_id: samplePatron.id,
        consent_to_share_contact: false,
      }),
    )
    expect(enrollPatronInGroupMock).not.toHaveBeenCalled()
  })

  it('routes submit through enrollPatronInGroup for non-confidential groups', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    enrollPatronInGroupMock.mockResolvedValue({
      id: 1,
      group_id: nonConfidentialGroup.id,
      patron_id: samplePatron.id,
      status: 'active',
      joined_date: '2026-05-20',
      consent_note_recorded: false,
      capacity_overridden: false,
    })

    render(
      wrap(
        <EnrollPatronModal
          group={nonConfidentialGroup}
          isOpen={true}
          onClose={() => undefined}
        />,
      ),
    )

    const input = screen.getByTestId('enroll-patron-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'pa' } })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(260)
    })

    const result = await screen.findByTestId('enroll-patron-result')
    fireEvent.click(result)

    const submit = screen.getByTestId('enroll-submit') as HTMLButtonElement
    fireEvent.click(submit)

    await waitFor(() => {
      expect(enrollPatronInGroupMock).toHaveBeenCalledTimes(1)
    })
    expect(enrollPatronInGroupMock).toHaveBeenCalledWith(
      nonConfidentialGroup.id,
      expect.objectContaining({
        patron_id: samplePatron.id,
      }),
    )
    expect(requestToJoinConfidentialGroupMock).not.toHaveBeenCalled()
  })
})
