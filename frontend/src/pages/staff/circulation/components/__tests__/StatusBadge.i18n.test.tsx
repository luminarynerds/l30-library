/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, describe, it, expect, vi } from "vitest"
import { useRef } from "react"
import { render, screen } from "@testing-library/react"
import { loadLanguage } from "@/i18n/translations"
import { PatronSearchSection } from "../PatronSearchSection"
import type { Patron } from "../../types"

// Use the real translation table — the inline-mock pattern in
// PatronSearchSection.test.tsx returns the key for unknown lookups, which would
// render literal "patronStatus.active" badges instead of "Active".
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

vi.mock("@/components/staff/AddPatronModal", () => ({
  default: () => null,
}))

function makePatron(id: number, status: Patron["patron_status"]): Patron {
  return {
    id,
    first_name: `Patron${id}`,
    last_name: "Test",
    email: `p${id}@example.org`,
    is_active: status === "active",
    library_card: `L${String(id).padStart(4, "0")}`,
    patron_status: status,
  } as Patron
}

function Harness({ results }: { results: Patron[] }): React.ReactElement {
  const inputRef = useRef<HTMLInputElement>(null)
  return (
    <PatronSearchSection
      patronQuery="x"
      setPatronQuery={() => {}}
      searchResults={results}
      selectedResultIndex={-1}
      isSearching={false}
      recentPatrons={[]}
      handlePatronSearch={(e) => e.preventDefault()}
      selectPatron={() => {}}
      handleNavigateUp={() => {}}
      handleNavigateDown={() => {}}
      searchInputRef={inputRef}
    />
  )
}

beforeAll(async () => {
  await loadLanguage("en")
  if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = vi.fn()
  }
})

describe("StatusBadge i18n", () => {
  it("renders the translated label for every patron_status value", () => {
    const results: Patron[] = [
      makePatron(1, "active"),
      makePatron(2, "blocked"),
      makePatron(3, "suspended"),
      makePatron(4, "deceased"),
    ]
    render(<Harness results={results} />)
    // Each badge is a <span> inside the result row; the result list is the
    // only place that renders the four labels, so an exact-string lookup is safe.
    expect(screen.getByText("Active")).toBeInTheDocument()
    expect(screen.getByText("Blocked")).toBeInTheDocument()
    expect(screen.getByText("Suspended")).toBeInTheDocument()
    expect(screen.getByText("Deceased")).toBeInTheDocument()
  })
})
