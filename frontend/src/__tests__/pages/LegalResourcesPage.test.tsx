/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, userEvent } from '../utils/test-utils'
import LegalResourcesPage from '@/pages/LegalResourcesPage'
import * as legalApi from '@/api/legal-api'

vi.mock('@/api/legal-api')

// Minimal fixtures — only the fields the page + tab components read.
// Cast through `unknown` so we don't need to satisfy every optional
// field in the schema (the page only renders a handful).
const mockTopics = [
  { id: 1, slug: 'housing', name: 'Housing', is_active: true },
  { id: 2, slug: 'family', name: 'Family', is_active: true },
] as unknown as legalApi.LegalTopic[]

const mockProviders = [
  {
    id: 10,
    name: 'Acme Legal Aid',
    phone: '555-1234',
    city: 'Anytown',
    state: 'OH',
    virtual_services: false,
  },
] as unknown as legalApi.LegalProviderSummary[]

describe('LegalResourcesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // jsdom doesn't implement scrollIntoView; stub so wizard jump
    // can run without throwing.
    Element.prototype.scrollIntoView = vi.fn()
    // Also clear any wizard-dismissed state from a prior test (the
    // wizard reads localStorage to decide whether to render).
    localStorage.clear()

    vi.mocked(legalApi.getLegalTopics).mockResolvedValue({
      topics: mockTopics,
      total: mockTopics.length,
      limit: 50,
      offset: 0,
    })
    vi.mocked(legalApi.getLegalGuides).mockResolvedValue({
      guides: [],
      total: 0,
      limit: 20,
      offset: 0,
    })
    vi.mocked(legalApi.getLegalForms).mockResolvedValue({
      forms: [],
      total: 0,
      limit: 50,
      offset: 0,
    })
    vi.mocked(legalApi.getUpcomingLegalClinics).mockResolvedValue([])
    vi.mocked(legalApi.getLegalProviders).mockResolvedValue({
      providers: mockProviders,
      total: mockProviders.length,
      limit: 20,
      offset: 0,
    })
    vi.mocked(legalApi.getLegalCollections).mockResolvedValue({
      collections: [],
      total: 0,
      limit: 10,
      offset: 0,
    })
    vi.mocked(legalApi.getLegalFormPackets).mockResolvedValue({
      packets: [],
      total: 0,
      limit: 50,
      offset: 0,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ============================================================
  // I1 — Tabs are gone; sections are always visible.
  // ============================================================
  describe('I1 — no tablist, stacked sections', () => {
    it('does not render a tablist (4-tab structure is gone)', async () => {
      render(<LegalResourcesPage />)
      // Wait for the page to settle (h1 from StandardPageLayout).
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      expect(screen.queryByRole('tablist')).toBeNull()
      // No leftover role=tab buttons either.
      expect(screen.queryByRole('tab')).toBeNull()
      // No leftover role=tabpanel wrappers.
      expect(screen.queryByRole('tabpanel')).toBeNull()
    })

    it('renders all four sections as regions, each with its own <h2>', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })

      // Each section is an aria-labelledby region with its h2.
      const headings = await screen.findAllByRole('heading', { level: 2 })
      const headingTexts = headings.map((h) => h.textContent?.trim())
      expect(headingTexts).toEqual(
        expect.arrayContaining([
          'Legal Resources',
          'Free Legal Clinics',
          'Common Forms',
          'Online Privacy & Removal',
        ]),
      )

      // The sections themselves are rendered as <region> landmarks
      // (aria-labelledby gives them an accessible name).
      const regions = screen.getAllByRole('region')
      const regionNames = regions.map((r) => r.getAttribute('aria-labelledby'))
      expect(regionNames).toEqual(
        expect.arrayContaining([
          'legal-resources-heading',
          'legal-clinics-heading',
          'legal-forms-heading',
          'legal-privacy-heading',
        ]),
      )
    })

    it('renders sections in the documented top-to-bottom order: Resources, Clinics, Forms, Privacy', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })

      const resources = screen.getByRole('heading', { level: 2, name: 'Legal Resources' })
      const clinics = screen.getByRole('heading', { level: 2, name: 'Free Legal Clinics' })
      const forms = screen.getByRole('heading', { level: 2, name: 'Common Forms' })
      const privacy = screen.getByRole('heading', { level: 2, name: 'Online Privacy & Removal' })

      // DOCUMENT_POSITION_FOLLOWING = 4
      expect(resources.compareDocumentPosition(clinics) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
      expect(clinics.compareDocumentPosition(forms) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
      expect(forms.compareDocumentPosition(privacy) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    })
  })

  // ============================================================
  // I5 — Plain-language hero via StandardPageLayout.
  // ============================================================
  describe('I5 — plain-language hero', () => {
    it('uses the new "Legal Help" hero title (not "Legal Resource Center")', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      // Old title is gone everywhere on the page.
      expect(screen.queryByText(/Legal Resource Center/i)).toBeNull()
    })
  })

  // ============================================================
  // E2/E5 — Wizard jump: scroll + focus the target section,
  //          and announce via aria-live.
  // ============================================================
  describe('wizard jump-to-section', () => {
    it('focuses the matching <h2> and announces when the wizard jumps to clinics', async () => {
      const user = userEvent.setup()
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })

      // Drive the wizard: topic -> "I'm not sure" -> "I'm researching"
      // -> Find a free legal clinic. This goes through handleGoToClinics,
      // which calls onJumpToSection('clinics').
      const wizardSkipTopic = await screen.findByRole('button', { name: /I'm not sure/i })
      await user.click(wizardSkipTopic)

      const researchingBtn = await screen.findByRole('button', { name: /I'm researching/i })
      await user.click(researchingBtn)

      const findClinicBtn = await screen.findByRole('button', { name: /Find a free legal clinic/i })
      await user.click(findClinicBtn)

      // Section heading received focus.
      const clinicsHeading = screen.getByRole('heading', { level: 2, name: 'Free Legal Clinics' })
      await waitFor(() => expect(clinicsHeading).toHaveFocus())

      // aria-live status region announced the jump.
      await waitFor(() => {
        const status = screen.getByTestId('legal-jump-announcement')
        expect(status).toHaveAttribute('aria-live', 'polite')
        expect(status).toHaveTextContent(/Jumped to Free Legal Clinics/i)
      })
    })

    it('focuses the resources <h2> when the wizard jumps to resources', async () => {
      const user = userEvent.setup()
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })

      const wizardSkipTopic = await screen.findByRole('button', { name: /I'm not sure/i })
      await user.click(wizardSkipTopic)
      const researchingBtn = await screen.findByRole('button', { name: /I'm researching/i })
      await user.click(researchingBtn)

      const browseAllBtn = await screen.findByRole('button', { name: /Browse all resources/i })
      await user.click(browseAllBtn)

      const resourcesHeading = screen.getByRole('heading', { level: 2, name: 'Legal Resources' })
      await waitFor(() => expect(resourcesHeading).toHaveFocus())
      await waitFor(() => {
        expect(screen.getByTestId('legal-jump-announcement')).toHaveTextContent(
          /Jumped to Legal Resources/i,
        )
      })
    })

    it('all four section <h2>s have tabIndex=-1 so they can receive programmatic focus', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      for (const name of [
        'Legal Resources',
        'Free Legal Clinics',
        'Common Forms',
        'Online Privacy & Removal',
      ]) {
        const h2 = screen.getByRole('heading', { level: 2, name })
        expect(h2).toHaveAttribute('tabindex', '-1')
      }
    })
  })

  // ============================================================
  // I4 — WCAG touch targets (spot check)
  // ============================================================
  describe('I4 — touch targets', () => {
    it('wizard topic option buttons have min-h-[44px]', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      // "I'm not sure" is only rendered inside the wizard step-1 grid;
      // safer than picking a topic name that also appears as a
      // ResourcesTab filter chip.
      const wizardOptBtn = await screen.findByRole('button', { name: /I'm not sure/i })
      expect(wizardOptBtn.className).toContain('min-h-[44px]')
    })

    it('clinics view-toggle buttons have min-h-[44px]', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      // 'List' is the icon-button label inside the always-visible Clinics section.
      const listBtn = await screen.findByRole('button', { name: /^List$/ })
      expect(listBtn.className).toContain('min-h-[44px]')
    })

    it('resources topic-filter chips have min-h-[44px]', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      // "All Topics" is the always-rendered chip in ResourcesTab.
      const allTopicsChip = await screen.findByRole('button', { name: /All Topics/i, pressed: true })
      expect(allTopicsChip.className).toContain('min-h-[44px]')
    })
  })

  // ============================================================
  // Tel-link accessible names
  // ============================================================
  describe('I4 — SR names for tel: links', () => {
    it('QuickAccessProviders phone link has a "Call <name>" aria-label', async () => {
      render(<LegalResourcesPage />)
      await screen.findByRole('heading', { level: 1, name: /Legal Help/i })
      // QuickAccess renders the first 4 providers; the mocked provider's
      // phone shows up with an aria-label override.
      const callLink = await screen.findByRole('link', {
        name: /Call Acme Legal Aid at 555-1234/i,
      })
      // Page normalizes the phone for href: strips everything except
      // digits + leading '+', so 555-1234 -> 5551234.
      expect(callLink).toHaveAttribute('href', 'tel:5551234')
    })
  })
})
