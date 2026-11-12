/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const getGenerations = vi.fn()
const getExplanations = vi.fn()
const getStaffExplanation = vi.fn()

vi.mock('../api/fair-scheduling-api', () => ({
  fairSchedulingApi: {
    getGenerations: (...a: unknown[]) => getGenerations(...a),
    getExplanations: (...a: unknown[]) => getExplanations(...a),
    getStaffExplanation: (...a: unknown[]) => getStaffExplanation(...a),
  },
}))

vi.mock('../components/shells', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import FairSchedulingExplanationsPage from './FairSchedulingExplanationsPage'

const EXPLANATION = {
  id: 1, generation_id: 3, shift_id: 11, staff_id: 7,
  explanation_type: 'preference_honored',
  explanation_text: 'Assigned morning shift',
  contributing_factors: [
    { factor: 'preference_match', weight: 0.3, score: 0.9, detail: 'Preferred morning shifts' },
    { factor: 'fairness_balance', weight: 0.4, score: 0.7, detail: 'Below avg weekend shifts' },
    { factor: 'mystery_metric', weight: 0.1, score: 1.0 },
  ],
  fairness_impact: 0.5,
}

describe('FairSchedulingExplanationsPage plain-language factors', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getGenerations.mockResolvedValue([{ id: 3, status: 'optimal' }])
    getExplanations.mockResolvedValue([EXPLANATION])
  })

  it('renders readable phrases for known factor keys instead of the literal "factor"', async () => {
    render(<FairSchedulingExplanationsPage />)
    const select = await screen.findByRole('combobox')
    fireEvent.change(select, { target: { value: '3' } })

    expect(await screen.findByText('Matched their preferences')).toBeInTheDocument()
    expect(screen.getByText('Balanced their workload')).toBeInTheDocument()
    // unknown key gets a humanized fallback, never the bare word "factor"
    expect(screen.getByText('Mystery metric')).toBeInTheDocument()
    expect(screen.queryByText('factor')).not.toBeInTheDocument()
  })
})
