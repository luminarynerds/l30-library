// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import { PatronHoldsTab } from "../PatronHoldsTab"
import type { Hold } from "../../../../../api/api"

function hold(partial: Partial<Hold>): Hold {
  return {
    id: 1, user_id: 1, item_id: 10, status: "pending", position: 1,
    created_at: "2026-05-01T00:00:00Z", notified_at: null, expires_at: null,
    cancelled_at: null, cancellation_reason: null, cancelled_by: null,
    item_title: "Test Title", item_author: "Author",
    ...partial,
  } as Hold
}

describe("PatronHoldsTab — Check Out button", () => {
  it("shows Check Out only for ready holds", () => {
    const onCheckoutHold = vi.fn().mockResolvedValue(undefined)
    render(
      <PatronHoldsTab
        holds={[
          hold({ id: 1, status: "ready", is_ready: true }),
          hold({ id: 2, status: "pending" }),
        ]}
        onCheckoutHold={onCheckoutHold}
      />,
    )
    expect(screen.getAllByRole("button", { name: /check out/i })).toHaveLength(1)
  })

  it("invokes onCheckoutHold with the hold id when clicked", async () => {
    const onCheckoutHold = vi.fn().mockResolvedValue(undefined)
    render(
      <PatronHoldsTab
        holds={[hold({ id: 7, status: "ready", is_ready: true })]}
        onCheckoutHold={onCheckoutHold}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /check out/i }))
    expect(onCheckoutHold).toHaveBeenCalledWith(7)
  })

  it("does not render Check Out when onCheckoutHold is not provided", () => {
    render(<PatronHoldsTab holds={[hold({ id: 1, status: "ready", is_ready: true })]} />)
    expect(screen.queryByRole("button", { name: /check out/i })).toBeNull()
  })

  it("disables the Check Out button while the checkout is in flight", async () => {
    let resolve!: () => void
    const onCheckoutHold = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
    render(
      <PatronHoldsTab
        holds={[hold({ id: 9, status: "ready", is_ready: true })]}
        onCheckoutHold={onCheckoutHold}
      />,
    )
    const btn = screen.getByRole("button", { name: /check out/i })
    await userEvent.click(btn)
    expect(btn).toBeDisabled()
    resolve()
    await waitFor(() => expect(btn).not.toBeDisabled())
  })
})
