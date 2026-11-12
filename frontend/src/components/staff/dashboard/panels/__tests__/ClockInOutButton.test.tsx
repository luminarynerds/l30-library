// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { it, expect, vi, beforeEach } from "vitest"
import ClockInOutButton from "../ClockInOutButton"
import * as api from "@/api/domains/staff/staff-presence-api"

vi.mock("@/api/domains/staff/staff-presence-api")

const renderButton = () =>
  render(<ClockInOutButton />, { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> })

const day = (over: Partial<api.TimesheetDayResponse> = {}): api.TimesheetDayResponse => ({
  shift_date: "2026-06-07", clock_in: null, clock_out: null, breaks: [],
  total_worked_hours: null, total_break_minutes: 0, scheduled_hours: null,
  status: "not_started", ...over,
})

beforeEach(() => {
  vi.mocked(api.getMyOpenShifts).mockResolvedValue([])
  vi.mocked(api.getMyPresence).mockResolvedValue({
    status: "off_duty", status_changed_at: null, shift_started_at: null, break_started_at: null,
  })
})

it("shows Not clocked in when timesheet has no clock_in", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())
  renderButton()
  expect(await screen.findByText("Not clocked in")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Clock in" })).toBeInTheDocument()
})

it("shows Clocked in (with time) when timesheet is in_progress", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(
    day({ clock_in: "2026-06-07T13:00:00-04:00", status: "in_progress" }),
  )
  renderButton()
  expect(await screen.findByText(/Clocked in at/)).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Clock out" })).toBeInTheDocument()
})

it("status line is an aria-live region", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())
  const { container } = renderButton()
  await screen.findByText("Not clocked in")
  expect(container.querySelector('[aria-live="polite"]')).toBeTruthy()
})

it("surfaces an error when clocking in fails", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())
  vi.mocked(api.updatePresenceStatus).mockRejectedValue(new Error("boom"))
  renderButton()
  await userEvent.click(await screen.findByRole("button", { name: "Clock in" }))
  expect(await screen.findByRole("status")).toHaveTextContent(/couldn.t/i)
})

it("warns when clock-in didn't record (presence flipped but timesheet still empty)", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())  // stays not_started after toggle
  vi.mocked(api.updatePresenceStatus).mockResolvedValue({
    status: "available", status_changed_at: null, shift_started_at: null, break_started_at: null,
  })
  renderButton()
  await userEvent.click(await screen.findByRole("button", { name: "Clock in" }))
  expect(await screen.findByRole("status")).toHaveTextContent(/didn.t record/i)
})
