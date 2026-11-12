/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Same-work matching for the indie-ebook affordance on checked-out print
 * items. Matching must be exact normalized title + author -- a wrong-work
 * link is worse than no link (same bug class as the related-formats fix).
 */
import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useIndieEbookMatch } from "../useIndieEbookMatch"
import type { CatalogItem } from "@/api/api"
import type { UnifiedSearchResult } from "@/api/domains/catalog/unified-search-api"

vi.mock("@/api/domains/catalog/unified-search-api", async () => {
  const actual = await vi.importActual<object>(
    "@/api/domains/catalog/unified-search-api"
  )
  return { ...actual, unifiedSearch: vi.fn() }
})
import { unifiedSearch } from "@/api/domains/catalog/unified-search-api"

function makeItem(overrides: Partial<CatalogItem>): CatalogItem {
  return {
    id: 1,
    title: "Emma",
    author: "Jane Austen",
    item_type: "book",
    status: "checked_out",
    isbn: null,
    publisher: null,
    publication_year: null,
    description: null,
    subjects: null,
    cover_url: null,
    page_count: null,
    location: null,
    barcode: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
    is_large_print: false,
    available_for_hold: true,
    images: [],
    series_name: null,
    series_number: null,
    call_number: null,
    dewey_decimal: null,
    total_checkouts: 0,
    ...overrides,
  } as CatalogItem
}

function makeIndieResult(
  overrides: Partial<UnifiedSearchResult>
): UnifiedSearchResult {
  return {
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
    ...overrides,
  }
}

function mockResults(results: UnifiedSearchResult[]) {
  vi.mocked(unifiedSearch).mockResolvedValue({
    query: "Emma",
    total_results: results.length,
    results,
    sources_searched: ["indie"],
    source_counts: { indie: results.length },
    search_time_ms: 1,
    has_more: false,
  })
}

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe("useIndieEbookMatch", () => {
  beforeEach(() => {
    vi.mocked(unifiedSearch).mockReset()
  })

  it("finds an exact-normalized title+author indie match for a checked-out print item", async () => {
    mockResults([
      makeIndieResult({ id: "indie:7", source_id: "7", title: "  EMMA ", author: "jane  austen" }),
    ])
    const { result } = renderHook(
      () => useIndieEbookMatch(makeItem({ status: "checked_out" })),
      { wrapper: makeWrapper() }
    )
    await waitFor(() =>
      expect(result.current.match).toEqual({ ebookId: 7, title: "  EMMA " })
    )
    expect(unifiedSearch).toHaveBeenCalledWith(
      expect.objectContaining({ query: "Emma", sources: ["indie"], formats: ["ebook"] })
    )
  })

  it("rejects substring titles and different authors (wrong work)", async () => {
    mockResults([
      makeIndieResult({ title: "Emma in the Night", author: "Jane Austen" }),
      makeIndieResult({ title: "Emma", author: "Wendy Walker" }),
    ])
    const { result } = renderHook(
      () => useIndieEbookMatch(makeItem({ status: "on_hold" })),
      { wrapper: makeWrapper() }
    )
    await waitFor(() => expect(unifiedSearch).toHaveBeenCalled())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.match).toBeNull()
  })

  it("rejects unavailable indie results", async () => {
    mockResults([makeIndieResult({ is_available: false })])
    const { result } = renderHook(
      () => useIndieEbookMatch(makeItem({})),
      { wrapper: makeWrapper() }
    )
    await waitFor(() => expect(unifiedSearch).toHaveBeenCalled())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.match).toBeNull()
  })

  it("does not query when the physical item is available", () => {
    renderHook(
      () => useIndieEbookMatch(makeItem({ status: "available" })),
      { wrapper: makeWrapper() }
    )
    expect(unifiedSearch).not.toHaveBeenCalled()
  })

  it("does not query when the item has no author (title-only match is too weak)", () => {
    renderHook(
      () => useIndieEbookMatch(makeItem({ author: "  " })),
      { wrapper: makeWrapper() }
    )
    expect(unifiedSearch).not.toHaveBeenCalled()
  })

  it("does not query when the item is already an ebook", () => {
    renderHook(
      () => useIndieEbookMatch(makeItem({ item_type: "ebook" })),
      { wrapper: makeWrapper() }
    )
    expect(unifiedSearch).not.toHaveBeenCalled()
  })
})
