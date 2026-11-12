/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import '@testing-library/jest-dom'
import { axe } from 'jest-axe'
import { render, screen, userEvent } from '../__tests__/utils/test-utils'
import LibraryPulse from './LibraryPulse'
import type { DayHours } from '@/api/domains/content/homepage-content-api'

const weekly: DayHours[] = [
  { id: 1, day_of_week: 0, open_time: '13:00', close_time: '17:00', is_closed: false, label: null },
  // label carries the day NAME, not an hours string — the value column must ignore it.
  { id: 2, day_of_week: 1, open_time: '09:00', close_time: '20:00', is_closed: false, label: 'Monday' },
  { id: 3, day_of_week: 2, open_time: '09:00', close_time: '20:00', is_closed: false, label: null },
  { id: 4, day_of_week: 3, open_time: '09:00', close_time: '20:00', is_closed: false, label: null },
  { id: 5, day_of_week: 4, open_time: '09:00', close_time: '20:00', is_closed: false, label: null },
  { id: 6, day_of_week: 5, open_time: '09:00', close_time: '17:00', is_closed: false, label: null },
  { id: 7, day_of_week: 6, open_time: null, close_time: null, is_closed: true, label: null },
]

const mainBranch = {
  address_line1: '402 Creek Road',
  city: 'Little Schitt Creek',
  state: 'OH',
  postal_code: '44092',
  phone: '(555) 123-4567',
  branch_type: 'main',
}

const baseProps = {
  mainBranch,
  todayHoursLabel: null,
  announcements: [],
  upcomingEvent: null,
  weekly,
}

describe('LibraryPulse — Visit Us card', () => {
  it('leads with open status and a warm sub-line when open', () => {
    render(<LibraryPulse {...baseProps} openStatus={{ is_open: true, opens_at: '09:00', closes_at: '20:00' }} />)
    // "Visit Us" is the stable heading; the open/closed word is emphasized text.
    expect(screen.getByRole('heading', { name: /visit us/i })).toBeInTheDocument()
    expect(screen.getByText(/^open now$/i)).toBeInTheDocument()
    expect(screen.getByText(/come on in\. open until 8 PM today/i)).toBeInTheDocument()
  })

  it('names the next open day when closed for the rest of today', () => {
    // Saturday (dow 6) is closed in the fixture, so a Saturday-evening close
    // should point the patron to Sunday's 1 PM opening.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-11T20:00:00'))
    render(<LibraryPulse {...baseProps} openStatus={{ is_open: false, opens_at: '13:00', closes_at: null }} />)
    expect(screen.getByText(/come back sunday at 1 PM/i)).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('falls back to a plain closed line when the schedule is unavailable', () => {
    render(<LibraryPulse {...baseProps} weekly={[]} openStatus={{ is_open: false, opens_at: '09:00', closes_at: null }} />)
    expect(screen.getByText(/come back at 9 AM/i)).toBeInTheDocument()
  })

  it('renders the week as a table with row headers', () => {
    render(<LibraryPulse {...baseProps} openStatus={{ is_open: true, opens_at: '09:00', closes_at: '20:00' }} />)
    expect(screen.getAllByRole('rowheader').length).toBe(7)
    // Saturday is a closed day → shows the closed label, not a time range.
    expect(screen.getByText(/^closed$/i)).toBeInTheDocument()
    // The hours column shows the time range, never the day-name label.
    expect(screen.getAllByText(/9 AM - 8 PM/).length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByRole('cell', { name: /^monday$/i })).not.toBeInTheDocument()
  })

  it('offers directions as an explicit action', () => {
    render(<LibraryPulse {...baseProps} openStatus={{ is_open: true, opens_at: '09:00', closes_at: '20:00' }} />)
    const directions = screen.getByRole('link', { name: /get directions/i })
    expect(directions).toHaveAttribute('href', expect.stringContaining('google.com/maps'))
    expect(directions).toHaveAttribute('target', '_blank')
  })

  it('uses the branch postal code and never sends missing address values to maps', () => {
    render(<LibraryPulse {...baseProps} mainBranch={{ address_line1: '402 Creek Road', zip_code: 'L1R 1R3' }} openStatus={null} />)
    const directions = screen.getByRole('link', { name: /get directions/i })
    expect(decodeURIComponent(directions.getAttribute('href')!)).toContain('402 Creek Road, L1R 1R3')
    expect(directions.getAttribute('href')).not.toMatch(/undefined|null/)
    expect(screen.queryByText(/we.re closed now/i)).not.toBeInTheDocument()
  })

  it('has no axe violations when open', async () => {
    const { container } = render(<LibraryPulse {...baseProps} openStatus={{ is_open: true, opens_at: '09:00', closes_at: '20:00' }} />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('has no axe violations when closed', async () => {
    const { container } = render(<LibraryPulse {...baseProps} openStatus={{ is_open: false, opens_at: '09:00', closes_at: null }} />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('reaches the directions link by keyboard with no trap', async () => {
    const user = userEvent.setup()
    render(<LibraryPulse {...baseProps} openStatus={{ is_open: true, opens_at: '09:00', closes_at: '20:00' }} />)
    await user.tab()
    expect(screen.getByRole('link', { name: /get directions/i })).toHaveFocus()
  })
})
