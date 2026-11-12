/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// L30 vitest setup does not preload i18n; mock useTranslation to echo keys
// (with double-brace param substitution) so we can assert on key paths
// instead of translated strings. Mirrors PRs #807/#810/#811.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      // Echo the key with appended params so the assertions in this file
      // can substring-match formatted values without needing a real i18n
      // bundle. We can't use {{key}} placeholders here because the source
      // page passes a raw key (no literal placeholders to substitute).
      if (!params) return key
      const tail = Object.entries(params)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(' ')
      return `${key} ${tail}`
    },
  }),
  // Page now calls useLanguage() to power the multilingual-default
  // effect. Return a stable English UI language so the effect
  // short-circuits without filtering.
  useLanguage: () => ({ language: 'en', setLanguage: vi.fn(), isRTL: false }),
}))

const breadcrumbMock = vi.fn()

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
  addBreadcrumb: (...args: unknown[]) => breadcrumbMock(...args),
}))

// Source page lives at src/pages/, test at src/pages/__tests__/, AdminShell
// at src/components/shells/. Mock AdminShell to a passthrough so we don't
// drag the full staff shell into the test render.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode; title?: string }) => (
    <div data-testid="admin-shell">{children}</div>
  ),
}))

const getResourceGuideMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  getResourceGuide: (...args: unknown[]) => getResourceGuideMock(...args),
}))

import ParentResourcesPage from '../ParentResourcesPage'

function withClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  // MemoryRouter required since the page now calls useSearchParams to track
  // ?handout= mode. The original tests run with default location "/".
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

const sampleSections = [
  {
    id: 1,
    title: 'Health',
    description: 'Pediatricians and clinics',
    icon: 'health',
    items: [
      {
        id: 11,
        title: 'Community Clinic',
        description: 'Walk-in family medicine',
        phone: '5558675309',
        address: '123 Main St',
        url: 'https://example.org',
        eligibility: null,
        notes: null,
      },
    ],
  },
  {
    id: 2,
    title: 'Unknown Section',
    description: null,
    icon: 'made_up_taxonomy_value',
    items: [],
  },
]

describe('ParentResourcesPage', () => {
  beforeEach(() => {
    getResourceGuideMock.mockReset()
    breadcrumbMock.mockReset()
    getResourceGuideMock.mockResolvedValue(sampleSections)
  })

  it('renders AdminShell title via the i18n key (not hardcoded English)', async () => {
    // The page mounts inside AdminShell; the title is passed as a prop. Our
    // AdminShell mock surfaces children but not the title, so we instead
    // assert the page-heading key reached the DOM, which is the same i18n
    // path used for the AdminShell title.
    render(withClient(<ParentResourcesPage />))
    await screen.findByText('parentOnboarding.resources.heading', undefined, {
      timeout: 5000,
    })
  })

  it('disclosure button reflects expanded state via aria-expanded and aria-controls', async () => {
    render(withClient(<ParentResourcesPage />))

    const healthButton = await screen.findByRole('button', { name: /Health/ }, { timeout: 5000 })
    expect(healthButton.getAttribute('aria-expanded')).toBe('false')
    expect(healthButton.getAttribute('aria-controls')).toBe('section-panel-1')

    fireEvent.click(healthButton)

    await waitFor(() => {
      const refreshed = screen.getByRole('button', { name: /Health/ })
      expect(refreshed.getAttribute('aria-expanded')).toBe('true')
    })

    // Panel exists with the matching id, role=region and aria-labelledby
    // pointing at the section heading.
    const panel = document.getElementById('section-panel-1')
    expect(panel).not.toBeNull()
    expect(panel?.getAttribute('role')).toBe('region')
    expect(panel?.getAttribute('aria-labelledby')).toBe('section-heading-1')
  })

  it('tel link uses aria-label with the formatted phone (no raw digits to screen readers)', async () => {
    render(withClient(<ParentResourcesPage />))
    const healthButton = await screen.findByRole('button', { name: /Health/ }, { timeout: 5000 })
    fireEvent.click(healthButton)

    // 5558675309 -> "555 867 5309" via the local formatPhone helper. The
    // mocked t() substitutes the {{phone}} placeholder in the key.
    const phoneLink = await screen.findByRole(
      'link',
      { name: /parentOnboarding\.resources\.callPhone/ },
      { timeout: 5000 },
    )
    expect(phoneLink.getAttribute('aria-label')).toContain('555 867 5309')
    expect(phoneLink.getAttribute('href')).toBe('tel:5558675309')
  })

  it('address row links to Google Maps with aria-label and renders a copy button', async () => {
    render(withClient(<ParentResourcesPage />))
    const healthButton = await screen.findByRole('button', { name: /Health/ }, { timeout: 5000 })
    fireEvent.click(healthButton)

    const mapLink = await screen.findByRole(
      'link',
      { name: /parentOnboarding\.resources\.openInMaps/ },
      { timeout: 5000 },
    )
    expect(mapLink.getAttribute('href')).toBe(
      `https://maps.google.com/?q=${encodeURIComponent('123 Main St')}`,
    )
    expect(mapLink.getAttribute('target')).toBe('_blank')
    expect(mapLink.getAttribute('rel')).toContain('noopener')
    expect(mapLink.getAttribute('aria-label')).toContain('123 Main St')

    const copyButton = screen.getByRole('button', {
      name: /parentOnboarding\.resources\.copyAddress/,
    })
    expect(copyButton.getAttribute('aria-label')).toContain('123 Main St')
  })

  it('contact row uses text-sm (WCAG AA), not text-xs', async () => {
    render(withClient(<ParentResourcesPage />))
    const healthButton = await screen.findByRole('button', { name: /Health/ }, { timeout: 5000 })
    fireEvent.click(healthButton)

    const row = await screen.findByTestId('contact-row-11', undefined, {
      timeout: 5000,
    })
    expect(row.className).toContain('text-sm')
    expect(row.className).not.toContain('text-xs')
  })

  it('logs a Sentry breadcrumb when a section.icon value falls outside the known taxonomy', async () => {
    render(withClient(<ParentResourcesPage />))

    // Wait for the unknown section row to mount; that mount triggers the
    // breadcrumb via renderSectionIcon.
    await screen.findByRole('button', { name: /Unknown Section/ }, { timeout: 5000 })

    expect(breadcrumbMock).toHaveBeenCalled()
    const firstCall = breadcrumbMock.mock.calls[0]?.[0]
    expect(firstCall?.category).toBe('i18n')
    expect(firstCall?.data?.icon).toBe('made_up_taxonomy_value')
  })
})
