/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'tok', user: { id: 1, role: 'admin' } }),
}))

const listStaff = vi.fn()
vi.mock('@/api/staff-api/staff-management', () => ({
  listStaff: (...a: unknown[]) => listStaff(...a),
}))

vi.mock('@/hooks/useBranchOptions', () => ({
  useBranchOptions: () => ({
    branches: [{ id: 1, name: 'Main Library' }, { id: 2, name: 'Downtown Branch' }],
    loading: false,
    error: null,
  }),
}))

vi.mock('../api/fair-scheduling-api', () => ({
  fairSchedulingApi: {
    getLearnedPreferences: vi.fn().mockResolvedValue([]),
    learnPreferences: vi.fn().mockResolvedValue({}),
    confirmPreference: vi.fn().mockResolvedValue({}),
  },
}))

vi.mock('../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import FairSchedulingPreferencesPage from './FairSchedulingPreferencesPage'

describe('FairSchedulingPreferencesPage name-based pickers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listStaff.mockResolvedValue({
      staff: [
        { id: 5, first_name: 'Ada', last_name: 'Lovelace', email: 'ada@x.org', role: 'staff', is_active: true },
        { id: 6, first_name: 'Grace', last_name: 'Hopper', email: 'grace@x.org', role: 'staff', is_active: true },
      ],
      total: 2, page: 1, per_page: 100,
    })
  })

  it('renders a name-based staff dropdown and a branch dropdown', async () => {
    render(<FairSchedulingPreferencesPage />)
    const staffSelect = await screen.findByLabelText('Staff member')
    expect(staffSelect.tagName).toBe('SELECT')
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ada Lovelace (ada@x.org)' })).toBeInTheDocument(),
    )
    expect(screen.getByRole('option', { name: 'Grace Hopper (grace@x.org)' })).toBeInTheDocument()

    const branchSelect = screen.getByLabelText('Branch ID (optional)')
    expect(branchSelect.tagName).toBe('SELECT')
    expect(screen.getByRole('option', { name: 'All branches' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Main Library' })).toBeInTheDocument()
  })
})
