/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useReservations } from "./useReservations"

vi.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("../../../../api/staff-rooms-api", () => ({
  getPendingReservations: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, per_page: 50 }),
  getAllReservations: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, per_page: 50 }),
  getReservationDetails: vi.fn(),
  approveReservation: vi.fn().mockResolvedValue({}),
  cancelReservation: vi.fn(),
  checkInReservation: vi.fn(),
  createOverrideBooking: vi.fn(),
}))

import { approveReservation } from "../../../../api/staff-rooms-api"
const mockedApprove = approveReservation as unknown as ReturnType<typeof vi.fn>

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useReservations approveMutation", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("sends rejection_reason_code and a human-readable rejection_reason when rejecting", async () => {
    const { result } = renderHook(
      () => useReservations({ token: "tok", enabled: false, filters: { status: "", dateFrom: "", dateTo: "" } }),
      { wrapper }
    )

    act(() => {
      result.current.approveMutation.mutate({
        reservationId: 42,
        approved: false,
        rejectionReasonCode: "schedule_conflict",
        rejectionReason: "Scheduling conflict",
      })
    })

    await waitFor(() => expect(mockedApprove).toHaveBeenCalledTimes(1))

    expect(mockedApprove).toHaveBeenCalledWith("tok", 42, {
      approved: false,
      rejection_reason_code: "schedule_conflict",
      rejection_reason: "Scheduling conflict",
    })
  })

  it("omits rejection fields entirely when approving", async () => {
    const { result } = renderHook(
      () => useReservations({ token: "tok", enabled: false, filters: { status: "", dateFrom: "", dateTo: "" } }),
      { wrapper }
    )

    act(() => {
      result.current.approveMutation.mutate({ reservationId: 7, approved: true })
    })

    await waitFor(() => expect(mockedApprove).toHaveBeenCalledTimes(1))

    expect(mockedApprove).toHaveBeenCalledWith("tok", 7, { approved: true })
  })
})
