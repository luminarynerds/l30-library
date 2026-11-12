/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'

export interface TimelineBucket {
  month: string
  banned: number
  restricted: number
  challenged: number
  pending: number
}

interface TimelineResponse {
  buckets: TimelineBucket[]
}

interface UseBanTrackerTimelineArgs {
  state?: string
  banType?: string
  reasonCategory?: string
  source?: string
}

export function useBanTrackerTimeline({
  state,
  banType,
  reasonCategory,
  source,
}: UseBanTrackerTimelineArgs) {
  const [buckets, setBuckets] = useState<TimelineBucket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams()
        if (state) params.set('state', state)
        if (banType) params.set('ban_type', banType)
        if (reasonCategory) params.set('reason_category', reasonCategory)
        if (source) params.set('source', source)
        const qs = params.toString()
        const url = `${API_BASE}/ban-tracker/public/timeline${qs ? `?${qs}` : ''}`
        const data: TimelineResponse = await api.get(url)
        if (!cancelled) setBuckets(data.buckets ?? [])
      } catch (err: unknown) {
        if (!cancelled) {
          const e = err as { message?: string }
          setError(e?.message ?? 'Failed to load timeline')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [state, banType, reasonCategory, source, reloadKey])

  const refetch = () => setReloadKey((k) => k + 1)

  return { buckets, loading, error, refetch }
}
