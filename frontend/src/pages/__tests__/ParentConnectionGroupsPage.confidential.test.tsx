/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Confidentiality + approval-queue UI tests for ParentConnectionGroupsPage
 * card variant.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

import ParentConnectionGroupsPage from '../ParentConnectionGroupsPage'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))
vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))
vi.mock('@/components/staff/parent-onboarding/EnrollPatronModal', () => ({
  EnrollPatronModal: () => null,
}))
vi.mock('@/components/staff/parent-onboarding/GroupMembersDrawer', () => ({
  GroupMembersDrawer: () => null,
}))

const { listMock } = vi.hoisted(() => ({ listMock: vi.fn() }))
vi.mock('@/api/parent-onboarding-api', () => ({
  listConnectionGroups: listMock,
  enrollPatronInGroup: vi.fn(),
  listConnectionGroupMembers: vi.fn(),
  removeConnectionGroupMember: vi.fn(),
  requestToJoinConfidentialGroup: vi.fn(),
}))

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

const defaultGroup = {
  id: 1,
  name: 'Default Crew',
  description: 'Open',
  group_type: 'first_time_parents',
  meeting_schedule: 'Weekly Tue',
  current_members: 4,
  max_members: 12,
  facilitator_name: 'Alex',
  facilitator_id: 7,
  is_active: true,
  topics: [],
  confidential: false,
}

const confidentialGroup = {
  id: 2,
  name: 'Teen Parents',
  description: 'Should not show',
  // Spec: confidential responses omit facilitator_id / facilitator_name / current_members.
  group_type: 'teen_parents',
  meeting_schedule: 'Weekly Sat',
  max_members: 8,
  is_active: true,
  topics: [],
  confidential: true,
  confidential_card_description: 'Welcome and safe',
  estimated_response_window_hours: 48,
}

beforeEach(() => {
  listMock.mockReset()
  listMock.mockResolvedValue({ groups: [defaultGroup, confidentialGroup] })
})

describe('ParentConnectionGroupsPage confidential variant', () => {
  it('omits member count and facilitator from the confidential card DOM', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const card = await screen.findByTestId('conngroups-card-confidential')
    expect(card.textContent || '').not.toMatch(/\/8/)
    // facilitator label not rendered
    expect(card.textContent || '').not.toMatch(/Facilitator/i)
    // "Limited capacity" label present
    expect(card.querySelector('[data-testid="conngroups-limited-capacity"]')).not.toBeNull()
  })

  it('renders the lock icon with the privacy aria-label', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const card = await screen.findByTestId('conngroups-card-confidential')
    const lockLabel = card.querySelector('[aria-label="connectionGroups.confidential.cardLabel"]')
    expect(lockLabel).not.toBeNull()
  })

  it('uses the Request-to-join label on the confidential action button', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const card = await screen.findByTestId('conngroups-card-confidential')
    const btns = card.querySelectorAll('[data-testid="conngroups-enroll"]')
    expect(btns.length).toBe(1)
    const first = btns[0] as Element
    expect(first.textContent || '').toContain('connectionGroups.confidential.requestButton')
  })

  it('default cards still show member count + facilitator', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const cards = await screen.findAllByTestId('conngroups-card')
    const def = cards[0] as HTMLElement
    expect(def?.textContent || '').toMatch(/4\/12/)
    expect(def?.textContent || '').toMatch(/Alex/)
  })
})
