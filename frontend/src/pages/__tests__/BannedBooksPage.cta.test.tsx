/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Locks the hero "Browse Banned Books in Our Catalog" CTA, the ALA
 * Frequently-Challenged outbound link, the per-challenge-story "View in
 * Catalog" deep-link (rendered only when catalog_item_id is non-null), and
 * the Banned Books Week signup CTA. These selling-to-checkout entry points
 * are the conversion path the audit (E2) flagged as missing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
// tsc-files (pre-commit) type-checks this file in isolation and doesn't see
// vitest's global setupFiles, so toHaveAttribute needs this import directly
// (see BannedBooksPage.test.tsx, the first file here to hit this).
import '@testing-library/jest-dom'

// ---- Mocks --------------------------------------------------------------

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string | Record<string, unknown>) => typeof fallback === 'string' ? fallback : _key,
  }),
}))

const { getPublicChallengesMock, getPublicStatsMock, getResourcesMock, submitMock, getReadingProgramsMock } = vi.hoisted(() => ({
  getPublicChallengesMock: vi.fn(),
  getPublicStatsMock: vi.fn(),
  getResourcesMock: vi.fn(),
  submitMock: vi.fn(),
  getReadingProgramsMock: vi.fn(),
}))

const { CHALLENGE_OUTCOME_LABELS, CHALLENGE_REASON_LABELS } = vi.hoisted(() => ({
  CHALLENGE_OUTCOME_LABELS: {
    retained: 'Retained',
    retained_with_changes: 'Retained with changes',
    removed: 'Removed',
    restricted: 'Restricted',
    withdrawn: 'Withdrawn',
    pending: 'Pending',
  },
  CHALLENGE_REASON_LABELS: {
    other: 'Other',
    sexual_content: 'Sexual content',
  },
}))

vi.mock('../../api/api', () => ({
  getPublicChallenges: getPublicChallengesMock,
  getPublicStats: getPublicStatsMock,
  getIntellectualFreedomResources: getResourcesMock,
  submitReconsiderationRequest: submitMock,
  getReadingPrograms: getReadingProgramsMock,
  CHALLENGE_OUTCOME_LABELS,
  CHALLENGE_REASON_LABELS,
}))

// TransparencyLog (rendered by BannedBooksPage) imports getPublicChallenges/
// getPublicStats directly from the domain module rather than through the
// '../../api/api' barrel above -- mock that path too, or TransparencyLog's
// queries hit the real (server-less) implementation and it renders its own
// error state instead of the story list.
vi.mock('../../api/domains/content/book-challenges-api', () => ({
  getPublicChallenges: getPublicChallengesMock,
  getPublicStats: getPublicStatsMock,
  CHALLENGE_OUTCOME_LABELS,
  CHALLENGE_REASON_LABELS,
}))

// ---- Fixtures -----------------------------------------------------------

import BannedBooksPage from '../BannedBooksPage'

function makeChallenge(overrides: Partial<{ id: number; catalog_item_id: number | null }> = {}) {
  return {
    id: 1,
    catalog_item_id: null,
    public_title: 'Test Challenge',
    title: 'Test Challenge',
    author: 'Test Author',
    primary_reason: 'other',
    outcome: 'retained',
    public_summary: null,
    lessons_learned: null,
    date_received: '2026-01-01',
    date_resolved: null,
    ...overrides,
  }
}

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

// ---- Tests --------------------------------------------------------------

