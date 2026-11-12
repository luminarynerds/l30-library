/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'tok', user: { id: 1, role: 'admin' } }),
}))

const listStaff = vi.fn()
vi.mock('@/api/staff-api/staff-management', () => ({
  listStaff: (...a: unknown[]) => listStaff(...a),
}))

const adminListEntries = vi.fn()
const adminUpdateEntry = vi.fn()
const adminCreateEntry = vi.fn()
vi.mock('@/api/domains/staff/staff-presence-api', () => ({
  adminListEntries: (...a: unknown[]) => adminListEntries(...a),
  adminUpdateEntry: (...a: unknown[]) => adminUpdateEntry(...a),
  adminCreateEntry: (...a: unknown[]) => adminCreateEntry(...a),
  adminDeleteEntry: vi.fn(),
}))

import StaffTimesheetEditorPage from './StaffTimesheetEditorPage'

const STAFF = { id: 5, email: 'a@b.c', first_name: 'Ada', last_name: 'Lovelace', role: 'staff', is_active: true }
const ENTRY = { id: 99, entry_type: 'clock_in', recorded_at: '2026-05-01T09:00:00Z', notes: null }
const CLOCK_OUT = { id: 100, entry_type: 'clock_out', recorded_at: '2026-05-01T17:00:00Z', notes: null }

describe('StaffTimesheetEditorPage unsaved-changes guard', () => {
  let addSpy: ReturnType<typeof vi.spyOn>
  let removeSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    listStaff.mockResolvedValue({ staff: [STAFF], total: 1, page: 1, per_page: 100 })
    adminListEntries.mockResolvedValue([ENTRY])
    addSpy = vi.spyOn(window, 'addEventListener')
    removeSpy = vi.spyOn(window, 'removeEventListener')
  })
  afterEach(() => {
    addSpy.mockRestore()
    removeSpy.mockRestore()
  })

  it('registers a beforeunload guard only after a row becomes dirty', async () => {
    render(<StaffTimesheetEditorPage />)
    // pick the staff member
    const staffSelect = await screen.findByRole('combobox', { name: /Staff member/i })
    fireEvent.change(staffSelect, { target: { value: '5' } })
    // entry row datetime input appears
    const inputs = await screen.findAllByDisplayValue(/2026-05-01T/)
    expect(addSpy).not.toHaveBeenCalledWith('beforeunload', expect.any(Function))

    // edit the row -> dirty
    const firstInput = inputs[0]!
    fireEvent.change(firstInput, { target: { value: '2026-05-01T10:30' } })
    await waitFor(() =>
      expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function)),
    )
  })
})

describe('StaffTimesheetEditorPage validation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listStaff.mockResolvedValue({ staff: [STAFF], total: 1, page: 1, per_page: 100 })
  })

  const setupDay = async (entries: unknown[]) => {
    adminListEntries.mockResolvedValue(entries)
    render(<StaffTimesheetEditorPage />)
    const staffSelect = await screen.findByRole('combobox', { name: /Staff member/i })
    fireEvent.change(staffSelect, { target: { value: '5' } })
    const dateInput = screen.getByLabelText(/Shift date/i)
    fireEvent.change(dateInput, { target: { value: '2026-05-01' } })
    await screen.findAllByDisplayValue(/2026-05-01T/)
  }

  it('rejects a clock-out earlier than the clock-in with an inline accessible error', async () => {
    await setupDay([ENTRY, CLOCK_OUT])
    const inputs = screen.getAllByDisplayValue(/2026-05-01T/)
    const clockOutInput = inputs[1]!
    fireEvent.change(clockOutInput, { target: { value: '2026-05-01T01:00' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[1]!)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/after clock-in/i)
    expect(adminUpdateEntry).not.toHaveBeenCalled()
    expect(clockOutInput).toHaveAttribute('aria-describedby', alert.id)
  })

  it('rejects a future timestamp on the add-entry form with an inline accessible error', async () => {
    await setupDay([ENTRY])
    const recordedAt = screen.getByLabelText(/Recorded at/i)
    fireEvent.change(recordedAt, { target: { value: '2099-01-09T10:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/future/i)
    expect(adminCreateEntry).not.toHaveBeenCalled()
    expect(recordedAt).toHaveAttribute('aria-describedby', alert.id)
  })

  it('rejects a timestamp on a different day than the selected shift date', async () => {
    await setupDay([ENTRY])
    const recordedAt = screen.getByLabelText(/Recorded at/i)
    fireEvent.change(recordedAt, { target: { value: '2026-05-02T10:00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/shift date/i)
    expect(adminCreateEntry).not.toHaveBeenCalled()
  })

  it('saves a coherent edit', async () => {
    await setupDay([ENTRY, CLOCK_OUT])
    adminUpdateEntry.mockResolvedValue({
      ...CLOCK_OUT,
      recorded_at: new Date('2026-05-01T18:00').toISOString(),
    })
    const inputs = screen.getAllByDisplayValue(/2026-05-01T/)
    fireEvent.change(inputs[1]!, { target: { value: '2026-05-01T18:00' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save' })[1]!)
    await waitFor(() => expect(adminUpdateEntry).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
