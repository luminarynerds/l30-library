/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Stub the I18nContext so we don't have to spin up Branding + i18n
// providers just to render a static filter section.
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
    language: 'en' as const,
    setLanguage: () => undefined,
    isRTL: false,
  }),
  I18nProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// LexileRangeFilter pulls in extra context; we don't render it (sidebar
// only renders it when onLexileChange is passed, so we just omit it).
vi.mock('@/components/LexileRangeFilter', () => ({
  LexileRangeFilter: () => null,
}))

import CatalogFilterSidebar from '../CatalogFilterSidebar'

function renderSidebar(overrides: Partial<React.ComponentProps<typeof CatalogFilterSidebar>> = {}) {
  const props: React.ComponentProps<typeof CatalogFilterSidebar> = {
    filters: {
      item_type: '',
      location: '',
      publisher: '',
      reading_time: '',
      access: '',
      topic: '',
      language: '',
      year_min: '',
      year_max: '',
    },
    showNewArrivals: false,
    showLargePrintOnly: false,
    availableNowOnly: false,
    availableForHold: false,
    onFilterChange: vi.fn(),
    onToggleNewArrivals: vi.fn(),
    onToggleLargePrint: vi.fn(),
    onToggleAvailableNow: vi.fn(),
    onToggleAvailableForHold: vi.fn(),
    onClearFilters: vi.fn(),
    isDrawerOpen: false,
    onDrawerClose: vi.fn(),
    ...overrides,
  }
  return {
    props,
    ...render(<CatalogFilterSidebar {...props} />),
  }
}

describe('CatalogFilterSidebar -- LanguageFacet', () => {
  it('renders the Language section with self-translated language names', () => {
    renderSidebar()

    // Section title (fallback string passed via the t() second arg in the
    // component lands here because we stubbed t to return the fallback).
    expect(screen.getAllByText(/^Language$/i).length).toBeGreaterThan(0)

    // Intl.DisplayNames in jsdom usually has full ICU; fall back to the
    // raw 3-letter code if not, so the test stays robust across CIs.
    // Sidebar renders desktop AND mobile variants, so we use *AllByText.
    expect(
      screen.queryAllByText(/^English$/).length
        + screen.queryAllByText(/^eng$/).length,
    ).toBeGreaterThan(0)
    expect(
      screen.queryAllByText(/^Spanish$/).length
        + screen.queryAllByText(/^spa$/).length,
    ).toBeGreaterThan(0)
  })

  it('clicking a language checkbox calls onFilterChange with the ISO 639-2/B code', () => {
    const { props } = renderSidebar()

    const englishMatches = screen.queryAllByText(/^English$/)
    const englishLabel = englishMatches[0] || screen.queryAllByText(/^eng$/)[0]
    expect(englishLabel).toBeTruthy()

    const checkbox = englishLabel!.closest('label')!.querySelector('input[type="checkbox"]')!
    fireEvent.click(checkbox)

    expect(props.onFilterChange).toHaveBeenCalledWith('language', 'eng')
  })

  it('toggles off when the currently selected language is clicked again', () => {
    const { props } = renderSidebar({
      filters: {
        item_type: '',
        location: '',
        publisher: '',
        reading_time: '',
        access: '',
        topic: '',
        language: 'spa',
        year_min: '',
        year_max: '',
      },
    })

    const spanishMatches = screen.queryAllByText(/^Spanish$/)
    const spanishLabel = spanishMatches[0] || screen.queryAllByText(/^spa$/)[0]
    expect(spanishLabel).toBeTruthy()

    const checkbox = spanishLabel!.closest('label')!.querySelector('input[type="checkbox"]')! as HTMLInputElement
    expect(checkbox.checked).toBe(true)

    fireEvent.click(checkbox)
    expect(props.onFilterChange).toHaveBeenCalledWith('language', '')
  })
})
