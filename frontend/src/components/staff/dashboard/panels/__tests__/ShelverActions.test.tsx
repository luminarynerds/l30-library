/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { it, expect, vi, beforeEach } from "vitest"
import toast from "react-hot-toast"
import { ApiError } from "@/lib/api-client"
import ShelverActions from "../ShelverActions"
import * as api from "@/api/domains/staff/staff-presence-api"

vi.mock("@/api/domains/staff/staff-presence-api")
vi.mock("react-hot-toast", () => {
  const t = Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() })
  return { default: t }
})

const day = (over: Partial<api.TimesheetDayResponse> = {}): api.TimesheetDayResponse => ({
  shift_date: "2026-06-10", clock_in: null, clock_out: null, breaks: [],
  total_worked_hours: null, total_break_minutes: 0, scheduled_hours: null,
  status: "not_started", ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getMyPresence).mockResolvedValue({
    status: "available", status_changed_at: null, shift_started_at: null, break_started_at: null,
  })
})

it("disables End shift when today's timesheet is not in progress", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())
  render(<ShelverActions />)
  await waitFor(() => expect(vi.mocked(api.getTimesheetToday)).toHaveBeenCalled())
  expect(screen.getByRole("button", { name: /End shift/ })).toBeDisabled()
})

it("ends the shift when clocked in, then disables the button against a second press", async () => {
  vi.mocked(api.getTimesheetToday)
    .mockResolvedValueOnce(day({ status: "in_progress", clock_in: "2026-06-10T13:00:00Z" }))
    .mockResolvedValue(
      day({ status: "completed", clock_in: "2026-06-10T13:00:00Z", clock_out: "2026-06-10T21:00:00Z" }),
    )
  vi.mocked(api.updatePresenceStatus).mockResolvedValue({
    status: "off_duty", status_changed_at: null, shift_started_at: null, break_started_at: null,
  })
  render(<ShelverActions />)
  const btn = screen.getByRole("button", { name: /End shift/ })
  await waitFor(() => expect(btn).toBeEnabled())
  await userEvent.click(btn)
  expect(api.updatePresenceStatus).toHaveBeenCalledWith("off_duty")
  await waitFor(() => expect(btn).toBeDisabled())
  expect(toast.success).toHaveBeenCalled()
})

it("surfaces the backend detail when ending a shift is rejected", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(
    day({ status: "in_progress", clock_in: "2026-06-10T13:00:00Z" }),
  )
  vi.mocked(api.updatePresenceStatus).mockRejectedValue(
    new ApiError("Conflict", 409, "You already clocked out today."),
  )
  render(<ShelverActions />)
  const btn = screen.getByRole("button", { name: /End shift/ })
  await waitFor(() => expect(btn).toBeEnabled())
  await userEvent.click(btn)
  await waitFor(() =>
    expect(toast.error).toHaveBeenCalledWith("You already clocked out today."),
  )
})

it("falls back to a generic message on server errors", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(
    day({ status: "in_progress", clock_in: "2026-06-10T13:00:00Z" }),
  )
  vi.mocked(api.updatePresenceStatus).mockRejectedValue(new Error("network down"))
  render(<ShelverActions />)
  const btn = screen.getByRole("button", { name: /End shift/ })
  await waitFor(() => expect(btn).toBeEnabled())
  await userEvent.click(btn)
  await waitFor(() =>
    expect(toast.error).toHaveBeenCalledWith("Could not end shift. Try again."),
  )
})
