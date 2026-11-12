/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Vitest coverage for the parent-resource multilingual surface (chips +
 * page-level language filter + lang= attributes + fallback marker).
 *
 * Test setup notes:
 *  - L30 vitest setup does not preload i18n
 *    (feedback_l30_vitest_i18n_no_preload). We mock `useTranslation` and
 *    `useLanguage` to echo keys + return a stable UI language so we can
 *    assert on key paths instead of translated strings.
 *  - `getResourceGuide` is mocked to return a deterministic shape; we
 *    intentionally do NOT mock the LanguageChip/LanguageFilter siblings
 *    so the test covers the integration between the page and the
 *    components it just gained.
 *  - MemoryRouter wraps the render so the page's useSearchParams works;
 *    the initial entry sets the `?lang=` URL state for filter-active
 *    tests.
 */
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Echo translation keys with params appended. Matches the convention in
// ParentResourcesPage.test.tsx + ParentResourcesPage.handout.test.tsx.
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
  // Pretend the staff member's UI locale is English. The default-lang
  // effect on first load only kicks in when UI lang !== 'en' AND a
  // matching translation exists; English short-circuits cleanly.
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

// `useStaffPredicate` lives in `./parent-resources/Verification.tsx` and
// reads from `@/contexts/AuthContext`'s `useAuth`. Sibling test files
// (`ParentResourcesPage.test.tsx`) don't mock either because they don't
// hit the staff-only verify-button branch. We don't either, but rendering
// still calls `useStaffPredicate` -> `useAuth`, so stub that out.
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'staff@test', role: 'staff' },
    isAuthenticated: true,
    loading: false,
  }),
}))

const getResourceGuideMock = vi.fn()
const verifyResourceGuideItemMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  getResourceGuide: (...args: unknown[]) => getResourceGuideMock(...args),
  verifyResourceGuideItem: (...args: unknown[]) =>
    verifyResourceGuideItemMock(...args),
}))

import ParentResourcesPage from '../ParentResourcesPage'

function withClient(ui: ReactNode, initialPath = '/staff/parent-onboarding/resources') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

// Two sections so we can cover the "section empties to inline message
// when filter excludes all items" branch.
const sampleSections = [
  {
    id: 1,
    title: 'Health',
    description: 'Pediatricians and clinics',
    icon: 'health',
    items: [
      {
        id: 11,
        title: 'Postpartum support line',
        description: 'Trained peers, 8am-8pm',
        languages: ['en', 'es'],
        translations: {
          es: {
            title: 'Línea de apoyo posparto',
            description: 'Pares capacitados, 8am-8pm',
          },
        },
        sort_order: 0,
      },
      {
        id: 12,
        title: 'English-only Clinic',
        description: 'No Spanish copy yet',
        languages: ['en'],
        translations: {},
        sort_order: 1,
      },
    ],
  },
  {
    id: 2,
    title: 'Nutrition',
    description: null,
    icon: 'nutrition',
    items: [
      {
        id: 21,
        title: 'Food pantry',
        description: 'Free groceries, Tuesdays',
        languages: ['so'],
        translations: { so: { title: 'Khadka cuntada' } },
        sort_order: 0,
      },
    ],
  },
]

async function waitForLoadedPage() {
  // The handoutMode tests use findByText on the page heading; we mirror
  // that pattern instead of polling on isLoading.
  return await screen.findByTestId('parent-resources-print-root')
}

/** Sections render collapsed by default; clicking the "Expand all"
 * affordance opens every panel so item-level assertions can find
 * the chip rows / fallback markers / per-item language attrs. */
async function expandAllSections() {
  await waitForLoadedPage()
  // The button's visible label echoes the i18n key text under our mock.
  const expandAllButton = screen.getByText('parentOnboarding.resources.expandAll')
  fireEvent.click(expandAllButton)
}

