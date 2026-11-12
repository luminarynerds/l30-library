/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'

interface HubFavoriteResponse {
  id: string
  hub_slug: string
  item_path: string
  created_at: string
}

/**
 * Server-backed favorites across ALL hubs for the current user. `/hub-favorites`
 * returns every favorite when no `hub_slug` filter is passed. The store is shared
 * with the Star toggles on hub-page item cards (see useHubFavorites), so starring
 * on a hub page surfaces the item here. Pass a changing `refreshKey` (e.g. the
 * current pathname) to refetch on navigation. Also refetches immediately when a
 * hub-page Star toggle dispatches the `staff-favorites-changed` window event, so
 * a freshly starred item appears without waiting for navigation.
 */
export const STAFF_FAVORITES_CHANGED_EVENT = 'staff-favorites-changed'

export function useAllHubFavorites(refreshKey?: unknown): { favoritePaths: string[]; isLoading: boolean } {
  const { isAuthenticated } = useAuth()
  const [favoritePaths, setFavoritePaths] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(isAuthenticated)
  const [version, setVersion] = useState(0)

  // Refetch when a Star is toggled anywhere in the app (current-page edits don't
  // change the pathname, so this is what makes them show up live in the rail).
  useEffect(() => {
    const bump = () => setVersion((v) => v + 1)
    window.addEventListener(STAFF_FAVORITES_CHANGED_EVENT, bump)
    return () => window.removeEventListener(STAFF_FAVORITES_CHANGED_EVENT, bump)
  }, [])

  useEffect(() => {
    let cancelled = false
    if (!isAuthenticated) {
      setFavoritePaths([])
      setIsLoading(false)
      return () => { cancelled = true }
    }
    setIsLoading(true)
    apiClient<HubFavoriteResponse[]>('/hub-favorites', { method: 'GET' })
      .then((rows) => {
        if (cancelled) return
        const seen = new Set<string>()
        const paths: string[] = []
        for (const r of rows ?? []) {
          if (!seen.has(r.item_path)) { seen.add(r.item_path); paths.push(r.item_path) }
        }
        setFavoritePaths(paths)
      })
      .catch(() => { if (!cancelled) setFavoritePaths([]) })
      .finally(() => { if (!cancelled) setIsLoading(false) })
    return () => { cancelled = true }

  }, [isAuthenticated, refreshKey, version])

  return { favoritePaths, isLoading }
}
