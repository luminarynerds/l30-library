/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for CatalogSearchPanel — locks down behavior preserved by the
 * HeaderSearch split (PR #753): trigram suggestion render, click-to-navigate,
 * combobox ArrowUp/ArrowDown active index, and the "Search catalog for X" CTA.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '../../../__tests__/utils/test-utils'

const mocks = vi.hoisted(() => ({
  getSearchSuggestions: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('../../../api/pg-search-api', () => ({
  getSearchSuggestions: mocks.getSearchSuggestions,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mocks.navigate }
})

import CatalogSearchPanel from '../CatalogSearchPanel'

const noop = () => {}

function renderPanel(props: Partial<React.ComponentProps<typeof CatalogSearchPanel>> = {}) {
  const defaults: React.ComponentProps<typeof CatalogSearchPanel> = {
    query: 'harry',
    facetFilter: null,
    setFacetFilter: noop,
    onClose: noop,
    onClearQuery: noop,
    onConsumeQuery: noop,
    saveRecentSearch: noop,
  }
  return render(
    <MemoryRouter>
      <CatalogSearchPanel {...defaults} {...props} />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  mocks.getSearchSuggestions.mockReset()
  mocks.navigate.mockReset()
})

describe('CatalogSearchPanel', () => {
  it('renders trigram suggestions returned by the API', async () => {
    mocks.getSearchSuggestions.mockResolvedValue({
      suggestions: [
        {
          id: 101,
          title: 'Harry Potter',
          author: 'J.K. Rowling',
          item_type: 'book',
          cover_url: null,
          is_available: true,
          similarity: 0.9,
          suggestion_type: 'title',
        },
        {
          id: null,
          title: 'Harriet Tubman',
          author: null,
          item_type: null,
          cover_url: null,
          is_available: null,
          similarity: 0.7,
          suggestion_type: 'author',
          book_count: 3,
        },
      ],
    })

    renderPanel({ query: 'harry' })

    expect(await screen.findByText('Harry Potter')).toBeInTheDocument()
    expect(screen.getByText('Harriet Tubman')).toBeInTheDocument()
    expect(screen.getByRole('listbox')).toBeInTheDocument()
    await waitFor(() => expect(mocks.getSearchSuggestions).toHaveBeenCalledWith('harry', 8))
  })

  it('navigates to /catalog/:id when a title suggestion is clicked', async () => {
    mocks.getSearchSuggestions.mockResolvedValue({
      suggestions: [
        {
          id: 42,
          title: 'Dune',
          author: 'Frank Herbert',
          item_type: 'book',
          cover_url: null,
          is_available: true,
          similarity: 0.95,
          suggestion_type: 'title',
        },
      ],
    })
    const onConsumeQuery = vi.fn()
    const onClose = vi.fn()

    renderPanel({ query: 'dune', onConsumeQuery, onClose })

    const button = await screen.findByRole('button', { name: /Dune/ })
    await userEvent.click(button)

    expect(mocks.navigate).toHaveBeenCalledWith('/catalog/42')
    expect(onConsumeQuery).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('moves active option with ArrowDown / ArrowUp via the registered key handler', async () => {
    mocks.getSearchSuggestions.mockResolvedValue({
      suggestions: [
        { id: 1, title: 'Alpha', author: null, item_type: null, cover_url: null, is_available: null, similarity: 1, suggestion_type: 'title' },
        { id: 2, title: 'Beta', author: null, item_type: null, cover_url: null, is_available: null, similarity: 0.9, suggestion_type: 'title' },
        { id: 3, title: 'Gamma', author: null, item_type: null, cover_url: null, is_available: null, similarity: 0.8, suggestion_type: 'title' },
      ],
    })

    let registered: ((e: React.KeyboardEvent<HTMLInputElement>) => void) | null = null
    const registerKeyHandler = (h: typeof registered) => { registered = h }

    renderPanel({ query: 'al', registerKeyHandler })

    await screen.findByText('Alpha')
    await waitFor(() => expect(registered).not.toBeNull())

    const options = () => screen.getAllByRole('option')
    expect(options().every((opt) => opt.getAttribute('aria-selected') === 'false')).toBe(true)

    const fakeEvent = (key: string) => ({ key, preventDefault: vi.fn() }) as unknown as React.KeyboardEvent<HTMLInputElement>

    registered!(fakeEvent('ArrowDown'))
    await waitFor(() => expect(options()[0]!.getAttribute('aria-selected')).toBe('true'))

    registered!(fakeEvent('ArrowDown'))
    await waitFor(() => expect(options()[1]!.getAttribute('aria-selected')).toBe('true'))

    registered!(fakeEvent('ArrowUp'))
    await waitFor(() => expect(options()[0]!.getAttribute('aria-selected')).toBe('true'))

    // ArrowUp from index 0 wraps to last
    registered!(fakeEvent('ArrowUp'))
    await waitFor(() => expect(options()[2]!.getAttribute('aria-selected')).toBe('true'))
  })

  it('fires the "Search catalog for X" CTA and navigates with the query', async () => {
    mocks.getSearchSuggestions.mockResolvedValue({ suggestions: [] })

    const onConsumeQuery = vi.fn()
    const saveRecentSearch = vi.fn()
    renderPanel({ query: 'beekeeping', onConsumeQuery, saveRecentSearch })

    const cta = await screen.findByRole('button', { name: /Search catalog for/i })
    fireEvent.click(cta)

    expect(saveRecentSearch).toHaveBeenCalledWith('beekeeping')
    expect(mocks.navigate).toHaveBeenCalledWith('/catalog?q=beekeeping')
    expect(onConsumeQuery).toHaveBeenCalled()
  })

  it('includes facetFilter as item_type in the CTA navigation when set', async () => {
    mocks.getSearchSuggestions.mockResolvedValue({ suggestions: [] })
    renderPanel({ query: 'kafka', facetFilter: 'book' })

    const cta = await screen.findByRole('button', { name: /Search catalog for/i })
    fireEvent.click(cta)

    expect(mocks.navigate).toHaveBeenCalledWith('/catalog?q=kafka&item_type=book')
  })
})
