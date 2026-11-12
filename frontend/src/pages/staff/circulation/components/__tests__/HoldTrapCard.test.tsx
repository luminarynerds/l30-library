/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { loadLanguage } from "@/i18n/translations"

vi.mock("@/i18n", async () => {
  const actual = await vi.importActual<typeof import("@/i18n")>("@/i18n")
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown>) => actual.getTranslation(key, "en", params),
      language: "en",
      isRTL: false,
    }),
  }
})

import { HoldTrapCard } from "../HoldTrapCard"
import type { NextHoldInfo } from "@/api/staff-api/circulation"

beforeAll(async () => {
  await loadLanguage("en")
})

function makeHold(overrides: Partial<NextHoldInfo> = {}): NextHoldInfo {
  return {
    hold_id: 42,
    patron_first_name: "Felicity",
    patron_last_initial: "T.",
    shelf_slot: "A-12",
    expires_at: "2026-06-01T00:00:00Z",
    item_title: "A Confederacy of Dunces",
    ...overrides,
  }
}

describe("HoldTrapCard", () => {
  it("renders patron initials and slot when shelf slot is assigned", () => {
    render(<HoldTrapCard nextHold={makeHold()} onDismiss={() => {}} />)
    const card = screen.getByTestId("hold-trap-card")
    expect(card).toBeInTheDocument()
    expect(card.textContent).toContain("Place on hold shelf for Felicity T. — slot A-12")
    expect(card.textContent).toContain("A Confederacy of Dunces")
  })

  it("falls back gracefully when shelf_slot is null", () => {
    render(<HoldTrapCard nextHold={makeHold({ shelf_slot: null })} onDismiss={() => {}} />)
    const card = screen.getByTestId("hold-trap-card")
    expect(card.textContent).toContain("Place on hold shelf for Felicity T.")
    // No "— slot X" suffix when shelf_slot is null
    expect(card.textContent).not.toContain("— slot")
    expect(card.textContent).toContain("Shelf slot not yet assigned")
  })

  it("calls onDismiss when dismiss button is clicked", async () => {
    const onDismiss = vi.fn()
    render(<HoldTrapCard nextHold={makeHold()} onDismiss={onDismiss} />)
    await userEvent.click(screen.getByRole("button", { name: /Dismiss hold trap card/i }))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it("invokes window.print when Print Hold Slip is clicked with no onPrint", async () => {
    const original = window.print
    const printMock = vi.fn()
    window.print = printMock
    try {
      render(<HoldTrapCard nextHold={makeHold()} onDismiss={() => {}} />)
      await userEvent.click(screen.getByTestId("hold-trap-print"))
      expect(printMock).toHaveBeenCalledOnce()
    } finally {
      window.print = original
    }
  })

  it("calls onPrint instead of window.print when onPrint is provided", async () => {
    const onPrint = vi.fn()
    const original = window.print
    const printMock = vi.fn()
    window.print = printMock
    try {
      render(<HoldTrapCard nextHold={makeHold()} onDismiss={() => {}} onPrint={onPrint} />)
      await userEvent.click(screen.getByTestId("hold-trap-print"))
      expect(onPrint).toHaveBeenCalledOnce()
      expect(printMock).not.toHaveBeenCalled()
    } finally {
      window.print = original
    }
  })

  it("renders translated copy from the staffCirculation.holdTrap namespace", () => {
    render(<HoldTrapCard nextHold={makeHold()} onDismiss={() => {}} />)
    expect(screen.getByRole("button", { name: /print hold slip/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /dismiss hold trap card/i })).toBeInTheDocument()
    expect(screen.getByText(/Hold pickup deadline:/)).toBeInTheDocument()
  })
})
