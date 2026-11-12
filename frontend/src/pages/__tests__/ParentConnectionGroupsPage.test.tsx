/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

// L30 vitest setup does not preload i18n; mock useTranslation to echo keys
// so we can assert on key paths instead of translated strings.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// vi.mock spec is resolved relative to THIS test file. Source page lives at
// src/pages/, test at src/pages/__tests__/, AdminShell at src/components/shells/.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

const listMock = vi.fn()
const leaveMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  listConnectionGroups: (...args: unknown[]) => listMock(...args),
  leaveConnectionGroup: (...args: unknown[]) => leaveMock(...args),
}))

import ParentConnectionGroupsPage from '../ParentConnectionGroupsPage'

function withClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

const sampleGroup = {
  id: 1,
  name: 'Test Group',
  description: 'A description',
  group_type: 'first_time_parents' as const,
  max_members: 10,
  current_members: 4,
  is_active: true,
  topics: ['feeding', 'sleep'],
  created_at: '2026-01-01T00:00:00Z',
}

describe('ParentConnectionGroupsPage', () => {
  beforeEach(() => {
    listMock.mockReset()
    leaveMock.mockReset()
    listMock.mockResolvedValue({ groups: [sampleGroup], total: 1 })
  })

  // REGRESSION (not stale-test), 3 tests below: commit f31606839 ("fix
  // (connection-groups): a11y and i18n on ParentConnectionGroupsPage #811")
  // documents adding role=group + aria-label on the filter-pill row,
  // aria-pressed reflecting active filter state, a member-count test hook,
  // and bumping card body copy from text-xs to text-sm for WCAG AA contrast
  // — but the code it actually shipped never added any of that (verified via
  // `git show f31606839:./src/pages/ParentConnectionGroupsPage.tsx` — no
  // role="group", aria-pressed, member-count, or text-sm on the body rows).
  // A later commit (905839227) explicitly calls these "3 pre-existing
  // failures ... out of scope." Left failing per policy; needs a real a11y
  // fix to ParentConnectionGroupsPage.tsx's filter pills + body copy, not a
  // test-side workaround.
  it('renders filter pills inside a role=group region', async () => {
    render(withClient(<ParentConnectionGroupsPage />))
    const region = await screen.findByRole(
      'group',
      { name: 'parentOnboarding.connectionGroups.pageStrings.filterAriaLabel' },
      { timeout: 5000 },
    )
    expect(region).toBeTruthy()
  })

  it('sets aria-pressed=true on the active filter pill and false on inactive ones', async () => {
    render(withClient(<ParentConnectionGroupsPage />))

    // Default: "All" filter is active; first-time-parents pill is not.
    const allButton = await screen.findByRole(
      'button',
      { name: /pageStrings\.allFilter/ },
      { timeout: 5000 },
    )
    expect(allButton.getAttribute('aria-pressed')).toBe('true')

    const firstTimeButton = screen.getByRole('button', {
      name: /types\.first_time_parents/,
    })
    expect(firstTimeButton.getAttribute('aria-pressed')).toBe('false')

    // Click the first-time-parents pill. Changing filterType triggers a refetch
    // that briefly unmounts the cards, so we re-query the button by role after
    // the page settles instead of holding a stale ref.
    fireEvent.click(firstTimeButton)

    await waitFor(
      () => {
        const refreshed = screen.getByRole('button', {
          name: /types\.first_time_parents/,
        })
        expect(refreshed.getAttribute('aria-pressed')).toBe('true')
      },
      { timeout: 5000 },
    )

    const refreshedAll = screen.getByRole('button', {
      name: /pageStrings\.allFilter/,
    })
    expect(refreshedAll.getAttribute('aria-pressed')).toBe('false')
  })

  it('uses the stable namespaced i18n keys for group type labels (no English-as-keys)', async () => {
    render(withClient(<ParentConnectionGroupsPage />))
    // The page passes the namespaced key to t(); the mock echoes keys, so the
    // literal namespaced path should appear in the DOM (filter pill + card badge).
    const matches = await screen.findAllByText(
      'parentOnboarding.connectionGroups.types.first_time_parents',
      undefined,
      { timeout: 5000 },
    )
    expect(matches.length).toBeGreaterThan(0)
  })

  it('renders card body text at text-sm (WCAG AA-friendly), not text-xs', async () => {
    render(withClient(<ParentConnectionGroupsPage />))
    const memberRow = await screen.findByTestId('member-count', undefined, {
      timeout: 5000,
    })
    // The parent space-y wrapper carries the body text size class.
    const bodyContainer = memberRow.parentElement
    expect(bodyContainer?.className).toContain('text-sm')
    expect(bodyContainer?.className).not.toContain('text-xs')
  })
})
