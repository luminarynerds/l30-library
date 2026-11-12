/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

// ---------------------------------------------------------------------------
// Types — mirror backend SavedSearchResponse exactly. Keep this in sync with
// /opt/l30/backend/app/schemas/saved_search.py.
// ---------------------------------------------------------------------------

export interface SavedSearch {
  id: string
  name: string
  query: string | null
  filters_json: Record<string, unknown>
  sort_by: string | null
  view_mode: string | null
  notify_on_new: boolean
  notify_in_app: boolean
  notify_email: boolean
  last_run_at: string | null
  created_at: string
  updated_at: string
}

interface SavedSearchListResponse {
  items: SavedSearch[]
  total: number
}

export interface SavedSearchCreateInput {
  name: string
  query?: string | null
  filters_json: Record<string, unknown>
  sort_by?: string | null
  view_mode?: string | null
  notify_on_new?: boolean
  notify_in_app?: boolean
  notify_email?: boolean
}

export interface SavedSearchUpdateInput {
  name?: string
  query?: string | null
  filters_json?: Record<string, unknown>
  sort_by?: string | null
  view_mode?: string | null
  notify_on_new?: boolean
  notify_in_app?: boolean
  notify_email?: boolean
}

const BASE = '/patrons/me/saved-searches'
const LIST_KEY = ['saved-searches'] as const

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSavedSearches(options: { enabled?: boolean } = {}) {
  const queryClient = useQueryClient()
  const enabled = options.enabled !== false

  const listQuery = useQuery({
    queryKey: LIST_KEY,
    queryFn: () => apiClient<SavedSearchListResponse>(BASE),
    enabled,
    // Saved searches are user-edited and not rapidly mutated by background
    // processes, so a 30s stale window is plenty and avoids a refetch on
    // every dialog open.
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: (input: SavedSearchCreateInput) =>
      apiClient<SavedSearch>(BASE, { method: 'POST', body: input }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LIST_KEY })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: SavedSearchUpdateInput }) =>
      apiClient<SavedSearch>(`${BASE}/${id}`, { method: 'PATCH', body: input }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LIST_KEY })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient<void>(`${BASE}/${id}`, { method: 'DELETE', skipJsonParse: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LIST_KEY })
    },
  })

  return {
    savedSearches: listQuery.data?.items ?? [],
    total: listQuery.data?.total ?? 0,
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    refetch: listQuery.refetch,
    create: createMutation,
    update: updateMutation,
    remove: deleteMutation,
  }
}

export async function fetchSavedSearch(id: string): Promise<SavedSearch> {
  return apiClient<SavedSearch>(`${BASE}/${id}`)
}
