import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { render } from '../../../../__tests__/utils/test-utils'

const mocks = vi.hoisted(() => ({
  getMyShifts: vi.fn(),
}))

vi.mock('@/api/fair-scheduling-api', () => ({
  fairSchedulingApi: { getMyShifts: mocks.getMyShifts },
}))

import MyShiftsTile from '../MyShiftsTile'

const renderTile = () =>
  render(
    <MemoryRouter>
      <MyShiftsTile />
    </MemoryRouter>
  )

describe('MyShiftsTile', () => {
  beforeEach(() => {
    mocks.getMyShifts.mockReset()
  })

  it('shows the empty state when there are no upcoming shifts', async () => {
    mocks.getMyShifts.mockResolvedValue({
      shifts: [],
      range_start: '2026-05-07',
      range_end: '2026-05-21',
    })

    renderTile()

    await waitFor(() => {
      expect(screen.getByText('No upcoming shifts')).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: /view full schedule/i })).toHaveAttribute(
      'href',
      '/staff/fair-scheduling',
    )
  })

  it('renders shifts with swap and call-out deep-links', async () => {
    // Use a far-future date so the "starts in" / "On now" pills don't appear
    // and our assertions stay deterministic.
    const futureDate = '2099-12-15'
    mocks.getMyShifts.mockResolvedValue({
      shifts: [
        {
          shift_id: 42,
          branch_id: 7,
          shift_date: futureDate,
          shift_type: 'opening',
          status: 'assigned',
          scheduled_start: '09:00:00',
          scheduled_end: '17:00:00',
          scheduled_hours: 8,
          is_holiday: false,
          is_weekend: false,
          has_open_swap: true,
          has_open_callout: false,
        },
      ],
      range_start: '2099-12-15',
      range_end: '2099-12-29',
    })

    renderTile()

    await waitFor(() => {
      expect(screen.getByText(/9:00 AM/)).toBeInTheDocument()
    })
    expect(screen.getByText(/5:00 PM/)).toBeInTheDocument()
    expect(screen.getByText('opening')).toBeInTheDocument()
    expect(screen.getByText(/open swap/i)).toBeInTheDocument()

    const swapLink = screen.getByRole('link', { name: /swap this shift/i })
    expect(swapLink).toHaveAttribute('href', '/staff/shift-swap?shift_id=42')

    const calloutLink = screen.getByRole('link', { name: /call out from this shift/i })
    expect(calloutLink).toHaveAttribute(
      'href',
      '/staff/fair-scheduling/call-outs?shift_id=42',
    )
  })

  it('shows an error fallback when the request fails', async () => {
    mocks.getMyShifts.mockRejectedValue(new Error('boom'))

    renderTile()

    await waitFor(() => {
      expect(screen.getByText(/couldn't load your schedule/i)).toBeInTheDocument()
    })
  })
})