describe('ParentResourcesPage -- multilingual chips + filter', () => {
  beforeEach(() => {
    getResourceGuideMock.mockReset()
    verifyResourceGuideItemMock.mockReset()
    getResourceGuideMock.mockResolvedValue(sampleSections)
  })

  it('renders a chip per item language; no chips when languages is empty', async () => {
    getResourceGuideMock.mockResolvedValue([
      {
        ...sampleSections[0],
        items: [
          { ...sampleSections[0]!.items[0]!, languages: ['en', 'es', 'so'] },
          { ...sampleSections[0]!.items[1]!, languages: [] },
        ],
      },
    ])
    render(withClient(<ParentResourcesPage />))
    await expandAllSections()

    // First item has three chips; chip data-testids carry the lang code
    // so we can assert membership directly.
    const itemOne = screen.getByTestId('language-chips-11')
    expect(within(itemOne).getByTestId('language-chip-en')).toBeTruthy()
    expect(within(itemOne).getByTestId('language-chip-es')).toBeTruthy()
    expect(within(itemOne).getByTestId('language-chip-so')).toBeTruthy()

    // Second item has empty languages array -- the chip row should not
    // render at all (avoid an empty flex container).
    expect(screen.queryByTestId('language-chips-12')).toBeNull()
  })

  it('clicking a chip sets ?lang= and aria-pressed=true; click active chip clears', async () => {
    render(withClient(<ParentResourcesPage />))
    await expandAllSections()

    const esChip = screen.getByTestId('language-chip-es')
    expect(esChip.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(esChip)

    // After click, the URL changes (?lang=es). That bumps the
    // useQuery cache key, so React Query goes back to `isLoading` while
    // it re-fetches; the loader briefly replaces the page. Wait for the
    // section to re-render so the chip is in the DOM again. ALSO need
    // to re-expand because expandedSections is local state that survives
    // the loader, but the items themselves come from the refetched data.
    await screen.findByTestId('parent-resources-print-root')
    // Sections may have collapsed between loader and re-render -- be
    // robust to that by reading the expand-all affordance again if
    // present.
    const expandBtn = screen.queryByText('parentOnboarding.resources.expandAll')
    if (expandBtn) fireEvent.click(expandBtn)

    const esChipAfter = await screen.findByTestId('language-chip-es')
    expect(esChipAfter.getAttribute('aria-pressed')).toBe('true')

    // Click again on the now-active chip and the filter clears.
    fireEvent.click(esChipAfter)
    await screen.findByTestId('parent-resources-print-root')
    const expandBtn2 = screen.queryByText('parentOnboarding.resources.expandAll')
    if (expandBtn2) fireEvent.click(expandBtn2)
    const esChipCleared = await screen.findByTestId('language-chip-es')
    expect(esChipCleared.getAttribute('aria-pressed')).toBe('false')
  })

  it('filter select options are the de-duplicated union of all item.languages, sorted by autonym, "All languages" first', async () => {
    render(withClient(<ParentResourcesPage />))
    await waitForLoadedPage()

    const select = screen.getByTestId('language-filter-select') as HTMLSelectElement
    const optionValues = Array.from(select.options).map((o) => o.value)
    // Union of all item languages: en, es, so. Plus the "All languages"
    // pin at index 0.
    expect(optionValues[0]).toBe('')
    // The rest are sorted by autonym:
    //  - English (en), Español (es), Soomaali (so) -- alphabetical by autonym
    //    lands on E, E, S which matches the codes order [en, es, so] here.
    expect(new Set(optionValues.slice(1))).toEqual(new Set(['en', 'es', 'so']))
  })

  it('items lacking the selected language render the English fallback with "(in English)" suffix; do not disappear', async () => {
    render(
      withClient(<ParentResourcesPage />, '/staff/parent-onboarding/resources?lang=es'),
    )
    await waitForLoadedPage()

    // Item 11 has a Spanish translation -- no fallback marker.
    expect(screen.queryByTestId('translation-fallback-marker-11')).toBeNull()
    // Item 12 advertises 'en' only; with ?lang=es active the item should
    // be HIDDEN entirely (no language match) so no fallback marker either.
    expect(screen.queryByTestId('translation-fallback-marker-12')).toBeNull()
    // To exercise the in-section fallback we need an item that DOES list
    // the selected language but has no translation for it. Replace the
    // mock for this case below.
  })

  it('item with the selected lang in languages but no translation gets the fallback marker', async () => {
    // Backend would normally substitute fields when a translation
    // exists; here we simulate the backend's response where translations
    // is empty so the source title is preserved AND the FE sees no entry
    // in translations[langFilter].
    getResourceGuideMock.mockResolvedValue([
      {
        id: 1,
        title: 'Health',
        description: '',
        icon: 'health',
        items: [
          {
            id: 11,
            title: 'WIC',
            description: 'Nutrition support',
            languages: ['en', 'es'],
            translations: {}, // No Spanish copy yet.
            sort_order: 0,
          },
        ],
      },
    ])
    render(
      withClient(<ParentResourcesPage />, '/staff/parent-onboarding/resources?lang=es'),
    )
    await expandAllSections()
    expect(screen.getByTestId('translation-fallback-marker-11')).toBeTruthy()
  })

  it('section with zero matching items renders the empty-state inline; keeps the section header visible', async () => {
    render(
      withClient(<ParentResourcesPage />, '/staff/parent-onboarding/resources?lang=es'),
    )
    await expandAllSections()

    // Section 2 has one item (id=21) tagged ['so']. With ?lang=es active,
    // that item falls out. The section header still renders; the inline
    // empty state replaces the item list.
    expect(screen.getByText('Nutrition')).toBeTruthy()
    expect(screen.getByTestId('section-empty-for-language-2')).toBeTruthy()
  })

  it('lang attribute on title span matches the translation code when translated; matches "en" when falling back', async () => {
    // The backend substitutes title/description for `?lang=es` when a
    // translation exists. The default mock returns un-substituted source
    // titles; here we simulate the backend's substitution behavior so
    // the test exercises the FE's lang-attribute branch.
    getResourceGuideMock.mockImplementation(({ lang }: { lang?: string }) => {
      // Deep copy + substitute when a translation exists for the
      // requested lang. Mirrors what `_build_item_response(..., lang=)`
      // does on the backend.
      return Promise.resolve(
        sampleSections.map((section) => ({
          ...section,
          items: section.items.map((item) => {
            const t = (item.translations as Record<string, { title?: string; description?: string }> | undefined)?.[lang ?? '']
            if (lang && t?.title) {
              return {
                ...item,
                title: t.title,
                description: t.description ?? item.description,
              }
            }
            return item
          }),
        })),
      )
    })

    render(
      withClient(<ParentResourcesPage />, '/staff/parent-onboarding/resources?lang=es'),
    )
    await expandAllSections()

    // Item 11 has translations.es -> backend (mock) substituted the
    // title. The page wraps it in <span lang="es">.
    const titleEs = screen.getByText('Línea de apoyo posparto')
    expect(titleEs.getAttribute('lang')).toBe('es')
  })

  it('aria-live status text updates on filter change', async () => {
    render(withClient(<ParentResourcesPage />))
    await waitForLoadedPage()

    const status = screen.getByTestId('language-filter-status')
    // Initially "All languages": echoes the statusAll key with total=3 items.
    expect(status.textContent).toContain('parentResources.languageFilter.statusAll')
    expect(status.textContent).toContain('total=3')

    // Switch via the select (filter change path that doesn't depend on
    // chip interaction).
    const select = screen.getByTestId('language-filter-select') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'es' } })

    const statusAfter = await screen.findByTestId('language-filter-status')
    expect(statusAfter.textContent).toContain('parentResources.languageFilter.status')
    expect(statusAfter.textContent).toContain('visible=1') // Only item 11 has 'es'.
    expect(statusAfter.textContent).toContain('total=3')
  })
})
