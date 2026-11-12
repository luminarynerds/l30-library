/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from "@testing-library/react"
import { it, expect, vi, beforeEach } from "vitest"
import DeskSchedulePanel from "../DeskSchedulePanel"
import * as api from "@/api/domains/staff/staff-presence-api"

vi.mock("@/api/domains/staff/staff-presence-api")

const member = (over: Partial<api.DeskScheduleStaff> = {}): api.DeskScheduleStaff => ({
  staff_id: 1, staff_name: "Robin Reader", scheduled_start: null, scheduled_end: null,
  scheduled_hours: null, shift_type: null, presence_status: "available", clock_in_time: null,
  ...over,
})

const schedule = (over: Partial<api.DeskScheduleResponse> = {}): api.DeskScheduleResponse => ({
  date: "2026-06-10", on_duty: [], on_break: [], scheduled_not_present: [],
  present_unscheduled: [], coverage_note: null, ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
})

it("formats a full ISO clock-in datetime as a local time, not 12:xx AM garbage", async () => {
  const iso = "2026-06-10T14:23:56+00:00"
  vi.mocked(api.getDeskScheduleToday).mockResolvedValue(
    schedule({ on_break: [member({ presence_status: "on_break", clock_in_time: iso })] }),
  )
  render(<DeskSchedulePanel />)
  const expected = new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  expect(await screen.findByText(`(since ${expected})`)).toBeInTheDocument()
})

it("still formats HH:MM:SS schedule times", async () => {
  vi.mocked(api.getDeskScheduleToday).mockResolvedValue(
    schedule({ on_duty: [member({ scheduled_start: "09:00:00", scheduled_end: "17:30:00" })] }),
  )
  render(<DeskSchedulePanel />)
  expect(await screen.findByText("9:00 AM - 5:30 PM")).toBeInTheDocument()
})

it("renders needs_help staff distinctly from Available", async () => {
  vi.mocked(api.getDeskScheduleToday).mockResolvedValue(
    schedule({
      on_duty: [
        member(),
        member({ staff_id: 2, staff_name: "Held Up", presence_status: "needs_help" }),
      ],
    }),
  )
  render(<DeskSchedulePanel />)
  expect(await screen.findByText("Needs help")).toBeInTheDocument()
  expect(screen.getAllByText("Available")).toHaveLength(1)
})

it("keeps the Available badge for unscheduled present staff without needs_help", async () => {
  vi.mocked(api.getDeskScheduleToday).mockResolvedValue(
    schedule({ present_unscheduled: [member()] }),
  )
  render(<DeskSchedulePanel />)
  expect(await screen.findByText("Available")).toBeInTheDocument()
  expect(screen.queryByText("Needs help")).not.toBeInTheDocument()
})
