// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { renderHook, act } from "@testing-library/react"
import { it, expect, vi, beforeEach, afterEach } from "vitest"
import { useElapsed, fmtElapsed } from "../useElapsed"

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it("fmtElapsed formats h/m", () => {
  expect(fmtElapsed(0)).toBe("0m")
  expect(fmtElapsed(60_000)).toBe("1m")
  expect(fmtElapsed(2 * 3600_000 + 14 * 60_000)).toBe("2h 14m")
})

it("useElapsed ticks while active and is null when inactive", () => {
  vi.setSystemTime(new Date("2026-06-07T13:00:00-04:00"))
  const { result, rerender } = renderHook(
    ({ since }: { since: string | null }) => useElapsed(since),
    { initialProps: { since: null as string | null } },
  )
  expect(result.current).toBeNull()
  rerender({ since: "2026-06-07T13:00:00-04:00" })
  act(() => { vi.advanceTimersByTime(60_000) })
  expect(result.current).toBeGreaterThanOrEqual(60_000)
})
