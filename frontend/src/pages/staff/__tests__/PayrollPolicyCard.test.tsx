// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
/// <reference types="@testing-library/jest-dom" />
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { it, expect, vi, beforeEach, describe } from "vitest"
import { PayrollPolicyCard } from "../StaffPayRatesPage"
import * as api from "@/api/fair-scheduling-api"

vi.mock("@/api/fair-scheduling-api")

const policy: api.PayrollPolicy = {
  overtime_multiplier: 1.5,
  holiday_multiplier: 2,
  weekend_differential: 1.1,
  evening_differential: 1.15,
  default_ot_threshold_hours: 40,
  evening_start_local: "18:00:00",
  updated_by_id: null,
  updated_at: "2026-06-10T12:00:00Z",
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getPayrollPolicy).mockResolvedValue(policy)
})

describe("read view", () => {
  it("renders the six policy values in plain language", async () => {
    render(<PayrollPolicyCard />)
    expect(await screen.findByText(/Overtime pays 1\.5x after 40 hrs\/week/)).toBeInTheDocument()
    expect(screen.getByText(/Holiday shifts pay 2x/)).toBeInTheDocument()
    expect(screen.getByText(/Weekend differential 1\.1x/)).toBeInTheDocument()
    expect(screen.getByText(/Evening differential 1\.15x after 6:00 PM/)).toBeInTheDocument()
    expect(screen.getByText(/keep the rates they were generated with/)).toBeInTheDocument()
  })

  it("shows an inline error when the policy fails to load", async () => {
    vi.mocked(api.getPayrollPolicy).mockRejectedValue(new Error("boom"))
    render(<PayrollPolicyCard />)
    expect(await screen.findByText(/Couldn't load the payroll policy/)).toBeInTheDocument()
  })
})

describe("edit form validation", () => {
  it("rejects an out-of-bounds multiplier with an inline accessible error", async () => {
    const user = userEvent.setup()
    render(<PayrollPolicyCard />)
    await user.click(await screen.findByRole("button", { name: "Edit policy" }))

    const input = screen.getByLabelText("Overtime multiplier")
    await user.clear(input)
    await user.type(input, "5")
    await user.click(screen.getByRole("button", { name: "Review changes" }))

    const error = await screen.findByText(/between 1\.00 and 3\.00/)
    expect(input).toHaveAttribute("aria-invalid", "true")
    expect(input).toHaveAttribute("aria-describedby", error.id)
    expect(api.updatePayrollPolicy).not.toHaveBeenCalled()
  })

  it("rejects an evening start outside the 4 PM to 10 PM window", async () => {
    const user = userEvent.setup()
    render(<PayrollPolicyCard />)
    await user.click(await screen.findByRole("button", { name: "Edit policy" }))

    const input = screen.getByLabelText("Evening starts at")
    await user.clear(input)
    await user.type(input, "23:00")
    await user.click(screen.getByRole("button", { name: "Review changes" }))

    const error = await screen.findByText(/between 4:00 PM and 10:00 PM/)
    expect(input).toHaveAttribute("aria-invalid", "true")
    expect(input).toHaveAttribute("aria-describedby", error.id)
    expect(api.updatePayrollPolicy).not.toHaveBeenCalled()
  })
})

describe("save flow", () => {
  it("saves only after an explicit confirm step and re-renders the new values", async () => {
    const user = userEvent.setup()
    vi.mocked(api.updatePayrollPolicy).mockResolvedValue({
      ...policy,
      overtime_multiplier: 1.75,
      updated_by_id: 7,
    })
    render(<PayrollPolicyCard />)
    await user.click(await screen.findByRole("button", { name: "Edit policy" }))

    const input = screen.getByLabelText("Overtime multiplier")
    await user.clear(input)
    await user.type(input, "1.75")
    await user.click(screen.getByRole("button", { name: "Review changes" }))

    // Confirm step shows before anything is written.
    expect(await screen.findByText(/Save these payroll policy values\?/)).toBeInTheDocument()
    expect(api.updatePayrollPolicy).not.toHaveBeenCalled()

    await user.click(screen.getByRole("button", { name: "Confirm and save" }))

    expect(await screen.findByText(/Overtime pays 1\.75x after 40 hrs\/week/)).toBeInTheDocument()
    expect(api.updatePayrollPolicy).toHaveBeenCalledWith(
      expect.objectContaining({ overtime_multiplier: 1.75 }),
    )
  })

  it("backing out of the confirm step does not save", async () => {
    const user = userEvent.setup()
    render(<PayrollPolicyCard />)
    await user.click(await screen.findByRole("button", { name: "Edit policy" }))
    await user.click(screen.getByRole("button", { name: "Review changes" }))
    await user.click(await screen.findByRole("button", { name: "Go back" }))

    expect(screen.getByRole("button", { name: "Review changes" })).toBeInTheDocument()
    expect(api.updatePayrollPolicy).not.toHaveBeenCalled()
  })

  it("surfaces a server failure as an inline alert, not silence", async () => {
    const user = userEvent.setup()
    vi.mocked(api.updatePayrollPolicy).mockRejectedValue(new Error("422"))
    render(<PayrollPolicyCard />)
    await user.click(await screen.findByRole("button", { name: "Edit policy" }))
    await user.click(screen.getByRole("button", { name: "Review changes" }))
    await user.click(await screen.findByRole("button", { name: "Confirm and save" }))

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent(/Save failed/)
  })
})
