/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, userEvent } from '@/__tests__/utils/test-utils'
import { fireEvent } from '@testing-library/react'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const enterFinanceMock = vi.fn()
vi.mock('@/api/annual-reports-api', () => ({
  enterAnnualReportFinance: (...args: unknown[]) => enterFinanceMock(...args),
}))

import FinanceEntryModal from '../FinanceEntryModal'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const report = { id: 7, fiscal_year: 2025 } as any

describe('FinanceEntryModal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('derives totals from line items and submits a reconciling payload', async () => {
    enterFinanceMock.mockResolvedValue({ report_id: 7, data_source: 'manual' })
    const onSaved = vi.fn().mockResolvedValue(undefined)
    const onClose = vi.fn()

    const { container } = render(
      <FinanceEntryModal report={report} onClose={onClose} onSaved={onSaved} />
    )
    const user = userEvent.setup()

    const byId = (id: string) => container.querySelector(`#${id}`) as HTMLInputElement

    await user.type(byId('revenue-local'), '60')
    await user.type(byId('revenue-state'), '30')
    await user.type(byId('revenue-federal'), '10')

    await user.type(byId('expenditure-salaries'), '70')
    await user.type(byId('expenditure-print'), '30')

    await user.type(byId('capital-outlay'), '5')

    // Totals are derived from the line items.
    expect(screen.getByTestId('revenue-total')).toHaveTextContent('$100.00')
    expect(screen.getByTestId('expenditure-total')).toHaveTextContent('$100.00')

    // Submit via the form's submit event. userEvent.click on a submit button
    // relies on form.requestSubmit(), which jsdom does not implement, so dispatch
    // the submit event directly.
    const saveButton = screen.getByRole('button', { name: /save finance/i })
    fireEvent.submit(saveButton.closest('form') as HTMLFormElement)

    await waitFor(() => expect(enterFinanceMock).toHaveBeenCalledTimes(1))
    const [token, reportId, payload] = enterFinanceMock.mock.calls[0]!
    expect(token).toBe('test-token')
    expect(reportId).toBe(7)
    expect(payload.total_operating_revenue).toBe(100)
    expect(payload.revenue).toEqual({ local: 60, state: 30, federal: 10, other: 0 })
    expect(payload.total_operating_expenditure).toBe(100)
    expect(payload.expenditure).toEqual({
      salaries: 70,
      benefits: 0,
      print: 30,
      electronic: 0,
      other: 0,
    })
    expect(payload.capital_outlay).toBe(5)

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})
