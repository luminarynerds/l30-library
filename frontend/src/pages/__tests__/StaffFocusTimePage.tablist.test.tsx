/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

// Keep the page light: stub the shell and the data-fetching child dashboards.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock('../../components/staff/FocusTimeScheduler', () => ({
  FocusTimeScheduler: () => <div>Scheduler content</div>,
}))
vi.mock('../../components/staff/FocusTimeApprovalDashboard', () => ({
  FocusTimeApprovalDashboard: () => <div>Approvals content</div>,
}))
vi.mock('../../components/staff/FocusTimeAnalyticsDashboard', () => ({
  FocusTimeAnalyticsDashboard: () => <div>Analytics content</div>,
}))

import { useAuth } from '@/contexts/AuthContext'
import StaffFocusTimePage from '../StaffFocusTimePage'

const setRole = (role: string) => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 1, role } as any,
    token: 't', isLoading: false, isAuthenticated: true,
  } as any)
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/staff/focus-time']}>
      <StaffFocusTimePage />
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.clearAllMocks()
})

describe('StaffFocusTimePage tablist', () => {
  it('renders a tablist with three tabs for managers', () => {
    setRole('admin')
    renderPage()
    const tablist = screen.getByRole('tablist')
    expect(tablist).toBeInTheDocument()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(3)
  })

  it('marks the schedule tab selected by default with an associated tabpanel', () => {
    setRole('admin')
    renderPage()
    const scheduleTab = screen.getByRole('tab', { name: /schedule/i })
    expect(scheduleTab).toHaveAttribute('aria-selected', 'true')
    expect(scheduleTab).toHaveAttribute('tabindex', '0')
    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', scheduleTab.id)
  })

  it('non-managers see only the schedule tab', () => {
    setRole('staff')
    renderPage()
    expect(screen.getAllByRole('tab')).toHaveLength(1)
  })

  it('ArrowRight moves selection and focus to the next tab', async () => {
    const user = userEvent.setup()
    setRole('admin')
    renderPage()
    const scheduleTab = screen.getByRole('tab', { name: /schedule/i })
    scheduleTab.focus()
    await user.keyboard('{ArrowRight}')
    const approvalsTab = screen.getByRole('tab', { name: /approvals/i })
    await waitFor(() => {
      expect(approvalsTab).toHaveAttribute('aria-selected', 'true')
      expect(approvalsTab).toHaveFocus()
    })
  })

  it('roving tabindex: only the active tab is in the tab order', async () => {
    const user = userEvent.setup()
    setRole('admin')
    renderPage()
    const scheduleTab = screen.getByRole('tab', { name: /schedule/i })
    const approvalsTab = screen.getByRole('tab', { name: /approvals/i })
    expect(scheduleTab).toHaveAttribute('tabindex', '0')
    expect(approvalsTab).toHaveAttribute('tabindex', '-1')
    scheduleTab.focus()
    await user.keyboard('{End}')
    const analyticsTab = screen.getByRole('tab', { name: /analytics/i })
    await waitFor(() => expect(analyticsTab).toHaveAttribute('tabindex', '0'))
  })
})
