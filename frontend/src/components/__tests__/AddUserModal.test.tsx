/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AddUserModal from '../AddUserModal'

// vi.mock factory runs at hoist time, before module-scope vars are initialized.
// Use vi.hoisted so the mocks are available to both the factory and the tests.
const mocks = vi.hoisted(() => ({
  createUser: vi.fn(),
  setTeacherCard: vi.fn(),
  listSchoolPartnersForTeacherCard: vi.fn(),
}))

// The SUT imports via '../api/staff-api'; the test path is '../../api/staff-api'.
// Vite/Vitest normalize relative specifiers to absolute, but we mock both
// the relative + alias specifiers to be safe across paths the module graph
// may register the barrel under.
vi.mock('../../api/staff-api', () => ({
  createUser: mocks.createUser,
  setTeacherCard: mocks.setTeacherCard,
  listSchoolPartnersForTeacherCard: mocks.listSchoolPartnersForTeacherCard,
}))
vi.mock('@/api/staff-api', () => ({
  createUser: mocks.createUser,
  setTeacherCard: mocks.setTeacherCard,
  listSchoolPartnersForTeacherCard: mocks.listSchoolPartnersForTeacherCard,
}))

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'tok' }),
}))

// Modal is rendered conditionally on isOpen; mock to render children directly
// to keep the test focused on form behavior.
vi.mock('../ui/Modal', () => ({
  Modal: ({ children, isOpen }: { children: React.ReactNode; isOpen: boolean }) =>
    isOpen ? <div role="dialog">{children}</div> : null,
}))

vi.mock('../../utils/toastNotifications', () => ({
  notifySuccess: vi.fn(),
  TOAST_MESSAGES: { user: { createSuccess: 'ok' } },
}))

vi.mock('@/i18n', () => ({
  t: (k: string) => k,
}))

describe('AddUserModal teacher card flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.createUser.mockResolvedValue({ id: 99, role: 'patron' })
    mocks.setTeacherCard.mockResolvedValue({ id: 99, role: 'teacher', school_id: 1 })
    mocks.listSchoolPartnersForTeacherCard.mockResolvedValue([
      { id: 1, name: 'Grant Elementary', partner_type: 'school' },
      { id: 2, name: 'Hillside High', partner_type: 'school' },
    ])
  })

  it('does not render the school picker for the default patron role', () => {
    render(<AddUserModal isOpen onClose={() => {}} onSuccess={() => {}} />)
    expect(screen.queryByLabelText(/^School/i)).not.toBeInTheDocument()
  })

  it('loads schools and shows the picker when teacher role is selected', async () => {
    const user = userEvent.setup()
    render(<AddUserModal isOpen onClose={() => {}} onSuccess={() => {}} />)

    await user.selectOptions(screen.getByLabelText(/^Role/i), 'teacher')

    await waitFor(() =>
      expect(mocks.listSchoolPartnersForTeacherCard).toHaveBeenCalledWith('tok')
    )
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Grant Elementary' })).toBeInTheDocument()
    )
  })

  it('creates the user as patron then PATCHes teacher-card when teacher + school selected', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(<AddUserModal isOpen onClose={() => {}} onSuccess={onSuccess} />)

    await user.type(screen.getByLabelText(/^Email/i), 'new-teacher@example.com')
    await user.type(screen.getByLabelText(/^Password/i), 'TestPass123!')
    await user.selectOptions(screen.getByLabelText(/^Role/i), 'teacher')
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Grant Elementary' })).toBeInTheDocument()
    )
    await user.selectOptions(screen.getByLabelText(/^School/i), '1')
    await user.click(screen.getByRole('button', { name: /Create User/i }))

    await waitFor(() => expect(mocks.createUser).toHaveBeenCalledTimes(1))
    // We downgrade role to patron at the create step; teacher promotion happens via teacher-card PATCH
    expect(mocks.createUser.mock.calls[0]![1]).toMatchObject({
      email: 'new-teacher@example.com',
      role: 'patron',
    })
    expect(mocks.setTeacherCard).toHaveBeenCalledWith('tok', 99, 1)
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
  })

  it('does not create the user when teacher is selected but no school is chosen', async () => {
    const user = userEvent.setup()
    render(<AddUserModal isOpen onClose={() => {}} onSuccess={() => {}} />)

    await user.type(screen.getByLabelText(/^Email/i), 'new-teacher@example.com')
    await user.type(screen.getByLabelText(/^Password/i), 'TestPass123!')
    await user.selectOptions(screen.getByLabelText(/^Role/i), 'teacher')
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Grant Elementary' })).toBeInTheDocument()
    )
    await user.click(screen.getByRole('button', { name: /Create User/i }))

    expect(mocks.createUser).not.toHaveBeenCalled()
    expect(mocks.setTeacherCard).not.toHaveBeenCalled()
  })
})
