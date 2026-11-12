/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// L30 vitest setup does not preload i18n; mock useTranslation to echo keys
// (with double-brace param substitution) so we can assert on key paths
// instead of translated strings. Mirrors the parent test file.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (!params) return key
      const tail = Object.entries(params)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(' ')
      return `${key} ${tail}`
    },
  }),
  // Page now calls useLanguage() to power the multilingual-default
  // effect (feat/parent-resources-multilingual). Stable English UI
  // lang short-circuits the effect without affecting handout flows.
  useLanguage: () => ({ language: 'en', setLanguage: vi.fn(), isRTL: false }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode; title?: string }) => (
    <div data-testid="admin-shell">{children}</div>
  ),
}))

// Mock BrandingContext so HandoutCoverSheet has stable inputs.
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({
    library_name: 'Test Public Library',
    library_short_name: 'TPL',
    domain: '',
    contact_email: 'hello@tpl.example',
    privacy_email: '',
    indie_email: '',
    giving_email: '',
    events_email: '',
    print_email: '',
    makerspace_email: '',
    phone: '555 867 5309',
    address_line1: '100 Main St',
    address_line2: '',
    city: 'Anytown',
    state: 'OH',
    zip_code: '44000',
    primary_color: '#8B5E5E',
    accent_color: '#D49898',
    card_prefix: '',
    product_name: '',
    product_tagline: '',
    hero_title: '',
    hero_subtitle: '',
    tagline: '',
    is_demo: false,
    bluesky_url: '',
    mastodon_url: '',
    seasonal_callout_active: false,
  }),
}))

// Mock qrcode.react so we don't pay the QR computation per item per test;
// the test only cares that the QR component is *rendered* with the right url.
vi.mock('qrcode.react', () => ({
  QRCodeSVG: ({ value }: { value: string }) => (
    <svg data-testid="qr-svg" data-qr-value={value} />
  ),
}))

const getResourceGuideMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  getResourceGuide: (...args: unknown[]) => getResourceGuideMock(...args),
}))

import ParentResourcesPage from '../ParentResourcesPage'

function withProviders(ui: ReactNode, initialEntries: string[] = ['/']) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <MemoryRouter initialEntries={initialEntries}>
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
      {
        id: 12,
        title: 'Pediatrician Network',
        description: 'Find a doctor',
        url: 'https://peds.example.org',
        eligibility: null,
        notes: null,
      },
    ],
  },
  {
    id: 2,
    title: 'Childcare',
    description: 'Daycare and after-school',
    icon: 'childcare',
    items: [
      {
        id: 21,
        title: 'Tot Spot',
        url: 'https://totspot.example.org',
        eligibility: null,
        notes: null,
      },
    ],
  },
]

