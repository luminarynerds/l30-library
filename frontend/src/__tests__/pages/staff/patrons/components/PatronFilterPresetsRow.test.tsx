/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { render } from "@/__tests__/utils/test-utils"
import { PatronFilterPresetsRow } from "@/pages/staff/patrons/components/PatronFilterPresetsRow"
import {
  BUILTIN_PRESETS,
  PATRON_PRESETS_VERSION,
  usePatronFilterPresets,
} from "@/pages/staff/patrons/hooks/usePatronFilterPresets"

function Harness({ userId = 42 }: { userId?: number }) {
  const presets = usePatronFilterPresets(userId)
  return (
    <PatronFilterPresetsRow
      userPresets={presets.userPresets}
      activePresetId={presets.activePresetId}
      currentFilters={{ finesMin: 5 }}
      currentStatusFilter="all"
      onApply={presets.applyPreset}
      onClearActive={presets.clearActivePreset}
      onSavePreset={presets.saveCurrentAsPreset}
      onDeleteUserPreset={presets.deleteUserPreset}
    />
  )
}

describe("PatronFilterPresetsRow", () => {
  // setup.ts replaces window.localStorage with a vi.fn() shim that doesn't persist.
  // Swap in a real in-memory Storage so we can assert against actual reads/writes.
  beforeEach(() => {
    const store = new Map<string, string>()
    const realLocalStorage: Storage = {
      get length() { return store.size },
      clear: () => store.clear(),
      getItem: (k) => (store.has(k) ? store.get(k)! : null),
      key: (i) => Array.from(store.keys())[i] ?? null,
      removeItem: (k) => { store.delete(k) },
      setItem: (k, v) => { store.set(k, String(v)) },
    }
    vi.stubGlobal("localStorage", realLocalStorage)
    Object.defineProperty(window, "localStorage", { value: realLocalStorage, configurable: true })
  })

  it("renders all four built-in presets as chips", () => {
    render(<Harness />)
    // Each built-in resolves a non-empty translation; the row renders one button per preset.
    BUILTIN_PRESETS.forEach((preset) => {
      const buttons = screen.getAllByRole("button", { pressed: false })
      // At least the four built-ins are rendered as unpressed chips initially.
      expect(buttons.length).toBeGreaterThanOrEqual(BUILTIN_PRESETS.length)
      expect(preset.id).toMatch(/^builtin:/)
    })
  })

  it("clicking a built-in chip marks it active; clicking again clears", () => {
    render(<Harness />)
    const initialUnpressed = screen.getAllByRole("button", { pressed: false }).length
    const firstChip = screen.getAllByRole("button", { pressed: false })[0]!
    fireEvent.click(firstChip)
    expect(screen.getAllByRole("button", { pressed: true }).length).toBe(1)
    const activeChip = screen.getByRole("button", { pressed: true })
    fireEvent.click(activeChip)
    expect(screen.queryAllByRole("button", { pressed: true }).length).toBe(0)
    expect(screen.getAllByRole("button", { pressed: false }).length).toBe(initialUnpressed)
  })

  it("save-current persists a user preset to localStorage under the per-user key", () => {
    const userId = 42
    render(<Harness userId={userId} />)

    // The English catalog loads synchronously (only non-en languages lazy-load
    // in I18nProvider), so this harness's I18nProvider DOES hydrate real
    // translations — query by the current EN copy, not the raw i18n key.
    fireEvent.click(screen.getByRole("button", { name: /save current view/i }))
    const input = screen.getByLabelText(/name for this preset/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: "My view" } })
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))

    const raw = window.localStorage.getItem(`patron-presets:${userId}`)
    expect(raw).not.toBeNull()
    const parsed = JSON.parse(raw!) as { version: number; presets: Array<{ name: string }> }
    expect(parsed.version).toBe(PATRON_PRESETS_VERSION)
    expect(parsed.presets).toHaveLength(1)
    expect(parsed.presets[0]!.name).toBe("My view")
  })

  it("ignores persisted shape with a stale version (does not crash)", () => {
    const userId = 99
    window.localStorage.setItem(
      `patron-presets:${userId}`,
      JSON.stringify({ version: PATRON_PRESETS_VERSION + 99, presets: [{ bogus: true }] })
    )
    render(<Harness userId={userId} />)
    // Only built-in chips are present; no user preset chips were hydrated from the stale blob.
    expect(screen.queryByText(/bogus/i)).toBeNull()
    expect(screen.getAllByRole("button", { pressed: false }).length).toBeGreaterThanOrEqual(
      BUILTIN_PRESETS.length
    )
  })
})
