/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import StaffShelfReadingPage from './StaffShelfReadingPage'
import {
  listSessions,
  getSessionProgress,
  listSessionScans,
  scanItem,
} from '../../api/shelf-reading-api'

vi.mock('../../api/shelf-reading-api', () => ({
  listSessions: vi.fn(),
  getSessionProgress: vi.fn(),
  listSessionScans: vi.fn(),
  scanItem: vi.fn(),
  createSession: vi.fn(),
  completeSession: vi.fn(),
  pauseSession: vi.fn(),
  resumeSession: vi.fn(),
  cancelSession: vi.fn(),
}))

vi.mock('../../api/branch-api', () => ({
  listBranches: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({
    children,
    actions,
  }: {
    children: React.ReactNode
    actions?: React.ReactNode
  }) => (
    <div>
      {actions}
      {children}
    </div>
  ),
}))

const session = {
  id: 1,
  name: 'Fiction A-C',
  status: 'in_progress',
  branch_name: 'Main',
  location: 'Adult Fiction',
  total_items_scanned: 0,
  accuracy_percentage: 0,
  call_number_start: null,
  call_number_end: null,
}

const progress = {
  session_id: 1,
  session_name: 'Fiction A-C',
  status: 'in_progress',
  total_items_scanned: 1,
  items_in_order: 1,
  items_out_of_order: 0,
  items_wrong_shelf: 0,
  accuracy_percentage: 100,
  last_scanned_call_number: null,
  points_earned: 0,
}

describe('StaffShelfReadingPage scan live regions', () => {
  beforeEach(() => {
    ;(listSessions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [session],
      total: 1,
      page: 1,
      per_page: 20,
    })
    ;(getSessionProgress as ReturnType<typeof vi.fn>).mockResolvedValue(progress)
    ;(listSessionScans as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
      session_accuracy: 0,
    })
  })

  async function openSession() {
    render(<StaffShelfReadingPage />)
    fireEvent.click(await screen.findByRole('button', { name: /Fiction A-C/i }))
    // wait for scan view
    await screen.findByRole('button', { name: /^scan$/i })
  }

  it('announces a successful scan in a polite live region', async () => {
    ;(scanItem as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 9,
      barcode: 'B123',
      catalog_title: 'Some Book',
      result: 'in_order',
    })
    await openSession()
    fireEvent.change(screen.getByLabelText(/barcode/i), {
      target: { value: 'B123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    // The scan-success message lives inside a polite live region.
    const msg = await screen.findByText(/Some Book/)
    expect(msg.closest('[aria-live="polite"]')).toBeTruthy()
  })

  it('announces a scan error via role=alert', async () => {
    ;(scanItem as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Barcode not found')
    )
    await openSession()
    fireEvent.change(screen.getByLabelText(/barcode/i), {
      target: { value: 'BAD' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Barcode not found')
    )
  })
})
