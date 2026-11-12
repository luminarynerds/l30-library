/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import toast from "react-hot-toast"
import {
  getStaffRooms, createStaffRoom, updateStaffRoom,
  deactivateStaffRoom, activateStaffRoom,
  type StaffRoom, type StaffRoomCreate, type StaffRoomUpdate,
} from "../../../../api/staff-rooms-api"

interface UseRoomsOptions {
  token: string | null
  enabled: boolean
  filters: {
    roomTypeFilter: string
    includeInactive: boolean
  }
}

export function useRooms({ token, enabled, filters }: UseRoomsOptions) {
  const queryClient = useQueryClient()
  const { roomTypeFilter, includeInactive } = filters

  const { data: roomsData, isLoading, refetch } = useQuery({
    queryKey: ["staff-rooms", roomTypeFilter, includeInactive],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, page: 1, per_page: 50 }
      return await getStaffRooms(token, {
        include_inactive: includeInactive,
        ...(roomTypeFilter ? { room_type: roomTypeFilter } : {}),
      })
    },
    enabled: !!token && enabled,
  })

  const createRoomMutation = useMutation({
    mutationFn: (data: StaffRoomCreate) => createStaffRoom(token!, data),
    onSuccess: () => {
      toast.success("Room created successfully")
      queryClient.invalidateQueries({ queryKey: ["staff-rooms"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const updateRoomMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: StaffRoomUpdate }) =>
      updateStaffRoom(token!, id, data),
    onSuccess: () => {
      toast.success("Room updated successfully")
      queryClient.invalidateQueries({ queryKey: ["staff-rooms"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const deactivateRoomMutation = useMutation({
    mutationFn: (roomId: number) => deactivateStaffRoom(token!, roomId),
    onSuccess: () => {
      toast.success("Room deactivated")
      queryClient.invalidateQueries({ queryKey: ["staff-rooms"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const activateRoomMutation = useMutation({
    mutationFn: (roomId: number) => activateStaffRoom(token!, roomId),
    onSuccess: () => {
      toast.success("Room activated")
      queryClient.invalidateQueries({ queryKey: ["staff-rooms"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSaveRoom = (editingRoom: StaffRoom | null, data: StaffRoomCreate | StaffRoomUpdate) => {
    if (editingRoom) {
      updateRoomMutation.mutate({ id: editingRoom.id, data })
    } else {
      createRoomMutation.mutate(data as StaffRoomCreate)
    }
  }

  return {
    rooms: roomsData?.items,
    isLoading,
    refetch,
    createRoomMutation,
    updateRoomMutation,
    deactivateRoomMutation,
    activateRoomMutation,
    handleSaveRoom,
  }
}
