/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from "@testing-library/react"
import { it, expect, vi, beforeEach, describe } from "vitest"
import MyHoursPanel, { getWeekBounds } from "../MyHoursPanel"
import * as api from "@/api/domains/staff/staff-presence-api"

vi.mock("@/api/domains/staff/staff-presence-api")

function localISO(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const day = (over: Partial<api.TimesheetDayResponse> = {}): api.TimesheetDayResponse => ({
  shift_date: "2026-06-10", clock_in: null, clock_out: null, breaks: [],
  total_worked_hours: null, total_break_minutes: 0, scheduled_hours: null,
  status: "not_started", ...over,
})

const summary = (days: api.TimesheetDayResponse[]): api.TimesheetSummaryResponse => ({
  start_date: days[0]!.shift_date,
  end_date: days[days.length - 1]!.shift_date,
  days,
  total_worked_hours: 8,
  total_scheduled_hours: 8,
  total_break_minutes: 0,
})

describe("getWeekBounds", () => {
  it("anchors the week on the local date, not the UTC date", () => {
    // Tue Jun 9 2026, 11:30pm local. West of UTC the UTC date is already
    // Wed Jun 10; the week must still run local Mon Jun 8 - Sun Jun 14.
    const { monday, sunday } = getWeekBounds(new Date(2026, 5, 9, 23, 30))
    expect(monday).toBe("2026-06-08")
    expect(sunday).toBe("2026-06-14")
  })
})

describe("missing clock-out days", () => {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getTimesheetToday).mockResolvedValue(day({ shift_date: localISO(today) }))
  })

  it("badges a past in_progress day instead of rendering runaway hours", async () => {
    vi.mocked(api.getTimesheetSummary).mockResolvedValue(summary([
      day({ shift_date: localISO(yesterday), status: "in_progress", total_worked_hours: 539.6 }),
      day({ shift_date: localISO(today) }),
    ]))
    render(<MyHoursPanel />)
    expect(await screen.findByText("Missing clock-out")).toBeInTheDocument()
    expect(screen.queryByText(/539\.6/)).not.toBeInTheDocument()
    expect(screen.getByText(/missing a clock-out/i)).toBeInTheDocument()
  })

  it("badges an 'incomplete' day from the post-guard backend payload", async () => {
    vi.mocked(api.getTimesheetSummary).mockResolvedValue(summary([
      day({ shift_date: localISO(yesterday), status: "incomplete", total_worked_hours: 0 }),
      day({ shift_date: localISO(today) }),
    ]))
    render(<MyHoursPanel />)
    expect(await screen.findByText("Missing clock-out")).toBeInTheDocument()
    expect(screen.getByText(/missing a clock-out/i)).toBeInTheDocument()
  })

  it("keeps today's in-progress row labeled in progress, not missing", async () => {
    vi.mocked(api.getTimesheetToday).mockResolvedValue(
      day({ shift_date: localISO(today), status: "in_progress" }),
    )
    vi.mocked(api.getTimesheetSummary).mockResolvedValue(summary([
      day({ shift_date: localISO(today), status: "in_progress", total_worked_hours: 2.5 }),
    ]))
    render(<MyHoursPanel />)
    expect(await screen.findByText("(today - in progress)")).toBeInTheDocument()
    expect(screen.queryByText("Missing clock-out")).not.toBeInTheDocument()
  })
})
