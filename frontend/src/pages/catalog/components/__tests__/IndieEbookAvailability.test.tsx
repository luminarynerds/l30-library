/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { IndieEbookAvailability } from "../IndieEbookAvailability"
import type { CatalogItem } from "@/api/api"

vi.mock("@/api/domains/catalog/unified-search-api", async () => {
  const actual = await vi.importActual<object>(
    "@/api/domains/catalog/unified-search-api"
  )
  return { ...actual, unifiedSearch: vi.fn() }
})
import { unifiedSearch } from "@/api/domains/catalog/unified-search-api"

const item = {
  id: 1,
  title: "Emma",
  author: "Jane Austen",
  item_type: "book",
  status: "checked_out",
  is_large_print: false,
} as CatalogItem

function mockIndieMatch() {
  vi.mocked(unifiedSearch).mockResolvedValue({
    query: "Emma",
    total_results: 1,
    results: [
      {
        id: "indie:42",
        source: "indie",
        source_id: "42",
        title: "Emma",
        author: "Jane Austen",
        authors: ["Jane Austen"],
        format: "ebook",
        format_details: ["epub"],
        description: null,
        cover_url: null,
        isbn: null,
        publisher: null,
        publication_year: null,
        subjects: [],
        language: "en",
        is_available: true,
        copies_available: null,
        copies_total: null,
        hold_count: null,
        estimated_wait_days: null,
        download_formats: ["epub"],
        relevance_score: 0.9,
        related_sources: [],
      },
    ],
    sources_searched: ["indie"],
    source_counts: { indie: 1 },
    search_time_ms: 1,
    has_more: false,
  })
}

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe("IndieEbookAvailability", () => {
  beforeEach(() => {
    vi.mocked(unifiedSearch).mockReset()
  })

  it("links to the indie ebook detail page when a match exists", async () => {
    mockIndieMatch()
    renderWithProviders(<IndieEbookAvailability item={item} noFOMO={false} />)
    const link = await screen.findByRole("link", {
      name: /also available as an ebook via metislib/i,
    })
    expect(link).toHaveAttribute("href", "/indie/book/emma-42")
  })

  it("never promises immediate availability ('now')", async () => {
    mockIndieMatch()
    renderWithProviders(<IndieEbookAvailability item={item} noFOMO={false} />)
    await screen.findByRole("link", {
      name: /also available as an ebook/i,
    })
    expect(screen.queryByText(/available now/i)).not.toBeInTheDocument()
  })

  it("drops the MetisLib mention under noFOMO and still avoids 'now'", async () => {
    mockIndieMatch()
    renderWithProviders(<IndieEbookAvailability item={item} noFOMO={true} />)
    const link = await screen.findByRole("link", {
      name: /^also available as an ebook$/i,
    })
    expect(link).toHaveAttribute("href", "/indie/book/emma-42")
    expect(screen.queryByText(/available now/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/metislib/i)).not.toBeInTheDocument()
  })

  it("renders nothing when no indie match exists", async () => {
    vi.mocked(unifiedSearch).mockResolvedValue({
      query: "Emma",
      total_results: 0,
      results: [],
      sources_searched: ["indie"],
      source_counts: {},
      search_time_ms: 1,
      has_more: false,
    })
    const { container } = renderWithProviders(
      <IndieEbookAvailability item={item} noFOMO={false} />
    )
    await waitFor(() => expect(unifiedSearch).toHaveBeenCalled())
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })
})
