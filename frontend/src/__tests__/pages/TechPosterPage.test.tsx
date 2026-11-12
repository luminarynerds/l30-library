/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, userEvent, within } from '../utils/test-utils'

// Per-file override of the global AuthContext mock from setup.ts.
// Without this, the StaffRoutes-style role-gated route would redirect.
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

import TechPosterPage from '@/pages/TechPosterPage'
import RequireAuth from '@/components/RequireAuth'

const STAFF_ROLES = ['staff', 'admin', 'director', 'legal', 'bookmobile', 'homebond', 'board_member']

describe('TechPosterPage', () => {
  beforeEach(() => {
    currentUser = mockUser
    isAuthenticated = true
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders all four destination groups under the category-neutral title', () => {
    render(<TechPosterPage />)
    expect(screen.getByRole('heading', { name: /Help QR Poster/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Quick triage launchpad/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Pre-scoped triage/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Direct to a guide/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Legal help/i })).toBeInTheDocument()
  })

  it('defaults to the /tech launchpad URL and shows a QR for it (with qr=tech-launchpad)', () => {
    render(<TechPosterPage />)
    const qr = screen.getByTestId('tech-poster-qr')
    expect(qr).toBeInTheDocument()
    expect(qr.querySelector('svg')).toBeTruthy()

    const url = screen.getByTestId('tech-poster-url')
    // jsdom origin is http://localhost:3000 by default
    expect(url.textContent).toMatch(/\/tech\?qr=tech-launchpad$/)
  })

  it('updates the encoded URL when a triage destination is picked (?p=printer&qr=tech-p-printer)', async () => {
    const user = userEvent.setup()
    render(<TechPosterPage />)

    const destinations = screen.getByTestId('tech-poster-destinations')
    const printingBtn = within(destinations).getByRole('button', { name: /Printing help/i })
    await user.click(printingBtn)

    const url = screen.getByTestId('tech-poster-url')
    expect(url.textContent).toContain('/tech?p=printer')
    expect(url.textContent).toContain('qr=tech-p-printer')
    expect(printingBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('updates the encoded URL when a guide destination is picked (qr=guide-<id>)', async () => {
    const user = userEvent.setup()
    render(<TechPosterPage />)

    const destinations = screen.getByTestId('tech-poster-destinations')
    // Find a guide button — wireless-printing path is stable
    const btns = within(destinations).getAllByRole('button')
    const guideBtn = btns.find((b) => b.textContent?.includes('/guides/wireless-printing'))
    expect(guideBtn).toBeTruthy()
    await user.click(guideBtn!)

    const url = screen.getByTestId('tech-poster-url')
    expect(url.textContent).toContain('/guides/wireless-printing')
    expect(url.textContent).toContain('qr=guide-wireless-printing')
  })

  it('encodes /legal with qr=legal-main when the Legal Help (main page) card is picked', async () => {
    const user = userEvent.setup()
    render(<TechPosterPage />)

    const destinations = screen.getByTestId('tech-poster-destinations')
    const legalBtn = within(destinations).getByRole('button', { name: /Legal Help \(main page\)/i })
    await user.click(legalBtn)

    const url = screen.getByTestId('tech-poster-url')
    expect(url.textContent).toMatch(/\/legal\?qr=legal-main$/)
    expect(legalBtn).toHaveAttribute('aria-pressed', 'true')

    const qr = screen.getByTestId('tech-poster-qr')
    expect(qr.getAttribute('aria-label')).toMatch(/\/legal\?qr=legal-main$/)
  })

  it('encodes /legal/calculators with qr=legal-calculators when the Legal calculators card is picked', async () => {
    const user = userEvent.setup()
    render(<TechPosterPage />)

    const destinations = screen.getByTestId('tech-poster-destinations')
    const calcBtn = within(destinations).getByRole('button', { name: /Legal calculators/i })
    await user.click(calcBtn)

    const url = screen.getByTestId('tech-poster-url')
    expect(url.textContent).toMatch(/\/legal\/calculators\?qr=legal-calculators$/)
    expect(calcBtn).toHaveAttribute('aria-pressed', 'true')

    const qr = screen.getByTestId('tech-poster-qr')
    expect(qr.getAttribute('aria-label')).toMatch(/\/legal\/calculators\?qr=legal-calculators$/)
  })
})

describe('TechPosterPage route gate', () => {
  beforeEach(() => {
    currentUser = mockUser
    isAuthenticated = true
  })

  it('redirects a patron away from the gated route', () => {
    currentUser = { role: 'patron' }
    isAuthenticated = true

    render(
      <MemoryRouter initialEntries={['/tech/poster']}>
        <Routes>
          <Route
            path="/tech/poster"
            element={
              <RequireAuth requiredRoles={STAFF_ROLES}>
                <div>POSTER</div>
              </RequireAuth>
            }
          />
          <Route path="/account" element={<div>ACCOUNT</div>} />
          <Route path="/login" element={<div>LOGIN</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByText('POSTER')).toBeNull()
    expect(screen.getByText('ACCOUNT')).toBeInTheDocument()
  })

  it('allows a staff user through the gate', () => {
    currentUser = { ...mockUser, role: 'staff' }
    isAuthenticated = true

    render(
      <MemoryRouter initialEntries={['/tech/poster']}>
        <Routes>
          <Route
            path="/tech/poster"
            element={
              <RequireAuth requiredRoles={STAFF_ROLES}>
                <div>POSTER</div>
              </RequireAuth>
            }
          />
          <Route path="/account" element={<div>ACCOUNT</div>} />
          <Route path="/login" element={<div>LOGIN</div>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('POSTER')).toBeInTheDocument()
  })
})
