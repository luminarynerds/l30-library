/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { LexileBadge } from "./LexileBadge"

vi.mock("@/i18n/I18nContext", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (key === "lexile_badge_prefix" && params?.measure) return "Lexile: " + params.measure
      if (key === "lexile_badge_label") return "Lexile reading level"
      if (key === "lexile_badge_tooltip") return "Lexile measures match books to readers. Higher is more advanced."
      return key
    },
  }),
}))

describe("LexileBadge", () => {
  it("renders nothing when measure is null", () => {
    const { container } = render(<LexileBadge measure={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("renders prefixed label by default", () => {
    render(<LexileBadge measure="750L" />)
    expect(screen.getByText(/Lexile: 750L/)).toBeInTheDocument()
  })

  it("renders compact label when compact", () => {
    render(<LexileBadge measure="750L" compact />)
    expect(screen.getByText("750L")).toBeInTheDocument()
  })
})
