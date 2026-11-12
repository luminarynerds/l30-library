/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen, userEvent } from "@/__tests__/utils/test-utils"
import { ReservationDetailModal } from "../ReservationDetailModal"
import type { StaffReservationDetail } from "../../../../../api/staff-rooms-api"

const reservation: StaffReservationDetail = {
  id: 42,
  room_id: 1,
  start_time: "2026-08-01T10:00:00Z",
  end_time: "2026-08-01T11:00:00Z",
  status: "pending",
  contact_name: "Pat Patron",
  contact_email: "pat@example.com",
}

describe("ReservationDetailModal reject flow", () => {
  it("defaults the reason picker to 'other' and passes the chosen code + label to onReject", async () => {
    const onReject = vi.fn()
    const user = userEvent.setup()

    render(
      <ReservationDetailModal
        reservation={reservation}
        isLoading={false}
        locale="en-US"
        onClose={vi.fn()}
        onApprove={vi.fn()}
        onReject={onReject}
        onCancel={vi.fn()}
        onCheckIn={vi.fn()}
        isApproving={false}
        isCancelling={false}
        isCheckingIn={false}
      />
    )

    await user.click(screen.getByRole("button", { name: /reject/i }))

    const select = await screen.findByLabelText("Reason for rejection")
    expect(select).toHaveValue("other")

    await user.selectOptions(select, "schedule_conflict")

    await user.click(screen.getByRole("button", { name: "Reject reservation" }))

    expect(onReject).toHaveBeenCalledWith("schedule_conflict", "Scheduling conflict")
  })

  it("submits the default 'other' code when staff confirms without changing the picker", async () => {
    const onReject = vi.fn()
    const user = userEvent.setup()

    render(
      <ReservationDetailModal
        reservation={reservation}
        isLoading={false}
        locale="en-US"
        onClose={vi.fn()}
        onApprove={vi.fn()}
        onReject={onReject}
        onCancel={vi.fn()}
        onCheckIn={vi.fn()}
        isApproving={false}
        isCancelling={false}
        isCheckingIn={false}
      />
    )

    await user.click(screen.getByRole("button", { name: /reject/i }))
    await user.click(screen.getByRole("button", { name: "Reject reservation" }))

    expect(onReject).toHaveBeenCalledWith("other", "Other")
  })
})
