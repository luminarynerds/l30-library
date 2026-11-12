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
import { axe } from 'jest-axe'

// Keep the page light: stub the shell and the volunteer API layer so the
// tabs render synchronously against fixed, empty-state data.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Every tab unconditionally mounts a ConfirmDialog (visibility is gated by
// isOpen internally), and ConfirmDialog reads useUnifiedAccessibility --
// stub it out rather than wire up that provider for a dialog that never
// opens in this test.
vi.mock('@/components/ConfirmDialog', () => ({
  default: () => null,
}))

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
    listPendingHourLogs: vi.fn().mockResolvedValue({ hour_logs: [], total: 0, page: 1, limit: 50 }),
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

describe('StaffVolunteerManagementPage tablist', () => {
  it('renders a tablist with four tabs', () => {
    renderPage()
    const tablist = screen.getByRole('tablist')
    expect(tablist).toBeInTheDocument()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(4)
  })

  it('marks the Applications tab selected by default with an associated tabpanel', () => {
    renderPage()
    const applicationsTab = screen.getByRole('tab', { name: /applications/i })
    expect(applicationsTab).toHaveAttribute('aria-selected', 'true')
    expect(applicationsTab).toHaveAttribute('tabindex', '0')
    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', applicationsTab.id)
  })

  it('ArrowRight moves selection and focus to the next tab', async () => {
    const user = userEvent.setup()
    renderPage()
    const applicationsTab = screen.getByRole('tab', { name: /applications/i })
    applicationsTab.focus()
    await user.keyboard('{ArrowRight}')
    const rosterTab = screen.getByRole('tab', { name: /active volunteers/i })
    await waitFor(() => {
      expect(rosterTab).toHaveAttribute('aria-selected', 'true')
      expect(rosterTab).toHaveFocus()
    })
  })

  it('roving tabindex: only the active tab is in the tab order', async () => {
    const user = userEvent.setup()
    renderPage()
    const applicationsTab = screen.getByRole('tab', { name: /applications/i })
    const rosterTab = screen.getByRole('tab', { name: /active volunteers/i })
    expect(applicationsTab).toHaveAttribute('tabindex', '0')
    expect(rosterTab).toHaveAttribute('tabindex', '-1')
    applicationsTab.focus()
    await user.keyboard('{End}')
    const hourLogsTab = screen.getByRole('tab', { name: /hour logs/i })
    await waitFor(() => expect(hourLogsTab).toHaveAttribute('tabindex', '0'))
  })

  it('has no axe violations', async () => {
    const { container } = renderPage()
    await waitFor(() => screen.getByText('No pending applications'))
    expect(await axe(container)).toHaveNoViolations()
  })

  it('activates each tab and renders its panel', async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByText('No pending applications'))

    await user.click(screen.getByRole('tab', { name: /active volunteers/i }))
    await waitFor(() => screen.getByText('No volunteers yet'))

    await user.click(screen.getByRole('tab', { name: /shifts/i }))
    await waitFor(() => screen.getByText('No shifts yet'))

    await user.click(screen.getByRole('tab', { name: /hour logs/i }))
    await waitFor(() => screen.getByText('No hours awaiting verification'))
  })
})
