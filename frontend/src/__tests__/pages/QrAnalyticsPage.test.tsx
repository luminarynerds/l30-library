/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '../utils/test-utils'

// Per-file AuthContext override -- the global setup.ts mock isn't a vi.fn(),
// so authenticated/role-gated route tests need this pattern.
// (memory: feedback_l30_authcontext_global_mock_override)
const mockUser = {
  id: 1,
  first_name: 'Test',
  last_name: 'Staff',
  role: 'staff',
  email: 's@l30.org',
}
let currentUser: typeof mockUser | { role: string } = mockUser
let isAuthenticated = true

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    token: 'test-token',
    isLoading: false,
    isAuthenticated,
    sessionExpired: false,
    clearSessionExpired: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
    showTimeoutWarning: false,
    timeoutSeconds: 120,
    dismissTimeoutWarning: vi.fn(),
    extendSession: vi.fn(),
    getSessionDuration: vi.fn(() => null),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Stub the api client so the page doesn't try to fetch.
const mockGetQrAnalytics = vi.fn()
const mockGetQrAnalyticsByMonth = vi.fn()
vi.mock('@/api/qr-analytics-api', () => ({
  getQrAnalytics: (...args: unknown[]) => mockGetQrAnalytics(...args),
  getQrAnalyticsByMonth: (...args: unknown[]) => mockGetQrAnalyticsByMonth(...args),
}))

import QrAnalyticsPage from '@/pages/QrAnalyticsPage'
import RequireAuth from '@/components/RequireAuth'
import { ApiError } from '@/lib/api-client'

const STAFF_ROLES = ['staff', 'admin', 'director', 'legal', 'bookmobile', 'homebond', 'board_member']

describe('QrAnalyticsPage', () => {
  beforeEach(() => {
    currentUser = mockUser
    isAuthenticated = true
    mockGetQrAnalytics.mockReset()
    mockGetQrAnalyticsByMonth.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page header', async () => {
    mockGetQrAnalytics.mockResolvedValue([])
    mockGetQrAnalyticsByMonth.mockResolvedValue({ months: [], series: [] })
    render(<QrAnalyticsPage />)
    expect(await screen.findByRole('heading', { name: /QR Poster Scans/i })).toBeInTheDocument()
  })

  it('populates the table from the api response', async () => {
    mockGetQrAnalytics.mockResolvedValue([
      { slug: 'tech-p-printer', pageviews: 50 },
      { slug: 'guide-password-reset', pageviews: 15 },
      { slug: 'tech-launchpad', pageviews: 5 },
    ])
    mockGetQrAnalyticsByMonth.mockResolvedValue({
      months: ['2026-03', '2026-04', '2026-05'],
      series: [
        { slug: 'tech-p-printer', counts: [10, 20, 20] },
        { slug: 'guide-password-reset', counts: [3, 5, 7] },
        { slug: 'tech-launchpad', counts: [1, 2, 2] },
      ],
    })

    render(<QrAnalyticsPage />)

    const table = await screen.findByTestId('qr-analytics-table')
    expect(table).toBeInTheDocument()

    // All three slug rows present.
    expect(screen.getByTestId('qr-analytics-row-tech-p-printer')).toBeInTheDocument()
    expect(screen.getByTestId('qr-analytics-row-guide-password-reset')).toBeInTheDocument()
    expect(screen.getByTestId('qr-analytics-row-tech-launchpad')).toBeInTheDocument()

    // All-time count (formatted with separator).
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()

    // This-month value pulled from the last month index of the trend series.
    const printerRow = screen.getByTestId('qr-analytics-row-tech-p-printer')
    expect(printerRow.textContent).toContain('20') // this month (last index)
  })

  it('shows the empty state when both endpoints return no data', async () => {
    mockGetQrAnalytics.mockResolvedValue([])
    mockGetQrAnalyticsByMonth.mockResolvedValue({ months: [], series: [] })

    render(<QrAnalyticsPage />)

    const empty = await screen.findByTestId('qr-analytics-empty')
    expect(empty.textContent).toMatch(/No QR scans yet/i)
  })

  it('shows the Umami-not-configured empty state on 503', async () => {
    const err503 = new ApiError('Umami website ID not configured', 503, 'Umami website ID not configured')
    mockGetQrAnalytics.mockRejectedValue(err503)
    mockGetQrAnalyticsByMonth.mockRejectedValue(err503)

    render(<QrAnalyticsPage />)

    const empty = await screen.findByTestId('qr-analytics-empty')
    expect(empty.textContent).toMatch(/Analytics not available/i)
    expect(empty.textContent).toMatch(/Umami integration is not configured/i)
  })

  it('shows a distinct insufficient-permissions empty state on 403', async () => {
    const err403 = new ApiError('Staff or admin role required', 403, 'Staff or admin role required')
    mockGetQrAnalytics.mockRejectedValue(err403)
    mockGetQrAnalyticsByMonth.mockRejectedValue(err403)

    render(<QrAnalyticsPage />)

    const empty = await screen.findByTestId('qr-analytics-empty')
    expect(empty.textContent).toMatch(/Insufficient permissions/i)
    expect(empty.textContent).not.toMatch(/Umami/i)
  })

  it('refetches when the period selector changes', async () => {
    mockGetQrAnalytics.mockResolvedValue([])
    mockGetQrAnalyticsByMonth.mockResolvedValue({ months: [], series: [] })

    render(<QrAnalyticsPage />)
    await screen.findByTestId('qr-analytics-empty')

    const radio90 = screen.getByRole('radio', { name: /Last 90 days/i })
    radio90.click()

    await waitFor(() => {
      // Default call (30) + the 90 click.
      expect(mockGetQrAnalytics).toHaveBeenCalledWith(90)
    })
  })
})

describe('QrAnalyticsPage route gate', () => {
  beforeEach(() => {
    currentUser = mockUser
    isAuthenticated = true
  })

  it('redirects a patron away from /staff/qr-scans', () => {
    currentUser = { role: 'patron' }
    isAuthenticated = true

    render(
      <MemoryRouter initialEntries={['/staff/qr-scans']}>
        <Routes>
          <Route
            path="/staff/qr-scans"
            element={
              <RequireAuth requiredRoles={STAFF_ROLES}>
                <div>QR-PAGE</div>
              </RequireAuth>
            }
          />
          <Route path="/account" element={<div>ACCOUNT</div>} />
          <Route path="/login" element={<div>LOGIN</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByText('QR-PAGE')).toBeNull()
    expect(screen.getByText('ACCOUNT')).toBeInTheDocument()
  })

  it.each(STAFF_ROLES)('allows %s through the gate', (role) => {
    // RequireAuth checks `user.is_board_member` instead of the role string
    // for the board_member entry, so we set the flag accordingly.
    currentUser = { ...mockUser, role, is_board_member: role === 'board_member' } as typeof mockUser
    isAuthenticated = true

    render(
      <MemoryRouter initialEntries={['/staff/qr-scans']}>
        <Routes>
          <Route
            path="/staff/qr-scans"
            element={
              <RequireAuth requiredRoles={STAFF_ROLES}>
                <div>QR-PAGE</div>
              </RequireAuth>
            }
          />
          <Route path="/account" element={<div>ACCOUNT</div>} />
          <Route path="/login" element={<div>LOGIN</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('QR-PAGE')).toBeInTheDocument()
  })
})
