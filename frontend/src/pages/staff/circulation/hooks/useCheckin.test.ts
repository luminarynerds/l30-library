/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { createRef } from "react"
import { useCheckin } from "./useCheckin"

vi.mock("@/i18n", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

vi.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/api", () => ({
  staffCheckinItem: vi.fn(),
}))

vi.mock("@/api/staff-api/circulation", () => ({
  reportCheckinCondition: vi.fn(),
}))

import { staffCheckinItem } from "@/api/api"
const mockedCheckin = staffCheckinItem as unknown as ReturnType<typeof vi.fn>

function fakeEvent() {
  return { preventDefault: vi.fn() } as unknown as React.FormEvent
}

describe("useCheckin", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  it("refocuses the barcode input via inputRef after a failed scan", async () => {
    const focusSpy = vi.fn()
    const inputRef = createRef<HTMLInputElement>()
    // Pretend the input is mounted.
    Object.defineProperty(inputRef, "current", {
      writable: true,
      value: { focus: focusSpy } as unknown as HTMLInputElement,
    })
    mockedCheckin.mockRejectedValueOnce(new Error("Item not found"))

    const { result } = renderHook(() => useCheckin("tok", { inputRef }))

    act(() => {
      result.current.setCheckinBarcode("ABC123")
    })
    await act(async () => {
      await result.current.handleCheckin(fakeEvent())
    })
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    expect(focusSpy).toHaveBeenCalled()
  })

  it("does not throw when no inputRef is provided", async () => {
    mockedCheckin.mockRejectedValueOnce(new Error("Item not found"))
    const { result } = renderHook(() => useCheckin("tok"))

    act(() => {
      result.current.setCheckinBarcode("ABC123")
    })
    await act(async () => {
      await result.current.handleCheckin(fakeEvent())
    })
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // The hook just settles. No assertion needed beyond not-throwing.
    expect(result.current.isCheckingIn).toBe(false)
  })
})
