/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression test for the /acquisition/funds/intelligence contract. The
 * component must read the backend's snake_case shape (warning_level, *_amount,
 * per-fund fy2025_comparison) and render without crashing the error boundary.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../../../__tests__/utils/test-utils'
import BudgetIntelligence from '../BudgetIntelligence'

const mocks = vi.hoisted(() => ({ fetchApi: vi.fn() }))

vi.mock('@/api/fetchApi', () => ({ fetchApi: mocks.fetchApi }))

const BACKEND_RESPONSE = {
  funds: [
    {
      fund_id: 1,
      fund_code: 'BOOKS',
      fund_name: 'Adult Materials',
      fiscal_year: 2026,
      allocated_amount: 10000,
      spent_amount: 9500,
      encumbered_amount: 0,
      available_amount: 500,
      spending_velocity: 1200,
      projected_exhaustion_date: '2026-07-01',
      months_remaining: 0.4,
      warning_level: 'critical',
      fy2025_comparison: {
        fy2025_allocated: 8000,
        fy2025_spent: 7800,
        allocation_change_pct: 25.0,
        spending_change_pct: 21.8,
      },
    },
    {
      fund_id: 2,
      fund_code: 'KIDS',
      fund_name: 'Childrens',
      fiscal_year: 2026,
      allocated_amount: 5000,
      spent_amount: 1000,
      encumbered_amount: 0,
      available_amount: 4000,
      spending_velocity: 200,
      projected_exhaustion_date: null,
      months_remaining: null,
      warning_level: 'ok',
      fy2025_comparison: null,
    },
  ],
  alerts: ['CRITICAL: Fund stub'],
  total_allocated: 15000,
  total_spent: 10500,
  total_available: 4500,
}

const formatMoney = (n: number) => `$${n.toLocaleString()}`

describe('BudgetIntelligence', () => {
  beforeEach(() => {
    mocks.fetchApi.mockReset()
  })

  it('renders the backend snake_case contract without crashing', async () => {
    mocks.fetchApi.mockResolvedValue(BACKEND_RESPONSE)
    render(<BudgetIntelligence token="t" formatMoney={formatMoney} />)

    expect((await screen.findAllByText('Adult Materials')).length).toBeGreaterThan(0)
    // warning_level "critical" capitalized in the status badge + alert
    expect(screen.getAllByText('Critical').length).toBeGreaterThan(0)
    // FY comparison table derived from per-fund fy2025_comparison
    expect(screen.getByText('FY2025 vs FY2026 Comparison')).toBeInTheDocument()
    expect(mocks.fetchApi).toHaveBeenCalledWith('/acquisition/funds/intelligence')
  })
})