describe('ParentResourcesPage handout mode', () => {
  beforeEach(() => {
    getResourceGuideMock.mockReset()
    getResourceGuideMock.mockResolvedValue(sampleSections)
  })

  it('"Build handout" enters builder mode and seeds default selection (all checked)', async () => {
    render(withProviders(<ParentResourcesPage />))

    const enterBtn = await screen.findByTestId('enter-handout-mode', undefined, {
      timeout: 5000,
    })
    fireEvent.click(enterBtn)

    // Toolbar mounts with all-on counts: 2 of 2 sections, 3 of 3 items.
    const toolbar = await screen.findByTestId('handout-toolbar', undefined, {
      timeout: 5000,
    })
    expect(within(toolbar).getByTestId('handout-toolbar-sections-count').textContent).toContain('selected=2')
    expect(within(toolbar).getByTestId('handout-toolbar-sections-count').textContent).toContain('total=2')
    expect(within(toolbar).getByTestId('handout-toolbar-items-count').textContent).toContain('selected=3')
    expect(within(toolbar).getByTestId('handout-toolbar-items-count').textContent).toContain('total=3')

    // Every section + item checkbox is checked.
    expect((screen.getByTestId('handout-section-checkbox-1') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('handout-section-checkbox-2') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('handout-item-checkbox-11') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('handout-item-checkbox-12') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('handout-item-checkbox-21') as HTMLInputElement).checked).toBe(true)
  })

  it('per-item checkbox toggles independently; section header reflects indeterminate (aria-checked="mixed")', async () => {
    render(withProviders(<ParentResourcesPage />))

    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Uncheck just item 11 of section 1.
    fireEvent.click(screen.getByTestId('handout-item-checkbox-11'))
    expect((screen.getByTestId('handout-item-checkbox-11') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByTestId('handout-item-checkbox-12') as HTMLInputElement).checked).toBe(true)

    // Section 1 master checkbox is now indeterminate (aria-checked="mixed").
    const sectionBox = screen.getByTestId('handout-section-checkbox-1') as HTMLInputElement
    expect(sectionBox.getAttribute('aria-checked')).toBe('mixed')

    // Toolbar counts reflect partial selection: section still counted (has 1
    // picked item), items 2 of 3.
    expect(screen.getByTestId('handout-toolbar-items-count').textContent).toContain('selected=2')
    expect(screen.getByTestId('handout-toolbar-sections-count').textContent).toContain('selected=2')
  })

  it('section header checkbox toggles all items in that section', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Section 1 is currently fully selected. Clicking unselects both items.
    fireEvent.click(screen.getByTestId('handout-section-checkbox-1'))
    expect((screen.getByTestId('handout-item-checkbox-11') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByTestId('handout-item-checkbox-12') as HTMLInputElement).checked).toBe(false)

    // Section header reads false (not mixed) when fully unselected.
    expect(screen.getByTestId('handout-section-checkbox-1').getAttribute('aria-checked')).toBe('false')

    // Re-click brings everything in section 1 back.
    fireEvent.click(screen.getByTestId('handout-section-checkbox-1'))
    expect((screen.getByTestId('handout-item-checkbox-11') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('handout-item-checkbox-12') as HTMLInputElement).checked).toBe(true)
  })

  it('large-type toggle sets data-large-type on the print root', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    const root = screen.getByTestId('parent-resources-print-root')
    expect(root.getAttribute('data-large-type')).toBe('false')

    fireEvent.click(screen.getByTestId('handout-toggle-large-type'))
    expect(root.getAttribute('data-large-type')).toBe('true')

    fireEvent.click(screen.getByTestId('handout-toggle-large-type'))
    expect(root.getAttribute('data-large-type')).toBe('false')
  })

  it('QR codes render only for items with a url and only when the QR toggle is on', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Default: QR toggle OFF -- no QR svgs in the DOM.
    expect(screen.queryByTestId('handout-qr-11')).toBeNull()
    expect(screen.queryByTestId('handout-qr-12')).toBeNull()

    fireEvent.click(screen.getByTestId('handout-toggle-qr-codes'))

    // All sample items have url; expect a QR for each (3 QRs).
    expect(screen.getByTestId('handout-qr-11')).toBeTruthy()
    expect(screen.getByTestId('handout-qr-12')).toBeTruthy()
    expect(screen.getByTestId('handout-qr-21')).toBeTruthy()

    // QR value matches the item url.
    const qr11 = screen.getByTestId('handout-qr-11').querySelector('[data-qr-value]')
    expect(qr11?.getAttribute('data-qr-value')).toBe('https://example.org')

    // Toggle off again -- QRs disappear.
    fireEvent.click(screen.getByTestId('handout-toggle-qr-codes'))
    expect(screen.queryByTestId('handout-qr-11')).toBeNull()
  })

  it('cover sheet toggle renders <HandoutCoverSheet/> with branding fields', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    expect(screen.queryByTestId('handout-cover-sheet')).toBeNull()

    fireEvent.click(screen.getByTestId('handout-toggle-cover-sheet'))

    const cover = screen.getByTestId('handout-cover-sheet')
    // Library name and phone come from the mocked BrandingContext.
    expect(cover.textContent).toContain('Test Public Library')
    expect(cover.textContent).toContain('555 867 5309')
    // Cover sheet pulls libraryLine and contactPrompt i18n keys.
    expect(cover.textContent).toContain('parentResources.handout.coverSheet.libraryLine')
    expect(cover.textContent).toContain('parentResources.handout.coverSheet.contactPrompt')
  })

  it('cancel exits handout mode, clears selection and toggles, removes ?handout from URL', async () => {
    render(withProviders(<ParentResourcesPage />, ['/parent-resources?handout=building']))

    // Toolbar should mount immediately because URL already has ?handout=building.
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Turn on large-type so we can prove it gets cleared.
    fireEvent.click(screen.getByTestId('handout-toggle-large-type'))
    expect(screen.getByTestId('parent-resources-print-root').getAttribute('data-large-type')).toBe('true')

    fireEvent.click(screen.getByTestId('handout-cancel'))

    expect(screen.queryByTestId('handout-toolbar')).toBeNull()
    expect(screen.getByTestId('parent-resources-print-root').getAttribute('data-large-type')).toBe('false')
    // The "Build handout" entry button is visible again.
    expect(screen.queryByTestId('enter-handout-mode')).not.toBeNull()
  })

  it('Preview & print calls window.print()', async () => {
    // jsdom does not implement window.print; define it before spying.
    const originalPrint = window.print
    const printFn = vi.fn()
    Object.defineProperty(window, 'print', {
      configurable: true,
      writable: true,
      value: printFn,
    })

    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    fireEvent.click(screen.getByTestId('handout-preview-print'))
    expect(printFn).toHaveBeenCalledTimes(1)

    Object.defineProperty(window, 'print', {
      configurable: true,
      writable: true,
      value: originalPrint,
    })
  })

  it('Preview & print is disabled when zero items are selected', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Uncheck all sections.
    fireEvent.click(screen.getByTestId('handout-section-checkbox-1'))
    fireEvent.click(screen.getByTestId('handout-section-checkbox-2'))

    const btn = screen.getByTestId('handout-preview-print') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
    expect(btn.getAttribute('aria-disabled')).toBe('true')
  })

  it('unselected items get print:hidden class so they drop out of the printed output', async () => {
    render(withProviders(<ParentResourcesPage />))
    fireEvent.click(await screen.findByTestId('enter-handout-mode', undefined, { timeout: 5000 }))
    await screen.findByTestId('handout-toolbar', undefined, { timeout: 5000 })

    // Uncheck item 11; the row containing it should pick up print:hidden.
    fireEvent.click(screen.getByTestId('handout-item-checkbox-11'))
    const item11Row = screen
      .getByTestId('handout-item-checkbox-11')
      .closest('[data-handout-item]')
    expect(item11Row?.className).toContain('print:hidden')
    // Item 12 stays selected -- no print:hidden on its row.
    const item12Row = screen
      .getByTestId('handout-item-checkbox-12')
      .closest('[data-handout-item]')
    expect(item12Row?.className).not.toContain('print:hidden')
  })
})
