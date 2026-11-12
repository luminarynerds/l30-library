/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Keep the page light: stub the shell and the volunteer API layer, same
// pattern as StaffVolunteerManagementPage.tablist.test.tsx.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ConfirmDialog', () => ({
  default: () => null,
}))

const listPendingHourLogs = vi.fn((_status: string, opts: { page: number }) => {
  if (opts.page === 2) {
    // Simulates the real trigger: the last item on page 2 was
    // verified/rejected out from under the view, so the page-2 query now
    // comes back empty even though the queue as a whole is not.
    return Promise.resolve({ hour_logs: [], total: 51, page: 2, limit: 50 })
  }
  return Promise.resolve({
    hour_logs: [
      {
        id: 1,
        volunteer_id: 5,
        volunteer_name: 'Jamie Volunteer',
        log_date: '2026-07-01',
        activity_type: 'shelving',
        description: 'Shelved returns',
        hours: 2,
        status: 'submitted',
      },
    ],
    total: 51,
    page: 1,
    limit: 50,
  })
})

vi.mock('@/api/domains/admin/volunteer-api', () => ({
  volunteerApi: {
    getVolunteerProgramOverview: vi.fn().mockResolvedValue({
      active_volunteers: 0,
      pending_applications: 0,
      total_hours_this_month: 0,
    }),
    listApplications: vi.fn().mockResolvedValue({ applications: [] }),
    getRoster: vi.fn().mockResolvedValue({ volunteers: [] }),
    listShiftsStaff: vi.fn().mockResolvedValue({ shifts: [], total: 0, page: 1, limit: 50 }),
    listPendingHourLogs: (status: string, opts: { page: number }) => listPendingHourLogs(status, opts),
  },
  ROLE_CATEGORY_LABELS: {},
  HOUR_LOG_STATUS_LABELS: {},
}))

import StaffVolunteerManagementPage from '../StaffVolunteerManagementPage'

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/staff/volunteers']}>
        <StaffVolunteerManagementPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('StaffVolunteerManagementPage Hour Logs pagination clamp', () => {
  it('steps back to page 1 when paging to an emptied-out page 2', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: /hour logs/i }))
    await waitFor(() => screen.getByText('Jamie Volunteer'))
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /next page/i }))

    // Page 2 comes back empty; the clamp effect should step back to page 1
    // and the page-1 row should reappear rather than stranding staff on the
    // "no hours pending" empty state.
    await waitFor(() => screen.getByText('Jamie Volunteer'))
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()

    const pagesRequested = listPendingHourLogs.mock.calls.map(([, opts]) => opts.page)
    expect(pagesRequested).toContain(2)
    // Clamped back to 1 after the page-2 fetch resolved empty.
    expect(pagesRequested.filter((p) => p === 1).length).toBeGreaterThan(1)
  })
})
