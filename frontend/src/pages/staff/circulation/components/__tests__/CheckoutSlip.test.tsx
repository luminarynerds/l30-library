/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

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

// Mock fetchApi so we can assert what the toolbar sends.
const fetchApiMock = vi.fn()
vi.mock("@/lib/api-client", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
  isApiError: (e: unknown): e is { detail?: string } =>
    typeof e === "object" && e !== null && "detail" in (e as object),
}))

// Stub react-hot-toast so we don't need a Toaster mounted.
vi.mock("react-hot-toast", () => {
  const fn = vi.fn()
  return {
    __esModule: true,
    default: Object.assign(fn, { success: vi.fn(), error: vi.fn() }),
  }
})

import { CheckoutSlip } from "../CheckoutSlip"
import type { Checkout } from "@/api/api"
import type { Patron } from "../../types"


const checkout: Checkout = {
  id: 4242,
  user_id: 1,
  item_id: 99,
  status: "active",
  checked_out_at: "2026-05-18T15:00:00Z",
  due_date: "2026-06-08T15:00:00Z",
  returned_at: null,
  item_title: "The Library Book",
  item_author: "Susan Orlean",
}

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

// vitest's global setup replaces window.localStorage with a vi.fn() mock
// that does not actually persist. Assert against setItem calls.
const setItemMock = window.localStorage.setItem as ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchApiMock.mockReset()
  setItemMock.mockClear()
})

describe("CheckoutSlip", () => {
  it("calls window.print() and remembers the choice when Print is clicked", async () => {
    // happy-dom may not provide window.print as a function; assign a stub
    // before spying so vi.spyOn can wrap it.
    const printStub = vi.fn()
    Object.defineProperty(window, "print", { value: printStub, writable: true, configurable: true })
    const user = userEvent.setup()
    render(<CheckoutSlip checkout={checkout} patron={patron} token="t" />)

    await user.click(screen.getByRole("button", { name: /print checkout slip/i }))

    expect(printStub).toHaveBeenCalledTimes(1)
    expect(setItemMock).toHaveBeenCalledWith("l30.circ.slip.lastChoice", "print")
  })

  it("POSTs to the email-slip endpoint with the checkout id when Email is clicked", async () => {
    fetchApiMock.mockResolvedValueOnce({ message: "Slip emailed.", sent: true })
    const user = userEvent.setup()
    render(<CheckoutSlip checkout={checkout} patron={patron} token="staff-token" />)

    await user.click(screen.getByRole("button", { name: /email checkout slip to patron/i }))

    await waitFor(() => expect(fetchApiMock).toHaveBeenCalledTimes(1))
    const [path, opts] = fetchApiMock.mock.calls[0] as [string, Record<string, unknown>]
    expect(path).toBe("/staff/circulation/email-slip")
    expect(opts).toMatchObject({
      method: "POST",
      token: "staff-token",
      body: { checkout_id: 4242 },
    })
    expect(setItemMock).toHaveBeenCalledWith("l30.circ.slip.lastChoice", "email")
  })

  it("disables Email when the patron has no email on file", () => {
    const noEmailPatron = { ...patron, email: null } as Patron
    render(<CheckoutSlip checkout={checkout} patron={noEmailPatron} token="t" />)

    const emailBtn = screen.getByRole("button", { name: /no email on file/i })
    expect(emailBtn).toBeDisabled()
  })
})
