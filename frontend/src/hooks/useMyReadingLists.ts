/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import toast from "react-hot-toast"
import { useAuth } from "@/contexts/AuthContext"
import {
  addItemToList,
  createReadingList,
  getListsContainingItem,
  getMyReadingLists,
  removeItemFromList,
  type ReadingListSummary,
} from "@/api/domains/content/reading-lists-api"

const LISTS_KEY = ["my-reading-lists"]

export function useMyReadingLists() {
  const { token } = useAuth()

  return useQuery<ReadingListSummary[]>({
    queryKey: LISTS_KEY,
    queryFn: () => getMyReadingLists(token!),
    enabled: !!token,
    staleTime: 60_000,
  })
}

export function useListsContainingItem(
  catalogItemId: number,
  enabled = true,
) {
  const { token } = useAuth()

  return useQuery<number[]>({
    queryKey: ["lists-containing", catalogItemId],
    queryFn: () => getListsContainingItem(token!, catalogItemId),
    // Gated on `enabled` so catalog grids don't fan out one request per card
    // on mount. Callers pass `open` to defer the lookup until the dropdown is
    // actually opened, avoiding a rate-limit-tripping request burst.
    enabled: !!token && enabled,
    staleTime: 30_000,
  })
}

export function useAddToList() {
  const { token } = useAuth()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({
      listId,
      catalogItemId,
    }: {
      listId: number
      catalogItemId: number
    }) => addItemToList(token!, listId, catalogItemId),
    onSuccess: (_data, { catalogItemId }) => {
      qc.invalidateQueries({ queryKey: LISTS_KEY })
      qc.invalidateQueries({ queryKey: ["lists-containing", catalogItemId] })
      toast.success("Added to list")
    },
    onError: (err: Error) => {
      if (err.message?.includes("already in list")) {
        toast("Already in that list")
      } else {
        toast.error("Could not add to list")
      }
    },
  })
}

export function useRemoveFromList() {
  const { token } = useAuth()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({
      listId,
      catalogItemId,
    }: {
      listId: number
      catalogItemId: number
    }) => removeItemFromList(token!, listId, catalogItemId),
    onSuccess: (_data, { catalogItemId }) => {
      qc.invalidateQueries({ queryKey: LISTS_KEY })
      qc.invalidateQueries({ queryKey: ["lists-containing", catalogItemId] })
      toast.success("Removed from list")
    },
    onError: () => {
      toast.error("Could not remove from list")
    },
  })
}

export function useCreateReadingList() {
  const { token } = useAuth()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({
      name,
      description,
    }: {
      name: string
      description?: string
    }) => createReadingList(token!, name, description),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LISTS_KEY })
      toast.success("List created")
    },
    onError: () => {
      toast.error("Could not create list")
    },
  })
}
