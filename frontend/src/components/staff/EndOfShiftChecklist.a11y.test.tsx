/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { loadLanguage } from "@/i18n/translations"

const fetchApiMock = vi.fn()
vi.mock("@/api/fetchApi", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
}))
vi.mock("@/lib/sentry-lazy", () => ({
  captureException: vi.fn(),
}))
vi.mock("@/i18n/I18nContext", async () => {
  const actual = await vi.importActual<typeof import("@/i18n/I18nContext")>(
    "@/i18n/I18nContext"
  )
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      language: "en",
      isRTL: false,
    }),
  }
})

import { EndOfShiftChecklist } from "./EndOfShiftChecklist"

const SESSION = {
  id: 1,
  items_completed: 1,
  total_items: 2,
  is_completed: false,
  notes: "",
  checklist_items: [
    {
      id: 10,
      category: "wrap_up",
      title: "Lock the cash drawer",
      status: "pending",
      order: 1,
      required: true,
    },
    {
      id: 11,
      category: "wrap_up",
      title: "Shelve returns",
      status: "completed",
      order: 2,
      required: false,
    },
  ],
}

beforeAll(async () => {
  await loadLanguage("en")
})

beforeEach(() => {
  fetchApiMock.mockReset()
  fetchApiMock.mockImplementation((url: string) => {
    if (url === "/staff/shift-sessions/current") return Promise.resolve(SESSION)
    if (url === "/staff/daily-wins") return Promise.resolve({ wins: [] })
    return Promise.resolve({})
  })
})

describe("EndOfShiftChecklist toggle a11y", () => {
  it("names each item toggle with the item title and exposes pressed state", async () => {
    render(<EndOfShiftChecklist />)

    const pendingToggle = await screen.findByRole("button", {
      name: "Lock the cash drawer",
    })
    expect(pendingToggle).toHaveAttribute("aria-pressed", "false")

    const completedToggle = screen.getByRole("button", { name: "Shelve returns" })
    expect(completedToggle).toHaveAttribute("aria-pressed", "true")
  })
})
