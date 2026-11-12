/// <reference types="vite/client" />
/// <reference types="@testing-library/jest-dom/vitest" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

const mockAcceptInvite = vi.fn()
const mockNavigate = vi.fn()

vi.mock("@/api/domains/auth/auth-api", () => ({
  acceptInvite: (...args: unknown[]) => mockAcceptInvite(...args),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock("@/hooks/usePageTitle", () => ({ usePageTitle: vi.fn() }))

vi.mock("@/i18n/I18nContext", () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

import AcceptInvitePage from "../AcceptInvitePage"

function renderPage() {
  return render(
    <MemoryRouter>
      <AcceptInvitePage />
    </MemoryRouter>
  )
}

describe("AcceptInvitePage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.location.hash = "#sometokenvalue"
    mockAcceptInvite.mockResolvedValue({ message: "Account activated" })
  })

  it("calls acceptInvite with the fragment token on submit", async () => {
    renderPage()

    const passwordInput = screen.getByLabelText(/auth\.newPassword/i)
    const confirmInput = screen.getByLabelText(/auth\.confirmPassword/i)
    const submitBtn = screen.getByRole("button", { name: /auth\.activateAccount|auth\.resetPasswordButton/i })

    fireEvent.change(passwordInput, { target: { value: "StrongP@ss1" } })
    fireEvent.change(confirmInput, { target: { value: "StrongP@ss1" } })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(mockAcceptInvite).toHaveBeenCalledWith("sometokenvalue", "StrongP@ss1")
    })
  })
})
