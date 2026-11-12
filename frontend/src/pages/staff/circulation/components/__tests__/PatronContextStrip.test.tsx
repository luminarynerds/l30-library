/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { loadLanguage } from "@/i18n/translations"

const fetchApiMock = vi.fn()
vi.mock("@/api/fetchApi", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
}))

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

import { PatronContextStrip } from "../PatronContextStrip"

beforeAll(async () => {
  await loadLanguage("en")
})

const today = new Date()
const todayIso = today.toISOString()
const tomorrowIso = new Date(today.getTime() + 24 * 60 * 60 * 1000).toISOString()

beforeEach(() => {
  fetchApiMock.mockReset()
})

describe("PatronContextStrip", () => {
  it("renders four tiles populated from the context-card endpoint", async () => {
    fetchApiMock.mockResolvedValueOnce({
      checkouts: {
        due_soon_items: [
          { id: 1, title: "Book A", due_date: todayIso },
          { id: 2, title: "Book B", due_date: todayIso },
          { id: 3, title: "Book C", due_date: tomorrowIso },
        ],
      },
      holds: { ready_for_pickup_count: 2, in_transit_count: 1 },
      fines: { total_owed: 0.75 },
    })

    render(<PatronContextStrip patronId={42} patronName="Pat Patron" />)

    await waitFor(() => expect(screen.getByTestId("patron-context-strip")).toBeInTheDocument())

    expect(screen.getByTestId("patron-context-strip-holds")).toHaveTextContent("2")
    expect(screen.getByTestId("patron-context-strip-transit")).toHaveTextContent("1")
    expect(screen.getByTestId("patron-context-strip-fines")).toHaveTextContent("$0.75")
    expect(screen.getByTestId("patron-context-strip-due-today")).toHaveTextContent("2")

    expect(fetchApiMock).toHaveBeenCalledWith("/staff/patrons/42/context-card")
  })

  it("renders zero-state tiles as disabled and muted", async () => {
    fetchApiMock.mockResolvedValueOnce({
      checkouts: { due_soon_items: [] },
      holds: { ready_for_pickup_count: 0, in_transit_count: 0 },
      fines: { total_owed: 0 },
    })

    render(<PatronContextStrip patronId={1} patronName="Empty Patron" />)
    await waitFor(() => expect(screen.getByTestId("patron-context-strip")).toBeInTheDocument())

    const holdsTile = screen.getByTestId("patron-context-strip-holds")
    const finesTile = screen.getByTestId("patron-context-strip-fines")
    const dueTodayTile = screen.getByTestId("patron-context-strip-due-today")

    expect(holdsTile).toBeDisabled()
    expect(holdsTile).toHaveAttribute("aria-disabled", "true")
    expect(finesTile).toBeDisabled()
    expect(dueTodayTile).toBeDisabled()
  })

  it("invokes scrollIntoView on the matching section when a populated tile is clicked", async () => {
    fetchApiMock.mockResolvedValueOnce({
      checkouts: { due_soon_items: [] },
      holds: { ready_for_pickup_count: 2, in_transit_count: 0 },
      fines: { total_owed: 0 },
    })

    const scrollIntoView = vi.fn()
    const section = document.createElement("div")
    section.id = "circulation-holds-section"
    ;(section as unknown as { scrollIntoView: typeof scrollIntoView }).scrollIntoView = scrollIntoView
    document.body.appendChild(section)

    render(<PatronContextStrip patronId={7} patronName="Click Patron" />)
    await waitFor(() => expect(screen.getByTestId("patron-context-strip")).toBeInTheDocument())

    const holdsTile = screen.getByTestId("patron-context-strip-holds")
    expect(holdsTile).not.toBeDisabled()

    const user = userEvent.setup()
    await user.click(holdsTile)

    expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest", behavior: "smooth" })

    document.body.removeChild(section)
  })

  it("renders a loading state before the fetch resolves", () => {
    fetchApiMock.mockReturnValueOnce(new Promise(() => { /* never resolves */ }))
    render(<PatronContextStrip patronId={9} patronName="Loading Patron" />)
    expect(screen.getByTestId("patron-context-strip-loading")).toBeInTheDocument()
  })

  it("renders fines via Intl.NumberFormat (locale-formatted USD, not a raw $X.XX template literal)", async () => {
    fetchApiMock.mockResolvedValueOnce({
      checkouts: { due_soon_items: [] },
      holds: { ready_for_pickup_count: 0, in_transit_count: 0 },
      fines: { total_owed: 1234.5 },
    })

    render(<PatronContextStrip patronId={11} patronName="Locale Patron" />)
    await waitFor(() => expect(screen.getByTestId("patron-context-strip")).toBeInTheDocument())

    // en-US formatter inserts a thousands separator: "$1,234.50"
    // The pre-Intl literal `$${n.toFixed(2)}` rendered "$1234.50" with no comma.
    expect(screen.getByTestId("patron-context-strip-fines")).toHaveTextContent("$1,234.50")
  })
})
