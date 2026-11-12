/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

import ConnectionGroupsApprovalsPage from '../ConnectionGroupsApprovalsPage'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))
vi.mock('@/components/ui/Modal', () => ({
  Modal: ({ children, isOpen }: { children: ReactNode; isOpen: boolean }) =>
    isOpen ? <div>{children}</div> : null,
}))

const { listMock, queueMock, decideMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  queueMock: vi.fn(),
  decideMock: vi.fn(),
}))

vi.mock('@/api/parent-onboarding-api', () => ({
  listConnectionGroups: listMock,
  getApprovalQueue: queueMock,
  decideApprovalRequest: decideMock,
}))

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

beforeEach(() => {
  listMock.mockReset()
  queueMock.mockReset()
  decideMock.mockReset()
})

describe('ConnectionGroupsApprovalsPage', () => {
  it('hides contact info when patron did not consent', async () => {
    listMock.mockResolvedValue({
      groups: [{ id: 1, confidential: true, name: 'Confidential 1', group_type: 'teen_parents', max_members: 8, is_active: true, created_at: '2026-01-01' }],
    })
    queueMock.mockResolvedValue({
      pending: [
        {
          id: 11,
          group_id: 1,
          group_name: 'Confidential 1',
          patron_id: 100,
          patron_name: 'Patron A',
          patron_contact_visible: false,
          request_message: 'please',
          requested_at: '2026-05-01T00:00:00Z',
          days_pending: 3,
        },
      ],
      approval_decision_log: [],
    })
    render(wrap(<ConnectionGroupsApprovalsPage />))
    await waitFor(() => screen.getByTestId('conngroups-approval-entry'))
    expect(screen.getByTestId('conngroups-approval-contact-hidden')).not.toBeNull()
    expect(screen.queryByTestId('conngroups-approval-contact')).toBeNull()
  })

  it('renders empty state when no pending requests', async () => {
    listMock.mockResolvedValue({
      groups: [{ id: 1, confidential: true, name: 'Conf', group_type: 'teen_parents', max_members: 8, is_active: true, created_at: '2026-01-01' }],
    })
    queueMock.mockResolvedValue({ pending: [], approval_decision_log: [] })
    render(wrap(<ConnectionGroupsApprovalsPage />))
    await waitFor(() => screen.getByTestId('conngroups-approvals-empty'))
    expect(screen.getByTestId('conngroups-approvals-empty')).not.toBeNull()
  })
})