describe('BannedBooksPage E2 CTA wiring', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: no challenges, no stats, no resources -- isolates the
    // catalog-CTA + BBW assertions from the data-driven sections. The
    // seeded Banned Books Week program IS present by default so the two
    // CTAs below resolve to the filtered programs URL; the fallback test
    // overrides this to an empty list.
    getPublicChallengesMock.mockResolvedValue([])
    getPublicStatsMock.mockResolvedValue(null)
    getResourcesMock.mockResolvedValue([])
    getReadingProgramsMock.mockResolvedValue([{ id: 1, name: 'Banned Books Week 2026' }])
  })

  it('shows announced 2027 dates without carrying over the 2026 theme or action day', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 12))
    try {
      render(wrap(<BannedBooksPage />))
      expect(await screen.findByText('October 3-9, 2027')).toBeInTheDocument()
      expect(screen.queryByText(/Let Books Be\. Protect the Freedom to Read\./)).not.toBeInTheDocument()
      expect(screen.queryByText('bannedBooks.freedomReadDayX')).not.toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })

  it('points the hero "Browse Banned Books in Our Catalog" CTA at a catalog search for the curated titles', () => {
    // Was /catalog?subject=banned+books -- no "banned books" subject facet
    // exists in the catalog (0 results live), so it pointed nowhere. The
    // curated program titles are combined with the catalog's supported
    // quoted-phrase OR syntax so the destination remains the catalog.
    render(wrap(<BannedBooksPage />))
    const link = screen.getByRole('link', { name: /Browse Banned Books in Our Catalog/i })
    expect(link.getAttribute('href')).toMatch(/^\/catalog\?q=/)
    const query = new URLSearchParams(link.getAttribute('href')?.split('?')[1]).get('q')
    expect(query).toContain('"Adventures of Huckleberry Finn"')
    expect(query).toContain('"Uncle Tom\'s Cabin"')
  })

  it('renders the ALA frequently-challenged outbound link with safe target attrs', () => {
    render(wrap(<BannedBooksPage />))
    const link = screen.getByRole('link', { name: /View Frequently Challenged Books \(ALA\)/i })
    expect(link).toBeTruthy()
    // Task 2 repointed the page at the live ALA URL (the old
    // /advocacy/bbooks/frequentlychallengedbooks path 404s) but only
    // updated BannedBooksPage.test.tsx's assertion, not this file's.
    expect(link.getAttribute('href')).toBe(
      'https://www.ala.org/bbooks/frequentlychallengedbooks/top10',
    )
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('points the "Join Banned Books Week" CTA at the programs list filtered to the seeded program', async () => {
    // Was /programs?q=banned+books+week -- no program matched that query
    // string against the seeded name "Banned Books Week 2026" (ReadingProgramsPage's
    // filter is a client-side case-insensitive substring match on name/description,
    // see src/pages/ReadingProgramsPage.tsx:97-100, so casing alone wasn't the
    // bug, but the link is corrected to match the real program name anyway).
    render(wrap(<BannedBooksPage />))
    await waitFor(() => {
      const joinLink = screen.getByRole('link', { name: /Join Banned Books Week/i })
      expect(joinLink).toHaveAttribute('href', '/programs?q=Banned+Books+Week')
    })
  })

  it('falls back to the plain programs list when no BBW program exists (unseeded fork)', async () => {
    getReadingProgramsMock.mockResolvedValue([])
    render(wrap(<BannedBooksPage />))
    await waitFor(() => {
      const joinLink = screen.getByRole('link', { name: /Join Banned Books Week/i })
      expect(joinLink).toHaveAttribute('href', '/programs')
    })
    const browseLink = screen.getByRole('link', { name: /Browse Banned Books in Our Catalog/i })
    expect(browseLink.getAttribute('href')).toMatch(/^\/catalog\?q=/)
  })

  it('falls back to the plain programs list when the BBW program exists but has been deactivated', async () => {
    // ReadingProgramsPage.tsx:26 defaults to { active_only: true }, so a
    // deactivated program (is_active is real and staff-toggleable, see
    // reading-programs-api.ts:20) is invisible at the destination even
    // though it still exists. The probe now asks the same question
    // (BannedBooksPage.tsx:73: getReadingPrograms({ active_only: true })),
    // so this mock -- like a real API -- only returns the program on an
    // unfiltered call. Without the fix, the probe called
    // getReadingPrograms() with no filters, matched the deactivated
    // program anyway, and pointed both CTAs at
    // /programs?q=Banned+Books+Week -- a query the destination then
    // filters to zero results.
    getReadingProgramsMock.mockImplementation(async (filters?: { active_only?: boolean }) =>
      filters?.active_only ? [] : [{ id: 1, name: 'Banned Books Week 2026', is_active: false }]
    )
    render(wrap(<BannedBooksPage />))
    await waitFor(() => expect(getReadingProgramsMock).toHaveBeenCalledWith({ active_only: true }))
    // The fallback href ('/programs') is identical during the initial
    // pre-fetch render and after a correctly-filtered empty resolution, so
    // polling the DOM alone can't tell "never checked" from "checked and
    // filtered out." Explicitly await the exact call's resolved promise
    // inside act() so React Query's state update is flushed before the
    // assertion runs, instead of relying on waitFor happening to poll after
    // that has already occurred.
    const activeOnlyCallIndex = getReadingProgramsMock.mock.calls.findIndex(
      (args) => (args[0] as { active_only?: boolean } | undefined)?.active_only === true
    )
    expect(activeOnlyCallIndex).toBeGreaterThan(-1)
    await act(async () => {
      await getReadingProgramsMock.mock.results[activeOnlyCallIndex]?.value
    })
    const joinLink = screen.getByRole('link', { name: /Join Banned Books Week/i })
    expect(joinLink).toHaveAttribute('href', '/programs')
    const browseLink = screen.getByRole('link', { name: /Browse Banned Books in Our Catalog/i })
    expect(browseLink.getAttribute('href')).toMatch(/^\/catalog\?q=/)
  })

  it('renders "View in Catalog" link on challenge stories when catalog_item_id is set', async () => {
    // getPublicChallenges({query}) -- the shape TransparencyLog (which now
    // renders the story list, see BannedBooksPage.tsx) calls it with --
    // resolves the paginated BookChallengePublicListResponse, not a bare
    // array. See [[project_l30_walkthrough_fixes... TransparencyLog extraction]].
    //
    // TransparencyLog.tsx:256-259 renders this Link when catalog_item_id is
    // non-null (`to={`/catalog/${challenge.catalog_item_id}`}`).
    getPublicChallengesMock.mockResolvedValue({
      items: [makeChallenge({ id: 7, catalog_item_id: 42 })],
      total: 1,
      page: 1,
      per_page: 10,
      pages: 1,
    })
    render(wrap(<BannedBooksPage />))
    const viewLink = await screen.findByRole('link', { name: /View in Catalog/i })
    expect(viewLink.getAttribute('href')).toBe('/catalog/42')
  })

  it('hides "View in Catalog" link when catalog_item_id is null', async () => {
    getPublicChallengesMock.mockResolvedValue({
      items: [makeChallenge({ id: 8, catalog_item_id: null })],
      total: 1,
      page: 1,
      per_page: 10,
      pages: 1,
    })
    render(wrap(<BannedBooksPage />))
    // Wait for the story card to render at all.
    await screen.findByText(/Test Challenge/i)
    expect(screen.queryByRole('link', { name: /View in Catalog/i })).toBeNull()
  })
})
