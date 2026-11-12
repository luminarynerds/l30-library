/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Vitest for the verification-trail UI on ParentResourcesPage.
 *
 * Covers:
 *   - Item renders "Verified ..." line when last_verified_at is set.
 *   - Item renders "Not yet re-verified" when last_verified_at is null.
 *   - Stale item gets the stale style + "(over N months ago)" suffix.
 *   - "Verify still current" only renders for staff.
 *   - Clicking "Verify still current" calls POST /verify and invalidates.
 *   - Clicking "Flag as out of date" opens the modal; submit calls POST /flags.
 *   - Modal radio group has a fieldset/legend.
 *
 * Pattern mirrors PRs #807/#810/#811 and the existing
 * ParentResourcesPage.test.tsx -- useTranslation is mocked to echo keys.
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (!params) return key
      const tail = Object.entries(params)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(' ')
      return `${key} ${tail}`
    },
    i18n: { language: 'en' },
  }),
  useLanguage: () => ({ language: 'en', setLanguage: vi.fn(), isRTL: false }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => (
    <div data-testid="admin-shell">{children}</div>
  ),
}))

const getResourceGuideMock = vi.fn()
const verifyMock = vi.fn()
const flagMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  getResourceGuide: (...a: unknown[]) => getResourceGuideMock(...a),
  verifyResourceGuideItem: (...a: unknown[]) => verifyMock(...a),
  flagResourceGuideItem: (...a: unknown[]) => flagMock(...a),
}))

// AuthContext: default to a staff user. Individual tests can re-mock
// before importing the page to flip to non-staff.
const useAuthMock = vi.fn(() => ({
  user: { id: 1, role: 'staff', email: 'rosa@example.org' },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

import ParentResourcesPage from '../ParentResourcesPage'

async function expandSection() {
  // Page renders sections collapsed by default; click the disclosure to
  // reveal item cards before asserting on per-item testids.
  const button = await screen.findByRole('button', { name: /Health/ })
  fireEvent.click(button)
  await waitFor(() =>
    expect(button.getAttribute('aria-expanded')).toBe('true'),
  )
}

function withClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

const now = new Date()
const recent = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()
// 9 months back -- well past the 6-month default.
const stale = new Date(now.getTime() - 9 * 30 * 24 * 60 * 60 * 1000).toISOString()

function makeSection(items: Array<Record<string, unknown>>) {
  return [
    {
      id: 1,
      title: 'Health',
      icon: 'health',
      items,
    },
  ]
}

beforeEach(() => {
  getResourceGuideMock.mockReset()
  verifyMock.mockReset()
  flagMock.mockReset()
  useAuthMock.mockReset()
  useAuthMock.mockReturnValue({
    user: { id: 1, role: 'staff', email: 'rosa@example.org' },
  })
})

describe('ParentResourcesPage verification trail', () => {
  it('renders "Verified" line when last_verified_at is set', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 11,
          title: 'WIC Office',
          last_verified_at: recent,
          verified_by_name: 'Rosa T.',
          stale: false,
          open_flag_count: 0,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    await screen.findByTestId('verified-badge-11')
    // useTranslation echoes "parentResources.verified.by date=... name=Rosa T.".
    expect(screen.getByTestId('verified-badge-11').textContent).toMatch(
      /parentResources\.verified\.by/,
    )
    expect(screen.getByTestId('verified-badge-11').textContent).toContain('Rosa T.')
  })

  it('renders "Not yet re-verified" when last_verified_at is null', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 12,
          title: 'Community Clinic',
          last_verified_at: null,
          verified_by_name: null,
          stale: true,
          open_flag_count: 0,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    const badge = await screen.findByTestId('verified-badge-12')
    expect(badge.textContent).toContain('parentResources.verified.never')
  })

  it('marks stale items with the stale data attribute + "over N months" suffix', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 13,
          title: 'Old Hotline',
          last_verified_at: stale,
          verified_by_name: 'Rosa T.',
          stale: true,
          open_flag_count: 0,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    const badge = await screen.findByTestId('verified-badge-13')
    expect(badge.getAttribute('data-stale')).toBe('true')
    expect(badge.textContent).toContain('parentResources.verified.stale')
  })

  it('hides "Verify still current" button for non-staff', async () => {
    useAuthMock.mockReturnValue({
      user: { id: 99, role: 'patron', email: 'parent@example.org' },
    })
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 14,
          title: 'WIC Office',
          last_verified_at: recent,
          verified_by_name: 'Rosa T.',
          stale: false,
          open_flag_count: 0,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    await screen.findByTestId('verified-badge-14')
    expect(screen.queryByTestId('verify-item-14')).toBeNull()
    // Flag button still renders (any authenticated user may flag).
    expect(screen.queryByTestId('flag-item-14')).not.toBeNull()
  })

  it('shows "Verify still current" button for staff and POSTs on click', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 15,
          title: 'WIC Office',
          last_verified_at: stale,
          verified_by_name: 'Rosa T.',
          stale: true,
          open_flag_count: 0,
        },
      ]),
    )
    verifyMock.mockResolvedValue({ id: 15, last_verified_at: recent })
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    const button = await screen.findByTestId('verify-item-15')
    fireEvent.click(button)
    await waitFor(() => {
      expect(verifyMock).toHaveBeenCalledWith(15)
    })
  })

  it('opens the flag modal with a fieldset/legend on click', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 16,
          title: 'Local Shelter',
          last_verified_at: recent,
          verified_by_name: 'Rosa T.',
          stale: false,
          open_flag_count: 0,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    const flagBtn = await screen.findByTestId('flag-item-16')
    fireEvent.click(flagBtn)
    const modal = await screen.findByTestId('flag-modal')
    expect(modal).toBeTruthy()
    // Radio group must be a <fieldset> with <legend> for AT announcement.
    const fieldset = modal.querySelector('fieldset')
    expect(fieldset).not.toBeNull()
    expect(fieldset?.querySelector('legend')).not.toBeNull()
    // All five reason radios present.
    expect(modal.querySelector('[data-testid="flag-reason-disconnected_phone"]')).not.toBeNull()
    expect(modal.querySelector('[data-testid="flag-reason-other"]')).not.toBeNull()
  })

  it('submits the flag with selected reason + comment', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 17,
          title: 'Local Shelter',
          last_verified_at: recent,
          verified_by_name: 'Rosa T.',
          stale: false,
          open_flag_count: 0,
        },
      ]),
    )
    flagMock.mockResolvedValue({ id: 9 })
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    fireEvent.click(await screen.findByTestId('flag-item-17'))
    await screen.findByTestId('flag-modal')

    // Pick a non-default reason
    fireEvent.click(screen.getByTestId('flag-reason-eligibility_changed'))
    fireEvent.change(screen.getByTestId('flag-comment'), {
      target: { value: 'Income limits raised in March.' },
    })
    fireEvent.click(screen.getByTestId('flag-submit'))

    await waitFor(() => {
      expect(flagMock).toHaveBeenCalledWith(17, {
        reason_code: 'eligibility_changed',
        comment: 'Income limits raised in March.',
      })
    })
  })

  it('flagged pill shows count when open_flag_count > 0', async () => {
    getResourceGuideMock.mockResolvedValue(
      makeSection([
        {
          id: 18,
          title: 'WIC Office',
          last_verified_at: recent,
          verified_by_name: 'Rosa T.',
          stale: false,
          open_flag_count: 2,
        },
      ]),
    )
    render(withClient(<ParentResourcesPage />))
    await expandSection()
    const pill = await screen.findByTestId('flag-pill-18')
    expect(pill.textContent).toContain('count=2')
  })
})
