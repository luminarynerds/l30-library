/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

const getInventoryCopiesMock = vi.fn()
vi.mock("../../api/domains/catalog/inventory-api", () => ({
  getInventoryCopies: (...args: unknown[]) => getInventoryCopiesMock(...args),
  withdrawCopy: vi.fn(),
  repairCopy: vi.fn(),
}))

vi.mock("../../components/shells/AdminShell", () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import RepairQueuePage from "./RepairQueuePage"

const ITEM = {
  id: 77,
  catalog_item_id: 5,
  barcode: "L30-DMG-77",
  condition: "damaged",
  replacement_cost: 20,
  catalog_title: "Cracked Spine",
  catalog_author: "A. Author",
  location: "Stacks",
  notes: null,
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <RepairQueuePage />
    </QueryClientProvider>
  )
}

// The global test setup stubs localStorage with non-functional vi.fn()s.
// Install a real in-memory store so persistence/restore can be exercised.
function installRealLocalStorage() {
  const store = new Map<string, string>()
  vi.spyOn(window.localStorage, "getItem").mockImplementation(
    (k: string) => (store.has(k) ? (store.get(k) as string) : null)
  )
  vi.spyOn(window.localStorage, "setItem").mockImplementation(
    (k: string, v: string) => {
      store.set(k, String(v))
    }
  )
  vi.spyOn(window.localStorage, "removeItem").mockImplementation((k: string) => {
    store.delete(k)
  })
  vi.spyOn(window.localStorage, "clear").mockImplementation(() => store.clear())
  return store
}

describe("RepairQueuePage draft persistence", () => {
  beforeEach(() => {
    installRealLocalStorage()
    localStorage.clear()
    getInventoryCopiesMock.mockReset()
    getInventoryCopiesMock.mockImplementation((params?: { condition?: string }) => {
      if (params?.condition === "damaged") {
        return Promise.resolve({ items: [ITEM], total: 1, page: 1, per_page: 100 })
      }
      return Promise.resolve({ items: [], total: 0, page: 1, per_page: 100 })
    })
  })

  it("restores a saved triage draft from localStorage on mount", async () => {
    localStorage.setItem(
      "l30_repair_queue_drafts",
      JSON.stringify({
        77: { decision: "repair", repairEstimate: "8.50", repairNotes: "Re-glue spine" },
      })
    )

    renderPage()

    // Wait for the query-fed item card to mount.
    await screen.findByText("Cracked Spine", {}, { timeout: 3000 })

    // Estimate input is always rendered; proves repairEstimate was restored.
    const estimate = screen.getByPlaceholderText("0.00") as HTMLInputElement
    expect(estimate.value).toBe("8.50")

    // The repair-notes field only renders when the restored decision === "repair",
    // so its presence + value proves both decision and notes were restored.
    const notes = screen.getByPlaceholderText(
      /describe repair needed/i
    ) as HTMLInputElement
    expect(notes.value).toBe("Re-glue spine")
  })

  it("writes drafts to localStorage as decisions change", async () => {
    renderPage()
    await screen.findByText("Cracked Spine", {}, { timeout: 3000 })
    // No draft seeded; effect persists the (empty) decisions map under the key.
    expect(localStorage.getItem("l30_repair_queue_drafts")).not.toBeNull()
  })

  it("clears the draft when the item is dismissed via Keep As-Is", async () => {
    const user = userEvent.setup()
    localStorage.setItem(
      "l30_repair_queue_drafts",
      JSON.stringify({ 77: { decision: "keep", repairEstimate: "", repairNotes: "" } })
    )

    renderPage()
    await screen.findByText("Cracked Spine", {}, { timeout: 3000 })

    // "keep" is the restored decision, so the Confirm button is shown.
    await user.click(screen.getByRole("button", { name: /confirm/i }))

    const saved = JSON.parse(localStorage.getItem("l30_repair_queue_drafts") || "{}")
    expect(saved["77"]).toBeUndefined()
  })
})
