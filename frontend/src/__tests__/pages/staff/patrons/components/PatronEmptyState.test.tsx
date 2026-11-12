/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from "vitest"
import { screen, fireEvent } from "@testing-library/react"
import { render } from "@/__tests__/utils/test-utils"
import { PatronEmptyState } from "@/pages/staff/patrons/components/PatronEmptyState"

beforeEach(() => {
  const store = new Map<string, string>()
  const real: Storage = {
    get length() { return store.size },
    clear: () => store.clear(),
    getItem: (k) => store.has(k) ? store.get(k)! : null,
    key: (i) => Array.from(store.keys())[i] ?? null,
    removeItem: (k) => { store.delete(k) },
    setItem: (k, v) => { store.set(k, String(v)) },
  }
  vi.stubGlobal("sessionStorage", real)
  Object.defineProperty(window, "sessionStorage", { value: real, configurable: true })
})

describe("PatronEmptyState", () => {
  it("renders the three primary actions", () => {
    render(
      <PatronEmptyState
        userId={1}
        headline="Select a patron"
        onScanCard={() => {}}
        onRegisterPatron={() => {}}
        onSelectRecent={() => {}}
      />
    )
    expect(screen.getByRole("button", { name: /scan card/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /register patron/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /no recent patrons|open recent/i })).toBeInTheDocument()
  })

  it("fires onScanCard and onRegisterPatron handlers", () => {
    const scan = vi.fn()
    const reg = vi.fn()
    render(
      <PatronEmptyState
        userId={1}
        headline="Select a patron"
        onScanCard={scan}
        onRegisterPatron={reg}
        onSelectRecent={() => {}}
      />
    )
    fireEvent.click(screen.getByRole("button", { name: /scan card/i }))
    fireEvent.click(screen.getByRole("button", { name: /register patron/i }))
    expect(scan).toHaveBeenCalledTimes(1)
    expect(reg).toHaveBeenCalledTimes(1)
  })

  it("disables the recents dropdown when sessionStorage is empty", () => {
    render(
      <PatronEmptyState
        userId={1}
        headline="Select a patron"
        onScanCard={() => {}}
        onRegisterPatron={() => {}}
        onSelectRecent={() => {}}
      />
    )
    expect(screen.getByRole("button", { name: /no recent patrons/i })).toBeDisabled()
  })

  it("shows recents from sessionStorage and fires onSelectRecent", () => {
    sessionStorage.setItem(
      "recent-patrons:1",
      JSON.stringify([
        { id: 99, displayName: "Ada Lovelace", viewedAt: new Date().toISOString() },
      ])
    )
    const onSelect = vi.fn()
    render(
      <PatronEmptyState
        userId={1}
        headline="Select a patron"
        onScanCard={() => {}}
        onRegisterPatron={() => {}}
        onSelectRecent={onSelect}
      />
    )
    fireEvent.click(screen.getByRole("button", { name: /open recent patron/i }))
    const opt = screen.getByRole("option", { name: /Ada Lovelace/i })
    fireEvent.click(opt)
    expect(onSelect).toHaveBeenCalledWith(99)
  })
})
