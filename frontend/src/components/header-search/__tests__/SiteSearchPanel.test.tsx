/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for SiteSearchPanel — locks down live site-search behavior preserved
 * by the HeaderSearch split (PR #753): results render, loading + no-match
 * states, CTA label toggling, and click-to-navigate via result.url.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { render, screen, waitFor } from '../../../__tests__/utils/test-utils'

const mocks = vi.hoisted(() => ({
  siteSearch: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('../../../api/site-search-api', () => ({
  siteSearch: mocks.siteSearch,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mocks.navigate }
})

import SiteSearchPanel from '../SiteSearchPanel'

const noop = () => {}

function renderPanel(props: Partial<React.ComponentProps<typeof SiteSearchPanel>> = {}) {
  const defaults: React.ComponentProps<typeof SiteSearchPanel> = {
    query: 'tax',
    onClose: noop,
    onClearQuery: noop,
    onConsumeQuery: noop,
    saveRecentSearch: noop,
  }
  return render(
    <MemoryRouter>
      <SiteSearchPanel {...defaults} {...props} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mocks.siteSearch.mockReset()
  mocks.navigate.mockReset()
})

describe('SiteSearchPanel', () => {
  it('renders live results when siteSearch returns items', async () => {
    mocks.siteSearch.mockResolvedValue({
      query: 'tax',
      total_results: 2,
      results: [
        { id: 'page-1', entity_type: 'page', title: 'Tax help', snippet: 'How to file', url: '/help/tax', score: 1, source: 'cms' },
        { id: 'evt-9', entity_type: 'event', title: 'Tax clinic', snippet: 'Free filing help', url: '/events/9', score: 0.9, source: 'events' },
      ],
      page: 1,
      per_page: 8,
      has_more: false,
    })

    renderPanel({ query: 'tax' })

    expect(await screen.findByText('Tax help')).toBeInTheDocument()
    expect(screen.getByText('Tax clinic')).toBeInTheDocument()
    await waitFor(() => expect(mocks.siteSearch).toHaveBeenCalledWith('tax', { perPage: 8 }))
  })

  it('shows the loading indicator while results are pending', async () => {
    let resolveIt: (value: unknown) => void = () => {}
    mocks.siteSearch.mockImplementation(() => new Promise((resolve) => { resolveIt = resolve }))

    renderPanel({ query: 'tax' })

    // Loading text appears after the 200ms debounce kicks the fetch.
    expect(await screen.findByText(/Loading suggestions/i)).toBeInTheDocument()

    // Resolve to clean up the in-flight promise.
    resolveIt({ query: 'tax', total_results: 0, results: [], page: 1, per_page: 8, has_more: false })
  })

  it('shows "no quick matches" copy when results are empty', async () => {
    mocks.siteSearch.mockResolvedValue({
      query: 'asdfqwerty',
      total_results: 0,
      results: [],
      page: 1,
      per_page: 8,
      has_more: false,
    })

    renderPanel({ query: 'asdfqwerty' })

    expect(await screen.findByText(/No quick matches/i)).toBeInTheDocument()
  })

  it('toggles CTA label between "See all results" / "Search site" based on result count', async () => {
    // Case 1: with results -> "See all results for"
    mocks.siteSearch.mockResolvedValueOnce({
      query: 'tax',
      total_results: 1,
      results: [{ id: 'p1', entity_type: 'page', title: 'Tax help', snippet: null, url: '/help/tax', score: 1, source: 'cms' }],
      page: 1, per_page: 8, has_more: false,
    })
    const { unmount } = renderPanel({ query: 'tax' })
    expect(await screen.findByRole('button', { name: /See all results for/i })).toBeInTheDocument()
    unmount()

    // Case 2: no results -> "Search site for"
    mocks.siteSearch.mockResolvedValueOnce({
      query: 'zzz', total_results: 0, results: [], page: 1, per_page: 8, has_more: false,
    })
    renderPanel({ query: 'zzz' })
    expect(await screen.findByRole('button', { name: /Search site for/i })).toBeInTheDocument()
  })

  it('navigates to result.url when a result is clicked', async () => {
    mocks.siteSearch.mockResolvedValue({
      query: 'tax',
      total_results: 1,
      results: [{ id: 'evt-9', entity_type: 'event', title: 'Tax clinic', snippet: null, url: '/events/9', score: 1, source: 'events' }],
      page: 1, per_page: 8, has_more: false,
    })
    const onConsumeQuery = vi.fn()
    const onClose = vi.fn()

    renderPanel({ query: 'tax', onConsumeQuery, onClose })

    const item = await screen.findByRole('button', { name: /Tax clinic/i })
    await userEvent.click(item)

    expect(mocks.navigate).toHaveBeenCalledWith('/events/9')
    expect(onConsumeQuery).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })
})
