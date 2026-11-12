/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const createReservation = vi.fn().mockResolvedValue({ id: 99 })
const fetchReservations = vi.fn().mockResolvedValue(undefined)
const fetchCurrentSession = vi.fn().mockResolvedValue(undefined)
const fetchStations = vi.fn().mockResolvedValue(undefined)

const stations = [
  { id: 1, name: 'Public PC 1', computer_number: 'PC-01', status: 'available', is_active: true, max_session_minutes: 60 },
  { id: 5, name: 'Kids Computer 1', computer_number: 'KIDS-01', status: 'available', is_active: true, max_session_minutes: 30 },
  { id: 8, name: 'Accessible Workstation', computer_number: 'ADA-01', status: 'maintenance', is_active: true, max_session_minutes: 90 },
]

vi.mock('../features/computers/useComputerSessions', () => ({
  useComputerSessions: () => ({
    stations,
    reservations: [],
    currentSession: null,
    fetchStations,
    fetchReservations,
    fetchCurrentSession,
    createReservation,
    cancelReservation: vi.fn(),
  }),
}))

// Light stubs so the page renders without the children's own data hooks.
vi.mock('../features/computers/StationList', () => ({ StationList: () => <div data-testid="station-list" /> }))
vi.mock('../features/computers/ActiveSession', () => ({ ActiveSession: () => null }))
vi.mock('../features/computers/WaitlistStatus', () => ({ WaitlistStatus: () => null }))
vi.mock('../features/computers/ReservationCard', () => ({ ReservationCard: () => null }))
vi.mock('../features/computers/AvailabilityGrid', () => ({
  AvailabilityGrid: ({ onPick }: { onPick: (id: number, s: string, e: string) => void }) => (
    <button type="button" onClick={() => onPick(1, '2026-06-09T13:00:00Z', '2026-06-09T14:00:00Z')}>
      grid-pick
    </button>
  ),
}))
vi.mock('../features/computers/BookingCalendar', () => ({
  BookingCalendar: ({
    computerId,
    onSlotSelect,
  }: {
    computerId?: number
    onSlotSelect?: (startTime: string, endTime: string) => void
  }) => (
    <div>
      <span data-testid="calendar-computer-id">{computerId ?? 'none'}</span>
      <button type="button" onClick={() => onSlotSelect?.('2026-06-09T13:00:00Z', '2026-06-09T14:00:00Z')}>
        pick-slot
      </button>
    </div>
  ),
}))

vi.mock('react-hot-toast', () => {
  const toast = Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() })
  return { default: toast }
})

import ComputersPage from './ComputersPage'

describe('ComputersPage — Book a Time tab', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('lets a user pick a computer then book a calendar slot (computer_id + slot duration)', async () => {
    render(<ComputersPage />)
    fireEvent.click(screen.getByRole('tab', { name: /book a time/i }))

    // Calendar is not shown until a computer is chosen, so there is nothing to book yet.
    expect(screen.queryByText('pick-slot')).not.toBeInTheDocument()

    const picker = screen.getByLabelText('Computer') as HTMLSelectElement
    fireEvent.change(picker, { target: { value: '1' } })

    // The chosen computer id is threaded into the calendar (fixes the 422 from a missing computer_id).
    expect(screen.getByTestId('calendar-computer-id').textContent).toBe('1')

    fireEvent.click(screen.getByText('pick-slot'))

    await waitFor(() => expect(createReservation).toHaveBeenCalledTimes(1))
    const [computerId, startTime, duration] = createReservation.mock.calls[0]!
    expect(computerId).toBe(1)
    expect(startTime).toBe('2026-06-09T13:00:00.000Z')
    expect(duration).toBe(60)
  })

  it('books the chosen computer when an all-computers grid cell is picked', async () => {
    render(<ComputersPage />)
    fireEvent.click(screen.getByRole('tab', { name: /book a time/i }))
    fireEvent.click(screen.getByText('grid-pick'))
    await waitFor(() => expect(createReservation).toHaveBeenCalledTimes(1))
    const [computerId, , duration] = createReservation.mock.calls[0]!
    expect(computerId).toBe(1)
    expect(duration).toBe(60)
  })

  it('does not render the calendar (so cannot book) until a computer is selected', () => {
    render(<ComputersPage />)
    fireEvent.click(screen.getByRole('tab', { name: /book a time/i }))
    expect(screen.queryByText('pick-slot')).not.toBeInTheDocument()
    expect(createReservation).not.toHaveBeenCalled()
  })

  it('caps the booked duration at the computer max session (60-min slot -> 30 for a 30-max station)', async () => {
    render(<ComputersPage />)
    fireEvent.click(screen.getByRole('tab', { name: /book a time/i }))
    fireEvent.change(screen.getByLabelText('Computer'), { target: { value: '5' } }) // KIDS-01, max 30
    fireEvent.click(screen.getByText('pick-slot'))
    await waitFor(() => expect(createReservation).toHaveBeenCalledTimes(1))
    expect(createReservation.mock.calls[0]![2]).toBe(30)
  })

  it('does not offer maintenance/offline computers in the picker', () => {
    render(<ComputersPage />)
    fireEvent.click(screen.getByRole('tab', { name: /book a time/i }))
    expect(screen.queryByRole('option', { name: /Accessible Workstation/ })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Public PC 1/ })).toBeInTheDocument()
  })
})
