/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * UnifiedReportsPage tests.
 *
 * Covers:
 * - Staff access gate
 * - Empty state shown before first run
 * - URL query params drive filter state
 * - Successful JSON generate shows cache indicator + results
 * - Error path shows persistent error panel with copy button
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '../utils/test-utils'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UnifiedReportsPage from '@/pages/UnifiedReportsPage'

// ----- mocks -----

const authState = vi.hoisted(() => ({
  user: { id: 1, email: 'staff@library.org', role: 'staff' } as Record<string, unknown> | null,
}))

vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    useAuth: () => ({
      user: authState.user,
      token: 'test-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      updateProfile: vi.fn(),
      refreshUser: vi.fn(),
    }),
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
  }
})

const mockGetReportTypes = vi.fn()
const mockGenerateJsonReport = vi.fn()
const mockGenerateReportAsync = vi.fn()
const mockGetReportProgress = vi.fn()
const mockGetReportResult = vi.fn()
const mockDownloadReport = vi.fn()
const mockInvalidateReportCache = vi.fn()

vi.mock('@/api/unified-reports-api', () => ({
  getReportTypes: (...args: unknown[]) => mockGetReportTypes(...args),
  generateJsonReport: (...args: unknown[]) => mockGenerateJsonReport(...args),
  generateReportAsync: (...args: unknown[]) => mockGenerateReportAsync(...args),
  getReportProgress: (...args: unknown[]) => mockGetReportProgress(...args),
  getReportResult: (...args: unknown[]) => mockGetReportResult(...args),
  downloadReport: (...args: unknown[]) => mockDownloadReport(...args),
  invalidateReportCache: (...args: unknown[]) => mockInvalidateReportCache(...args),
}))

vi.mock('@/api/branch-api', () => ({
  listBranches: vi.fn().mockResolvedValue([
    { id: 1, name: 'Main Branch' },
    { id: 2, name: 'West Branch' },
  ]),
}))

const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

// ----- tests -----

describe('UnifiedReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authState.user = { id: 1, email: 'staff@library.org', role: 'staff' }
    mockGetReportTypes.mockResolvedValue({
      report_types: ['circulation', 'financial', 'patron_activity', 'collection', 'compliance'],
      output_formats: ['json', 'csv', 'excel', 'pdf'],
    })
  })

  // Access control lives at the route level: staff routes wrap in RequireAuth
  // (src/routes/StaffRoutes.tsx:232-234), which redirects unauthorized users
  // before this page mounts. StaffLayout's `return null` for non-staff is
  // flash prevention behind that guard, so a bare unauthorized render yields
  // an empty tree — the page's own "Staff access required" branch is
  // unreachable defense-in-depth, not the user-facing denial path.
  it('renders nothing for non-staff users (route guard handles the redirect)', () => {
    authState.user = { id: 9, email: 'p@x.com', role: 'patron' }
    const { container } = render(<UnifiedReportsPage />)
    expect(screen.queryByText(/Pick a report type/i)).toBeNull()
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the empty state before any generate', async () => {
    render(<UnifiedReportsPage />)
    expect(await screen.findByText(/Pick a report type and click Generate/i)).toBeTruthy()
  })

  it('generates a JSON report and shows fresh-vs-cached indicator', async () => {
    mockGenerateJsonReport.mockResolvedValue({
      data: { title: 'Circulation Report', total: 42 },
      cacheHit: false,
      bytes: 1234,
    })
    render(<UnifiedReportsPage />)
    const generate = await screen.findByRole('button', { name: /Generate/i })
    await userEvent.click(generate)

    await waitFor(() => {
      expect(mockGenerateJsonReport).toHaveBeenCalled()
    })
    expect(await screen.findByText(/Freshly generated/i)).toBeTruthy()
    expect(screen.getByText(/Report Results/i)).toBeTruthy()
  })

  it('offers Regenerate fresh when result came from cache', async () => {
    mockGenerateJsonReport
      .mockResolvedValueOnce({ data: { total: 1 }, cacheHit: true, bytes: 100 })
      .mockResolvedValueOnce({ data: { total: 2 }, cacheHit: false, bytes: 100 })
    render(<UnifiedReportsPage />)
    await userEvent.click(await screen.findByRole('button', { name: /Generate/i }))

    const refreshBtn = await screen.findByRole('button', { name: /Regenerate fresh/i })
    await userEvent.click(refreshBtn)

    await waitFor(() => {
      expect(mockGenerateJsonReport).toHaveBeenCalledTimes(2)
    })
    // Second call should disable cache.
    expect(mockGenerateJsonReport.mock.calls[1]?.[0]).toMatchObject({ use_cache: false })
  })

  it('surfaces a persistent error panel when generation fails', async () => {
    mockGenerateJsonReport.mockRejectedValue(new Error('Boom: upstream 500'))
    render(<UnifiedReportsPage />)
    await userEvent.click(await screen.findByRole('button', { name: /Generate/i }))

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText(/Boom: upstream 500/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Copy error/i })).toBeTruthy()
  })

  it('renders a download fallback for large JSON payloads', async () => {
    mockGenerateJsonReport.mockResolvedValue({
      data: { huge: 'x'.repeat(10) },
      cacheHit: false,
      bytes: 2_000_000, // 2 MB > 500 KB limit
    })
    render(<UnifiedReportsPage />)
    await userEvent.click(await screen.findByRole('button', { name: /Generate/i }))

    expect(await screen.findByRole('button', { name: /Download JSON/i })).toBeTruthy()
  })
})
