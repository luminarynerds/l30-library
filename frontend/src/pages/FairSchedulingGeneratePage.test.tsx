/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'admin' }, token: 'tok' }),
}))

const getGenerations = vi.fn()
vi.mock('../api/fair-scheduling-api', () => ({
  fairSchedulingApi: {
    getGenerations: (...a: unknown[]) => getGenerations(...a),
  },
}))

vi.mock('../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/hooks/useBranchOptions', () => ({
  useBranchOptions: () => ({
    branches: [
      { id: 1, name: 'Main Library' },
      { id: 2, name: 'Downtown Branch' },
    ],
    loading: false,
    error: null,
  }),
}))

import FairSchedulingGeneratePage from './FairSchedulingGeneratePage'

const baseGen = {
  id: 1, branch_id: 1, period_start: '2026-05-01', period_end: '2026-05-07',
  status: 'optimal', objective_value: 1, solve_time_seconds: 1.2,
  total_shifts_assigned: 10, total_violations: 0, fairness_score: 0.9,
  constraint_summary: null, created_at: '2026-05-01T00:00:00Z',
}

describe('FairSchedulingGeneratePage published status label', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows visible "Published" text for a published generation', async () => {
    getGenerations.mockResolvedValue([{ ...baseGen, is_published: true }])
    render(<FairSchedulingGeneratePage />)
    // Header cell + the status cell both read "Published"; the status cell is the new label.
    const matches = await screen.findAllByText(/^Published$/)
    expect(matches.length).toBeGreaterThanOrEqual(2)
    expect(matches.some(el => el.tagName === 'SPAN')).toBe(true)
  })

  it('exposes an sr-only "Not published" label for an unpublished generation', async () => {
    getGenerations.mockResolvedValue([{ ...baseGen, id: 2, is_published: false }])
    render(<FairSchedulingGeneratePage />)
    expect(await screen.findByText('Not published')).toBeInTheDocument()
  })

  it('offers a name-based branch picker instead of a numeric ID input', async () => {
    getGenerations.mockResolvedValue([])
    render(<FairSchedulingGeneratePage />)
    const select = await screen.findByLabelText('Branch')
    expect(select.tagName).toBe('SELECT')
    expect(screen.getByRole('option', { name: 'Main Library' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Downtown Branch' })).toBeInTheDocument()
  })
})
