/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
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

import { CurrentCheckoutsList } from "../CurrentCheckoutsList"
import type { Patron, PatronCheckout } from "../../types"

beforeAll(async () => {
  await loadLanguage("en")
})

const patron: Patron = {
  id: 1,
  email: "p@example.com",
  first_name: "Pat",
  last_name: "Patron",
  role: "patron",
  is_active: true,
  library_card: "LSC000001",
  phone: null,
  address: null,
  created_at: "2024-01-01T00:00:00Z",
  fines_balance: 0,
  total_checkouts: 0,
  current_checkouts: 0,
  current_holds: 0,
} as Patron

function makeCheckout(over: Partial<PatronCheckout> = {}): PatronCheckout {
  return {
    id: 1,
    item_title: "Sample Title",
    item_author: "Sample Author",
    due_date: "2099-12-31T00:00:00Z",
    ...over,
  } as PatronCheckout
}

describe("CurrentCheckoutsList i18n", () => {
  it("renders the translated empty state when there are no checkouts", () => {
    render(
      <CurrentCheckoutsList
        selectedPatron={patron}
        patronCheckouts={[]}
        loadingCheckouts={false}
        isRenewingAll={false}
        onRenewAllClick={() => {}}
      />
    )
    expect(screen.getByText(/No items checked out/i)).toBeInTheDocument()
    expect(screen.getByText(/Current Checkouts \(0\)/)).toBeInTheDocument()
  })

  it("renders the translated 'Renew All' button when checkouts exist", () => {
    render(
      <CurrentCheckoutsList
        selectedPatron={patron}
        patronCheckouts={[makeCheckout()]}
        loadingCheckouts={false}
        isRenewingAll={false}
        onRenewAllClick={() => {}}
      />
    )
    expect(screen.getByRole("button", { name: /renew all eligible items/i })).toBeInTheDocument()
    expect(screen.getByText(/Renew All/)).toBeInTheDocument()
    expect(screen.getByText(/by Sample Author/)).toBeInTheDocument()
  })

  it("uses the translated 'Unknown Item' fallback when title is missing", () => {
    render(
      <CurrentCheckoutsList
        selectedPatron={patron}
        patronCheckouts={[makeCheckout({ item_title: "", item_author: undefined })]}
        loadingCheckouts={false}
        isRenewingAll={false}
        onRenewAllClick={() => {}}
      />
    )
    expect(screen.getByText(/Unknown Item/)).toBeInTheDocument()
  })
})
