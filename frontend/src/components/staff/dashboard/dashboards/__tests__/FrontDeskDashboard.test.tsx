/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { it, expect, vi, beforeEach } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import * as api from "@/api/domains/staff/staff-presence-api"

vi.mock("@/api/domains/staff/staff-presence-api")
vi.mock("@/api/fair-scheduling-api", () => ({
  fairSchedulingApi: { getMyShifts: vi.fn().mockResolvedValue({ shifts: [] }) },
}))

vi.mock("../../panels/FrontDeskSearchBar", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskPatronPin", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskState", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskStatusLine", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskQuickActions", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskToday", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskHandoff", () => ({ default: () => null }))
vi.mock("../../panels/FrontDeskOfflineChip", () => ({ default: () => null }))
vi.mock("../../panels/LibraryHeartbeat", () => ({ default: () => null }))
vi.mock("../../panels/StaffMessages", () => ({ default: () => null }))
vi.mock("../../panels/MyCourses", () => ({ default: () => null }))
vi.mock("../../MyShiftsTile", () => ({ default: () => null }))

const counters = vi.hoisted(() => ({ myHoursMounts: 0 }))

vi.mock("../../panels/MyHoursPanel", async () => {
  const React = await import("react")
  function MyHoursPanelStub() {
    React.useEffect(() => {
      counters.myHoursMounts += 1
    }, [])
    return null
  }
  return { default: MyHoursPanelStub }
})

vi.mock("../../panels/ClockInOutButton", async () => {
  const React = await import("react")
  function ClockInOutButtonStub(props: { onPunch?: () => void }) {
    return React.createElement("button", { onClick: () => props.onPunch?.() }, "punch-stub")
  }
  return { default: ClockInOutButtonStub }
})

import FrontDeskDashboard from "../FrontDeskDashboard"

const day = (over: Partial<api.TimesheetDayResponse> = {}): api.TimesheetDayResponse => ({
  shift_date: "2026-06-10", clock_in: null, clock_out: null, breaks: [],
  total_worked_hours: null, total_break_minutes: 0, scheduled_hours: null,
  status: "not_started", ...over,
})

const renderDash = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <FrontDeskDashboard />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  counters.myHoursMounts = 0
  vi.mocked(api.getTimesheetToday).mockReset()
  // Stale cross-day presence: says available even though no punch exists today.
  vi.mocked(api.getMyPresence).mockResolvedValue({
    status: "available", status_changed_at: null, shift_started_at: null, break_started_at: null,
  })
})

it("keeps the Shift section closed when the timesheet says not clocked in, even with stale presence", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day())
  renderDash()
  await waitFor(() => expect(vi.mocked(api.getTimesheetToday)).toHaveBeenCalled())
  const details = screen.getByText("Shift").closest("details")
  await waitFor(() => expect(details?.open).toBe(false))
})

it("opens the Shift section when the timesheet says in progress", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day({ status: "in_progress" }))
  renderDash()
  const details = screen.getByText("Shift").closest("details")
  await waitFor(() => expect(details?.open).toBe(true))
})

it("remounts MyHoursPanel after a punch action", async () => {
  vi.mocked(api.getTimesheetToday).mockResolvedValue(day({ status: "in_progress" }))
  renderDash()
  await waitFor(() => expect(counters.myHoursMounts).toBe(1))
  await userEvent.click(screen.getByRole("button", { name: "punch-stub" }))
  await waitFor(() => expect(counters.myHoursMounts).toBe(2))
})
