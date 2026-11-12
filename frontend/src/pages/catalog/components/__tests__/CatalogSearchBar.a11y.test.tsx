/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Combobox semantics: the search input must expose aria-activedescendant
 * pointing at the highlighted option, and aria-controls must only reference
 * the listbox while it is actually rendered.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import CatalogSearchBar from '../CatalogSearchBar'
import type { SearchSuggestion } from '@/api/pg-search-api'

vi.mock('@/api/domains/catalog/catalog-api', () => ({
  getRandomItem: vi.fn(),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en',
    t: (key: string, fallback?: string | Record<string, unknown>) =>
      typeof fallback === 'string' ? fallback : key,
  }),
}))

const SUGGESTIONS: SearchSuggestion[] = [
  { title: 'Harry Potter', author: 'Rowling', suggestion_type: 'title' },
  { title: 'Harriet the Spy', author: 'Fitzhugh', suggestion_type: 'title' },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
] as any

function renderBar(overrides: Partial<React.ComponentProps<typeof CatalogSearchBar>> = {}) {
  const props: React.ComponentProps<typeof CatalogSearchBar> = {
    searchQuery: 'har',
    onSearchChange: vi.fn(),
    onSubmit: vi.fn(),
    onClearSearch: vi.fn(),
    suggestions: SUGGESTIONS,
    showSuggestions: true,
    onShowSuggestionsChange: vi.fn(),
    selectedSuggestionIndex: -1,
    onSelectedSuggestionIndexChange: vi.fn(),
    onSuggestionSelect: vi.fn(),
    searchInputRef: React.createRef<HTMLInputElement>() as React.RefObject<HTMLInputElement>,
    suggestionsRef: React.createRef<HTMLDivElement>() as React.RefObject<HTMLDivElement>,
    isLoading: false,
    reduceMotion: true,
    ...overrides,
  }
  return render(
    <MemoryRouter>
      <CatalogSearchBar {...props} />
    </MemoryRouter>,
  )
}

describe('CatalogSearchBar — combobox activedescendant wiring', () => {
  it('gives options stable ids and points aria-activedescendant at the highlighted one', () => {
    renderBar({ selectedSuggestionIndex: 1 })

    const input = screen.getByRole('combobox')
    expect(input).toHaveAttribute('aria-activedescendant', 'catalog-suggestion-1')
    expect(input).toHaveAttribute('aria-controls', 'catalog-suggestions')
    expect(input).toHaveAttribute('aria-expanded', 'true')

    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('id', 'catalog-suggestion-0')
    expect(options[1]).toHaveAttribute('id', 'catalog-suggestion-1')
    expect(options[1]).toHaveAttribute('aria-selected', 'true')
    expect(options[0]).toHaveAttribute('aria-selected', 'false')
  })

  it('omits aria-activedescendant when nothing is highlighted', () => {
    renderBar({ selectedSuggestionIndex: -1 })

    const input = screen.getByRole('combobox')
    expect(input).not.toHaveAttribute('aria-activedescendant')
    expect(input).toHaveAttribute('aria-controls', 'catalog-suggestions')
  })

  it('omits aria-controls and aria-activedescendant when the list is closed', () => {
    renderBar({ showSuggestions: false, selectedSuggestionIndex: 1 })

    const input = screen.getByRole('combobox')
    expect(input).not.toHaveAttribute('aria-controls')
    expect(input).not.toHaveAttribute('aria-activedescendant')
    expect(input).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
