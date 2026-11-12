/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"
import toast from "react-hot-toast"
import {
  getPendingReservations, getAllReservations, getReservationDetails,
  approveReservation, cancelReservation, checkInReservation, createOverrideBooking,
  type StaffReservationDetail, type StaffOverrideCreate,
} from "../../../../api/staff-rooms-api"

interface UseReservationsOptions {
  token: string | null
  enabled: boolean
  filters: {
    status: string
    dateFrom: string
    dateTo: string
  }
}

export function useReservations({ token, enabled, filters }: UseReservationsOptions) {
  const queryClient = useQueryClient()
  const { status, dateFrom, dateTo } = filters

  const { data: pendingData, isLoading: isLoadingPending, refetch: refetchPending } = useQuery({
    queryKey: ["staff-pending-reservations"],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, page: 1, per_page: 50 }
      return await getPendingReservations(token)
    },
    enabled: !!token && enabled,
  })

  const {
    data: allData,
    isLoading: isLoadingAll,
    refetch: refetchAllQuery,
  } = useQuery({
    queryKey: ["staff-reservations", status, dateFrom, dateTo],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, page: 1, per_page: 50 }
      return await getAllReservations(token, {
        ...(status ? { status_filter: status } : {}),
        ...(dateFrom ? { start_date: dateFrom } : {}),
        ...(dateTo ? { end_date: dateTo } : {}),
      })
    },
    enabled: !!token && enabled,
  })

  const fetchDetails = useCallback(async (reservationId: number): Promise<StaffReservationDetail | null> => {
    if (!token) return null
    try {
      return await getReservationDetails(token, reservationId)
    } catch {
      return null
    }
  }, [token])

  const refetchAll = useCallback(() => {
    refetchAllQuery()
    refetchPending()
  }, [refetchAllQuery, refetchPending])

  const approveMutation = useMutation({
    mutationFn: ({
      reservationId,
      approved,
      rejectionReasonCode,
      rejectionReason,
    }: {
      reservationId: number
      approved: boolean
      rejectionReasonCode?: string
      rejectionReason?: string
    }) =>
      approveReservation(token!, reservationId, {
        approved,
        ...(approved
          ? {}
          : {
              rejection_reason_code: rejectionReasonCode,
              rejection_reason: rejectionReason,
            }),
      }),
    onSuccess: () => {
      toast.success("Reservation updated")
      queryClient.invalidateQueries({ queryKey: ["staff-reservations"] })
      queryClient.invalidateQueries({ queryKey: ["staff-pending-reservations"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const cancelMutation = useMutation({
    mutationFn: ({ reservationId, reason }: { reservationId: number; reason: string }) =>
      cancelReservation(token!, reservationId, reason),
    onSuccess: () => {
      toast.success("Reservation cancelled")
      queryClient.invalidateQueries({ queryKey: ["staff-reservations"] })
      queryClient.invalidateQueries({ queryKey: ["staff-pending-reservations"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const checkInMutation = useMutation({
    mutationFn: (reservationId: number) => checkInReservation(token!, reservationId),
    onSuccess: () => {
      toast.success("Patron checked in")
      queryClient.invalidateQueries({ queryKey: ["staff-reservations"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const createOverrideMutation = useMutation({
    mutationFn: (data: StaffOverrideCreate) => createOverrideBooking(token!, data),
    onSuccess: () => {
      toast.success("Override booking created")
      queryClient.invalidateQueries({ queryKey: ["staff-reservations"] })
      queryClient.invalidateQueries({ queryKey: ["staff-pending-reservations"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return {
    allReservations: allData?.items,
    pendingReservations: pendingData?.items,
    isLoadingAll,
    isLoadingPending,
    refetchAll,
    fetchDetails,
    approveMutation,
    cancelMutation,
    checkInMutation,
    createOverrideMutation,
  }
}
