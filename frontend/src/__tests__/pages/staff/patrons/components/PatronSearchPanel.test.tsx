/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, waitFor } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { PatronSearchPanel } from "@/pages/staff/patrons/components/PatronSearchPanel"
import { I18nProvider } from "@/i18n/I18nContext"
import { BrandingProvider } from "@/contexts/BrandingContext"

const defaultAdvancedProps = {
  advancedFilters: {},
  onAdvancedFiltersChange: vi.fn(),
  onClearAdvancedFilters: vi.fn(),
  activeFilterCount: 0,
}

function renderPanel(searchQuery = "") {
  const onDebouncedSearch = vi.fn()

  const utils = render(
    <BrandingProvider><I18nProvider><PatronSearchPanel
      searchQuery={searchQuery}
      onSearchQueryChange={vi.fn()}
      statusFilter="all"
      onStatusFilterChange={vi.fn()}
      onSearch={vi.fn()}
      isSearching={false}
      onDebouncedSearch={onDebouncedSearch}
      {...defaultAdvancedProps}
    />
    </I18nProvider></BrandingProvider>
  )

  return { ...utils, onDebouncedSearch }
}

describe("PatronSearchPanel", () => {
  it("does not call debounced search on initial mount", async () => {
    const { onDebouncedSearch } = renderPanel("")

    await new Promise((resolve) => setTimeout(resolve, 450))

    expect(onDebouncedSearch).not.toHaveBeenCalled()
  })

  it("calls debounced search when query changes after mount", async () => {
    const { onDebouncedSearch, rerender } = renderPanel("")

    rerender(
      <BrandingProvider><I18nProvider>
        <PatronSearchPanel
          searchQuery="alex"
          onSearchQueryChange={vi.fn()}
          statusFilter="all"
          onStatusFilterChange={vi.fn()}
          onSearch={vi.fn()}
          isSearching={false}
          onDebouncedSearch={onDebouncedSearch}
          {...defaultAdvancedProps}
        />
      </I18nProvider></BrandingProvider>
    )

    await waitFor(() => {
      expect(onDebouncedSearch).toHaveBeenCalledWith("alex")
    }, { timeout: 1000 })
  })

  it("does not call debounced search when callback identity changes but query is unchanged", async () => {
    const initialCallback = vi.fn()
    const nextCallback = vi.fn()

    const { rerender } = render(
      <BrandingProvider><I18nProvider>
        <PatronSearchPanel
          searchQuery="alex"
          onSearchQueryChange={vi.fn()}
          statusFilter="all"
          onStatusFilterChange={vi.fn()}
          onSearch={vi.fn()}
          isSearching={false}
          onDebouncedSearch={initialCallback}
          {...defaultAdvancedProps}
        />
      </I18nProvider></BrandingProvider>
    )

    rerender(
      <BrandingProvider><I18nProvider>
        <PatronSearchPanel
          searchQuery="alex"
          onSearchQueryChange={vi.fn()}
          statusFilter="all"
          onStatusFilterChange={vi.fn()}
          onSearch={vi.fn()}
          isSearching={false}
          onDebouncedSearch={nextCallback}
          {...defaultAdvancedProps}
        />
      </I18nProvider></BrandingProvider>
    )

    await new Promise((resolve) => setTimeout(resolve, 450))

    expect(initialCallback).not.toHaveBeenCalled()
    expect(nextCallback).not.toHaveBeenCalled()
  })
})
