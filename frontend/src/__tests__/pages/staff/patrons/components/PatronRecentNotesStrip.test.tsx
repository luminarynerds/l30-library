/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from "vitest"
import { screen, fireEvent, waitFor } from "@testing-library/react"
import { render } from "@/__tests__/utils/test-utils"
import { PatronRecentNotesStrip } from "@/pages/staff/patrons/components/PatronRecentNotesStrip"
import * as api from "@/api/domains/patron/patron-communication-api"

vi.mock("@/api/domains/patron/patron-communication-api", async () => {
  const actual = await vi.importActual<typeof import("@/api/domains/patron/patron-communication-api")>(
    "@/api/domains/patron/patron-communication-api"
  )
  return {
    ...actual,
    getPatronNotes: vi.fn(),
    createPatronNote: vi.fn(),
  }
})

const mockedGet = vi.mocked(api.getPatronNotes)
const mockedCreate = vi.mocked(api.createPatronNote)

beforeEach(() => {
  vi.clearAllMocks()
  const store = new Map<string, string>()
  const real: Storage = {
    get length() { return store.size },
    clear: () => store.clear(),
    getItem: (k) => store.has(k) ? store.get(k)! : null,
    key: (i) => Array.from(store.keys())[i] ?? null,
    removeItem: (k) => { store.delete(k) },
    setItem: (k, v) => { store.set(k, String(v)) },
  }
  vi.stubGlobal("localStorage", real)
  Object.defineProperty(window, "localStorage", { value: real, configurable: true })
})

describe("PatronRecentNotesStrip", () => {
  it("persists collapse state to localStorage per-user", async () => {
    mockedGet.mockResolvedValue({ notes: [], total: 0 })
    render(
      <PatronRecentNotesStrip
        token="t"
        patronId={42}
        userId={7}
        onOpenNote={() => {}}
      />
    )
    const toggle = await screen.findByRole("button", { name: /recent notes/i })
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    expect(localStorage.getItem("recent-notes-collapsed:7")).toBe("1")
    fireEvent.click(toggle)
    expect(localStorage.getItem("recent-notes-collapsed:7")).toBe("0")
  })

  it("optimistically prepends a new note on save before the API resolves", async () => {
    mockedGet.mockResolvedValue({ notes: [], total: 0 })
    // Hold the create promise open so we can assert the optimistic state.
    let resolveCreate!: (v: api.PatronNote) => void
    mockedCreate.mockImplementation(() => new Promise<api.PatronNote>((resolve) => {
      resolveCreate = resolve
    }))

    render(
      <PatronRecentNotesStrip
        token="t"
        patronId={42}
        userId={7}
        onOpenNote={() => {}}
      />
    )
    await screen.findByText(/no notes yet/i)
    fireEvent.click(screen.getByRole("button", { name: /add the first/i }))
    const textarea = await screen.findByPlaceholderText(/write a note/i)
    fireEvent.change(textarea, { target: { value: "Urgent: returning a damaged item Friday" } })
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))

    // Optimistic: visible before resolve
    await screen.findByText(/Urgent: returning a damaged item Friday/i)

    // Now resolve the API and assert no duplicate render
    resolveCreate({
      id: 1234,
      patron_id: 42,
      author_id: null,
      author_name: null,
      category: "general",
      content: "Urgent: returning a damaged item Friday",
      created_at: new Date().toISOString(),
      updated_at: null,
    })
    await waitFor(() => {
      const matches = screen.queryAllByText(/Urgent: returning a damaged item Friday/i)
      expect(matches.length).toBe(1)
    })
  })

  it("rolls back the optimistic note when the API fails", async () => {
    mockedGet.mockResolvedValue({ notes: [], total: 0 })
    mockedCreate.mockRejectedValueOnce(new Error("server down"))
    render(
      <PatronRecentNotesStrip
        token="t"
        patronId={42}
        userId={7}
        onOpenNote={() => {}}
      />
    )
    await screen.findByText(/no notes yet/i)
    fireEvent.click(screen.getByRole("button", { name: /add the first/i }))
    const textarea = await screen.findByPlaceholderText(/write a note/i)
    fireEvent.change(textarea, { target: { value: "Should disappear" } })
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))
    await waitFor(() => {
      expect(screen.queryByText(/Should disappear/i)).not.toBeInTheDocument()
    })
  })
})
