/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, userEvent } from '@/__tests__/utils/test-utils'
import { ApiError } from '@/lib/api-client'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const certifyMock = vi.fn()
const getReconciliationMock = vi.fn()
vi.mock('@/api/annual-reports-api', () => ({
  certifyAnnualReport: (...args: unknown[]) => certifyMock(...args),
  getReconciliation: (...args: unknown[]) => getReconciliationMock(...args),
  // Other functions the modal imports; unused in these tests.
  validateAnnualReport: vi.fn(),
  getYoYComparison: vi.fn(),
  exportAsExcel: vi.fn(),
  exportAsPdf: vi.fn(),
  downloadFile: vi.fn(),
  formatCurrency: (v: number | undefined) => String(v ?? 'N/A'),
  formatNumber: (v: number | undefined) => String(v ?? 'N/A'),
  formatPercent: (v: number | undefined) => String(v ?? 'N/A'),
}))

import ReportDetailsModal from '../ReportDetailsModal'


const baseReport = {
  id: 7,
  fiscal_year: 2025,
  state_code: 'OH',
  library_name: 'Little Schitt Creek Library',
  status: 'generated',
  is_validated: false,
} as any

describe('ReportDetailsModal — certify flow', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders inline validation errors when certify returns 409', async () => {
    const four09 = new ApiError('Validation failed', 409, 'Validation failed', undefined, {
      error: {
        code: 'HTTP_409',
        message: {
          message: 'Report cannot be certified',
          error_count: 2,
          errors: [
            { field: 'total_operating_revenue', message: 'Revenue is required' },
            { field: 'total_staff_fte', message: 'Staff FTE is missing' },
          ],
        },
      },
    })
    certifyMock.mockRejectedValue(four09)
    const onRefresh = vi.fn().mockResolvedValue(undefined)

    render(
      <ReportDetailsModal report={baseReport} onClose={vi.fn()} onRefresh={onRefresh} />
    )
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /certify/i }))

    await waitFor(() => expect(certifyMock).toHaveBeenCalledTimes(1))
    const [token, reportId] = certifyMock.mock.calls[0]!
    expect(token).toBe('test-token')
    expect(reportId).toBe(7)

    // Each blocking validation error is surfaced inline.
    expect(await screen.findByText('Revenue is required')).toBeInTheDocument()
    expect(screen.getByText('Staff FTE is missing')).toBeInTheDocument()
    expect(screen.getByText('total_operating_revenue')).toBeInTheDocument()
  })

  it('certifies a valid report and refreshes the list', async () => {
    certifyMock.mockResolvedValue({
      report_id: 7,
      status: 'validated',
      is_validated: true,
      validated_by_id: 1,
    })
    const onRefresh = vi.fn().mockResolvedValue(undefined)
    const report = Object.freeze({ ...baseReport })

    render(
      <ReportDetailsModal report={report} onClose={vi.fn()} onRefresh={onRefresh} />
    )
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /certify/i }))

    await waitFor(() => expect(certifyMock).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(onRefresh).toHaveBeenCalled())
    expect(screen.getByText('Status: Validated')).toBeInTheDocument()
    expect(report.status).toBe('generated')
    expect(report.is_validated).toBe(false)
  })

  it('surfaces persisted report.validation_errors on open', () => {
    const reportWithErrors = {
      ...baseReport,
      validation_errors: [{ field: 'total_items_owned', message: 'Items owned cannot be zero' }],
    }
    render(
      <ReportDetailsModal report={reportWithErrors} onClose={vi.fn()} onRefresh={vi.fn()} />
    )
    expect(screen.getByText('Items owned cannot be zero')).toBeInTheDocument()
  })
})
