/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const getTeamFatigue = vi.fn()
const getStaffFatigue = vi.fn()
const getStaffFatigueHistory = vi.fn()

vi.mock('../api/fair-scheduling-api', () => ({
  fairSchedulingApi: {
    getTeamFatigue: (...a: unknown[]) => getTeamFatigue(...a),
    getStaffFatigue: (...a: unknown[]) => getStaffFatigue(...a),
    getStaffFatigueHistory: (...a: unknown[]) => getStaffFatigueHistory(...a),
  },
}))

vi.mock('../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => <div />, XAxis: () => <div />, YAxis: () => <div />,
  CartesianGrid: () => <div />, Tooltip: () => <div />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/hooks/useBranchOptions', () => ({
  useBranchOptions: () => ({
    branches: [{ id: 1, name: 'Main Library' }, { id: 2, name: 'Downtown Branch' }],
    loading: false,
    error: null,
  }),
}))

import FairSchedulingFatiguePage from './FairSchedulingFatiguePage'

const REC = {
  id: 1, staff_id: 7, record_date: '2026-05-01', fatigue_level: 'high',
  fatigue_score: 80, consecutive_days_worked: 5, hours_last_7_days: 40,
  hours_last_14_days: 80, closing_shifts_last_7_days: 2, short_turnarounds_last_14_days: 1,
  overtime_hours_last_30_days: 0, days_since_last_day_off: 3, weekend_shifts_last_30_days: 2,
  fatigue_trend: null, alert_triggered: false, alert_message: null, calculated_at: '2026-05-01T00:00:00Z',
}

describe('FairSchedulingFatiguePage keyboard access', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getTeamFatigue.mockResolvedValue([REC])
    getStaffFatigue.mockResolvedValue(REC)
    getStaffFatigueHistory.mockResolvedValue([REC])
  })

  it('exposes the staff row as a focusable button with an accessible name', async () => {
    render(<FairSchedulingFatiguePage />)
    fireEvent.click(screen.getByRole('button', { name: 'Load' }))
    const staffBtn = await screen.findByRole('button', { name: 'View fatigue details for staff #7' })
    expect(staffBtn.tagName).toBe('BUTTON')
  })

  it('loads detail when the staff button is activated', async () => {
    render(<FairSchedulingFatiguePage />)
    fireEvent.click(screen.getByRole('button', { name: 'Load' }))
    const staffBtn = await screen.findByRole('button', { name: 'View fatigue details for staff #7' })
    fireEvent.click(staffBtn)
    await waitFor(() => expect(getStaffFatigue).toHaveBeenCalledWith(7))
    expect(staffBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('offers a name-based branch picker', async () => {
    render(<FairSchedulingFatiguePage />)
    const branchSelect = await screen.findByLabelText('Branch')
    expect(branchSelect.tagName).toBe('SELECT')
    expect(screen.getByRole('option', { name: 'Main Library' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Downtown Branch' })).toBeInTheDocument()
  })
})
