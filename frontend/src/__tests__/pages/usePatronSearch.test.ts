/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { renderHook, act, waitFor } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { usePatronSearch } from "@/pages/staff/patrons/hooks/usePatronSearch"
import { searchPatrons } from "@/api/api"

vi.mock("@/api/api", () => ({
  searchPatrons: vi.fn(),
}))

describe("usePatronSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(searchPatrons).mockResolvedValue({
      patrons: [],
      total: 0,
      page: 1,
      per_page: 25,
    })
  })

  // Contract: the hook auto-loads the patron list exactly ONCE on mount
  // (staff pages show data immediately), then only refetches on explicit
  // search or page/filter/sort changes — never on raw query-text edits.
  // A double-fetch-on-mount regression is what these counts pin down.

  it("auto-loads the patron list exactly once on mount", async () => {
    renderHook(() => usePatronSearch("token", true))

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(1)
    })
    expect(searchPatrons).toHaveBeenCalledWith(
      "token",
      "",
      1,
      { sortBy: "name", sortDirection: "asc" },
      "all",
      25
    )

    // let any stray second fetch land before asserting it doesn't exist
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(searchPatrons).toHaveBeenCalledTimes(1)
  })

  it("does not auto-load when unauthenticated", async () => {
    renderHook(() => usePatronSearch(null, false))

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(searchPatrons).not.toHaveBeenCalled()
  })

  it("refetches when pagination changes after an explicit search", async () => {
    const { result } = renderHook(() => usePatronSearch("token", true))

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(1) // mount auto-load
    })

    await act(async () => {
      await result.current.performSearch()
    })

    expect(searchPatrons).toHaveBeenCalledTimes(2)

    act(() => {
      result.current.setCurrentPage(2)
    })

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(3)
    })
  })

  it("search form submit fetches page 1 even when current page is not 1", async () => {
    const { result } = renderHook(() => usePatronSearch("token", true))

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(1) // mount auto-load
    })

    await act(async () => {
      await result.current.performSearch({ page: 3 })
    })

    expect(searchPatrons).toHaveBeenLastCalledWith(
      "token",
      "",
      3,
      { sortBy: "name", sortDirection: "asc" },
      "all",
      25
    )

    await act(async () => {
      result.current.handleSearch({ preventDefault: () => {} } as never)
    })

    expect(searchPatrons).toHaveBeenLastCalledWith(
      "token",
      "",
      1,
      { sortBy: "name", sortDirection: "asc" },
      "all",
      25
    )
  })

  it("does not issue duplicate requests when submit resets page to 1", async () => {
    const { result } = renderHook(() => usePatronSearch("token", true))

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(1) // mount auto-load
    })

    await act(async () => {
      await result.current.performSearch()
    })

    expect(searchPatrons).toHaveBeenCalledTimes(2)

    act(() => {
      result.current.setCurrentPage(3)
    })

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(3)
    })

    act(() => {
      result.current.handleSearch({ preventDefault: () => {} } as never)
    })

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(4)
    })

    expect(searchPatrons).toHaveBeenLastCalledWith(
      "token",
      "",
      1,
      { sortBy: "name", sortDirection: "asc" },
      "all",
      25
    )
  })

  it("does not auto-refetch on query text changes after initial explicit search", async () => {
    const { result } = renderHook(() => usePatronSearch("token", true))

    await waitFor(() => {
      expect(searchPatrons).toHaveBeenCalledTimes(1) // mount auto-load
    })

    await act(async () => {
      await result.current.performSearch({ query: "alex" })
    })

    expect(searchPatrons).toHaveBeenCalledTimes(2)

    act(() => {
      result.current.setSearchQuery("alexa")
    })

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(searchPatrons).toHaveBeenCalledTimes(2)
  })
})
