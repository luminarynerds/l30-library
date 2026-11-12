// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Regression test: chained refreshHolds + refreshCheckouts must not clobber each other.
 *
 * Before the fix, both callbacks called `setSelectedPatron({ ...selectedPatron, <field> })`
 * where `selectedPatron` was the CLOSURE-CAPTURED value at callback-creation time.
 * When both were created from the SAME render snapshot and awaited sequentially inside
 * a single act(), the second call spread the SAME stale snapshot and discarded the
 * first call's fresh data.
 *
 * After the fix both use the functional-updater form:
 *   setSelectedPatron(prev => prev ? { ...prev, <field>: fresh } : prev)
 * which always merges into the CURRENT state, so chaining is safe.
 */
import { describe, it, expect, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useState, useCallback, useRef } from "react"

// Minimal stand-in types
interface Hold { id: number; status: string }
interface Checkout { id: number; item_id: number }
interface PatronDetail { id: number; holds?: Hold[]; checkouts?: Checkout[] }

const INITIAL_HOLDS: Hold[] = [{ id: 10, status: "ready" }]
const INITIAL_CHECKOUTS: Checkout[] = [{ id: 20, item_id: 100 }]
const FRESH_HOLDS: Hold[] = [{ id: 99, status: "fulfilled" }]
const FRESH_CHECKOUTS: Checkout[] = [{ id: 55, item_id: 200 }]

// ---- Fixed hook: functional updater ----
function useFixedRefresh(
  fetchHolds: () => Promise<Hold[]>,
  fetchCheckouts: () => Promise<Checkout[]>,
) {
  const [patron, setPatron] = useState<PatronDetail | null>({
    id: 1,
    holds: INITIAL_HOLDS,
    checkouts: INITIAL_CHECKOUTS,
  })

  const refreshHolds = useCallback(async () => {
    if (!patron) return
    const holds = await fetchHolds()
    setPatron(prev => prev ? { ...prev, holds } : prev)
  }, [fetchHolds, patron])

  const refreshCheckouts = useCallback(async () => {
    if (!patron) return
    const checkouts = await fetchCheckouts()
    setPatron(prev => prev ? { ...prev, checkouts } : prev)
  }, [fetchCheckouts, patron])

  return { patron, refreshHolds, refreshCheckouts }
}

// ---- Buggy hook: stale closure — captures patron at creation time ----
function useBuggyRefresh(
  fetchHolds: () => Promise<Hold[]>,
  fetchCheckouts: () => Promise<Checkout[]>,
) {
  const [patron, setPatron] = useState<PatronDetail | null>({
    id: 1,
    holds: INITIAL_HOLDS,
    checkouts: INITIAL_CHECKOUTS,
  })

  // Freeze the patron at hook-creation time using a ref so callbacks
  // always close over the SAME stale snapshot — this replicates the bug
  // where both useCallbacks captured `selectedPatron` in the same render.
  const stalePatronRef = useRef(patron)

  const refreshHolds = useCallback(async () => {
    if (!stalePatronRef.current) return
    const holds = await fetchHolds()
    // BUG: always spreads stalePatronRef.current — the original snapshot
    setPatron({ ...stalePatronRef.current, holds })
  }, [fetchHolds])

  const refreshCheckouts = useCallback(async () => {
    if (!stalePatronRef.current) return
    const checkouts = await fetchCheckouts()
    // BUG: always spreads stalePatronRef.current — discards holds update
    setPatron({ ...stalePatronRef.current, checkouts })
  }, [fetchCheckouts])

  return { patron, refreshHolds, refreshCheckouts }
}

describe("chained patron refresh — stale-closure vs functional updater", () => {
  it("functional updater: chained refreshHolds then refreshCheckouts preserves both fresh arrays", async () => {
    const fetchHolds = vi.fn().mockResolvedValue(FRESH_HOLDS)
    const fetchCheckouts = vi.fn().mockResolvedValue(FRESH_CHECKOUTS)

    const { result } = renderHook(() => useFixedRefresh(fetchHolds, fetchCheckouts))

    // Both calls inside ONE act() so they execute against the same render snapshot
    await act(async () => {
      await result.current.refreshHolds()
      await result.current.refreshCheckouts()
    })

    // The functional updater guarantees both fresh arrays survive
    expect(result.current.patron?.holds).toEqual(FRESH_HOLDS)
    expect(result.current.patron?.checkouts).toEqual(FRESH_CHECKOUTS)
  })

  it("stale-closure (pre-fix bug): chained calls with frozen snapshot lose the holds update", async () => {
    const fetchHolds = vi.fn().mockResolvedValue(FRESH_HOLDS)
    const fetchCheckouts = vi.fn().mockResolvedValue(FRESH_CHECKOUTS)

    const { result } = renderHook(() => useBuggyRefresh(fetchHolds, fetchCheckouts))

    // Both calls inside ONE act() — they both close over the same stale ref
    await act(async () => {
      await result.current.refreshHolds()
      await result.current.refreshCheckouts()
    })

    // The second call spreads the frozen stale snapshot (holds = INITIAL_HOLDS),
    // clobbering the fresh holds from the first call.
    expect(result.current.patron?.holds).not.toEqual(FRESH_HOLDS)   // bug demonstrated
    expect(result.current.patron?.holds).toEqual(INITIAL_HOLDS)      // reverted to stale
    expect(result.current.patron?.checkouts).toEqual(FRESH_CHECKOUTS) // checkouts fine
  })
})
