/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import ParentConnectionGroupsPage, {
  buildGroupsCsv,
} from '../ParentConnectionGroupsPage'

// L30 vitest setup doesn't preload i18n; mock useTranslation to echo keys so
// we can assert on key paths rather than locale-rendered text. Matches the
// pattern in ParentConnectionGroupsPage.test.tsx (PR #811).
vi.mock('@/i18n', () => ({
  getCurrentLocale: () => 'en-US',
  useTranslation: () => ({ t: (key: string) => key }),
}))

// vi.hoisted so the Sentry mock is available inside the vi.mock factory
// before the page module imports it. sentry-lazy doesn't expose withScope;
// the scrub goes through captureException's second CaptureContext arg.
const { sentryCapture } = vi.hoisted(() => ({
  sentryCapture: vi.fn(),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: sentryCapture,
}))

const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))
vi.mock('react-hot-toast', () => ({
  default: { success: toastSuccess, error: toastError },
}))

// AdminShell is a heavy import (nav, auth wiring). Stub it.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

const { listMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
}))

vi.mock('@/api/parent-onboarding-api', async () => {
  return {
    listConnectionGroups: listMock,
    // Modals are mounted lazily on click; stub everything they import so the
    // page can render without dragging the modal module into vitest.
    enrollPatronInGroup: vi.fn(),
    listConnectionGroupMembers: vi.fn(),
    removeConnectionGroupMember: vi.fn(),
  }
})

// Stub the modal + drawer so we don't need to mount their auth/search deps
// in page-level polish tests. Functional coverage for the modals lives in
// their own __tests__ folders.
vi.mock('@/components/staff/parent-onboarding/EnrollPatronModal', () => ({
  EnrollPatronModal: () => null,
}))
vi.mock('@/components/staff/parent-onboarding/GroupMembersDrawer', () => ({
  GroupMembersDrawer: () => null,
}))

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

const today = new Date()
const yesterday = new Date(today.getTime() - 86400000)
const tomorrow = new Date(today.getTime() + 86400000)
// Serialize in LOCAL date parts, not toISOString (UTC): west of UTC, evening
// runs cross UTC midnight and "yesterday" serializes as today, making the
// stale fixture non-stale — a time-of-day flake.
const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const groupsFixture = [
  {
    id: 1,
    name: 'Tuesday Morning Crew',
    description: 'Coffee + chats',
    group_type: 'first_time_parents',
    meeting_schedule: 'Weekly Tue 10am',
    next_meeting_date: isoDay(tomorrow),
    meeting_location: 'Library Room A',
    current_members: 5,
    max_members: 10,
    topics: ['sleep', 'feeding'],
    facilitator_name: 'Alex',
    is_active: true,
  },
  {
    id: 2,
    name: 'Teen Parents Circle',
    description: '',
    group_type: 'teen_parents',
    meeting_schedule: 'Biweekly Sat 2pm',
    next_meeting_date: isoDay(yesterday), // STALE
    meeting_location: 'Library Room B',
    current_members: 8,
    max_members: 8, // FULL
    topics: ['school', 'childcare', 'jobs', 'housing', 'food'],
    facilitator_name: 'Sam',
    is_active: true,
  },
  {
    id: 3,
    name: 'Single Parents Network',
    description: 'Support and resources',
    group_type: 'single_parents',
    meeting_schedule: 'Monthly',
    next_meeting_date: null,
    meeting_location: '',
    current_members: 3,
    max_members: 12,
    topics: [],
    facilitator_name: '',
    is_active: true,
  },
]

beforeEach(() => {
  listMock.mockReset()
  sentryCapture.mockReset()
  toastSuccess.mockReset()
  toastError.mockReset()

  listMock.mockResolvedValue({ groups: groupsFixture })
})

describe('ParentConnectionGroupsPage polish', () => {
  it('renders KPI strip with correct aggregates from fixture', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    await screen.findByTestId('conngroups-kpi-strip')

    // 3 active groups
    expect(screen.getByTestId('conngroups-kpi-active-groups')).toHaveTextContent(
      '3',
    )
    // 5 + 8 + 3 = 16 members
    expect(screen.getByTestId('conngroups-kpi-active-members')).toHaveTextContent(
      '16',
    )
    // (5+8+3) / (10+8+12) = 16/30 = 53%
    expect(screen.getByTestId('conngroups-kpi-utilization')).toHaveTextContent(
      '53%',
    )
    // 1 full group (id 2: 8/8)
    expect(screen.getByTestId('conngroups-kpi-full-groups')).toHaveTextContent(
      '1',
    )
  })

  it('uses <ul role="list"> with <li> children for grid semantics', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const grid = await screen.findByTestId('conngroups-grid')
    expect(grid.tagName).toBe('UL')
    expect(grid.getAttribute('role')).toBe('list')
    expect(grid.querySelectorAll('li').length).toBe(3)
  })

  it('renders stale next_meeting_date in warning color with SR-only explanation', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const stale = await screen.findByTestId('next-meeting-stale')
    expect(stale.className).toMatch(/text-status-warning-600/)
    expect(stale.textContent).toMatch(
      /parentOnboarding\.connectionGroups\.pageStrings\.pastMeetingSr/,
    )
  })

  it('places Enroll, View members, and CSV export buttons with focus-visible ring classes', async () => {
    render(wrap(<ParentConnectionGroupsPage />))
    const csvBtn = await screen.findByTestId('conngroups-export-csv')
    expect(csvBtn.className).toMatch(/focus-visible:ring-2/)
    expect(csvBtn.className).toMatch(/focus-visible:ring-lsc-rose/)

    const enrollBtns = await screen.findAllByTestId('conngroups-enroll')
    expect(enrollBtns.length).toBeGreaterThan(0)
    enrollBtns.forEach((b) => {
      expect(b.className).toMatch(/focus-visible:ring-2/)
      expect(b.className).toMatch(/focus-visible:ring-lsc-rose/)
    })

    const viewBtns = await screen.findAllByTestId('conngroups-view-members')
    expect(viewBtns.length).toBeGreaterThan(0)
  })
})

describe('buildGroupsCsv', () => {
  it('emits header + one row per group with raw enum type', () => {
    const csv = buildGroupsCsv(groupsFixture as never)
    const lines = csv.trimEnd().split('\n')
    expect(lines[0]).toBe(
      'name,type,schedule,next_meeting,location,current_members,max_members,topics',
    )
    expect(lines.length).toBe(4) // header + 3
    // raw enum string in type column, not a translated label
    expect(lines[1]).toContain('first_time_parents')
    expect(lines[1]).toContain('Tuesday Morning Crew')
    // topics joined with `|`
    expect(lines[1]).toContain('sleep|feeding')
    // long topics list also pipe-joined
    expect(lines[2]).toContain('school|childcare|jobs|housing|food')
  })

  it('quotes cells containing commas and escapes inner quotes', () => {
    const csv = buildGroupsCsv([
      {
        ...groupsFixture[0],
        name: 'Comma, group "alpha"',
      },
    ] as never)
    const line = csv.split('\n')[1]
    expect(line).toContain('"Comma, group ""alpha"""')
  })

  it('omits facilitator_name from output (PII-safe default)', () => {
    const csv = buildGroupsCsv(groupsFixture as never)
    expect(csv).not.toContain('Alex')
    expect(csv).not.toContain('facilitator')
  })
})
