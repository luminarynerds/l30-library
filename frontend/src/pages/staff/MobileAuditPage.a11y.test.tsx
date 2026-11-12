/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("@/lib/api-client", () => ({
  fetchApi: vi.fn(() => Promise.resolve({ items: [] })),
}))

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, role: "staff" },
    token: "test-token",
    isLoading: false,
  }),
}))

import MobileAuditPage from "./MobileAuditPage"

describe("MobileAuditPage a11y", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it("renders a live region (role=status, aria-live=assertive) for scan results", () => {
    render(<MobileAuditPage />)
    const live = screen.getByRole("status")
    expect(live).toHaveAttribute("aria-live", "assertive")
  })

  it("manual-entry toggle flips the barcode input between inputMode none and text", async () => {
    const user = userEvent.setup()
    render(<MobileAuditPage />)

    const input = screen.getByLabelText("Barcode input")
    expect(input).toHaveAttribute("inputmode", "none")

    const toggle = screen.getByRole("button", { name: /enable manual keyboard entry/i })
    expect(toggle).toHaveAttribute("aria-pressed", "false")

    await user.click(toggle)

    expect(input).toHaveAttribute("inputmode", "text")
    expect(
      screen.getByRole("button", { name: /disable manual keyboard entry/i })
    ).toHaveAttribute("aria-pressed", "true")
  })
})
