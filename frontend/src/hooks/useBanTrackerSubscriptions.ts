/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'
import { API_BASE } from '@/api/types'
import api, { ApiError } from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'

// Closed contract aligned with backend/app/schemas/ban_tracker.py
// (SubscriptionScope / SubscriptionFrequency / SubscriptionBanType).
// Widen only when the phase-3 digest worker is updated to match.
export type SubscriptionScope = 'any' | 'state' | 'catalog'
export type SubscriptionFrequency = 'weekly' | 'daily'
export type SubscriptionBanType = 'banned' | 'restricted' | 'challenged'

export interface BanTrackerSubscription {
  id: number
  scope: SubscriptionScope | string
  state_filter: string | null
  ban_type_filter: SubscriptionBanType | string | null
  frequency: SubscriptionFrequency | string
  is_active: boolean
  last_sent_at: string | null
  created_at: string
}

export interface BanTrackerSubscriptionCreatePayload {
  scope: SubscriptionScope
  state_filter?: string | null
  ban_type_filter?: SubscriptionBanType | null
  frequency: SubscriptionFrequency
}

export interface BanTrackerSubscriptionUpdatePayload {
  scope?: SubscriptionScope
  state_filter?: string | null
  ban_type_filter?: SubscriptionBanType | null
  frequency?: SubscriptionFrequency
  is_active?: boolean
}

const BASE_PATH = `${API_BASE}/ban-tracker/subscriptions`

export async function createSubscription(
  payload: BanTrackerSubscriptionCreatePayload,
): Promise<BanTrackerSubscription> {
  return api.post<BanTrackerSubscription>(BASE_PATH, payload)
}

export async function updateSubscription(
  id: number,
  payload: BanTrackerSubscriptionUpdatePayload,
): Promise<BanTrackerSubscription> {
  return api.patch<BanTrackerSubscription>(`${BASE_PATH}/${id}`, payload)
}

export async function deleteSubscription(id: number): Promise<void> {
  await api.delete<void>(`${BASE_PATH}/${id}`)
}

export function isDuplicateSubscriptionError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 409
}

interface UseBanTrackerSubscriptionsResult {
  subscriptions: BanTrackerSubscription[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export function useBanTrackerSubscriptions(): UseBanTrackerSubscriptionsResult {
  const { isAuthenticated } = useAuth()
  const [subscriptions, setSubscriptions] = useState<BanTrackerSubscription[]>([])
  const [loading, setLoading] = useState<boolean>(isAuthenticated)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!isAuthenticated) {
      setSubscriptions([])
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<BanTrackerSubscription[]>(BASE_PATH)
      setSubscriptions(data ?? [])
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load subscriptions'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      if (!isAuthenticated) {
        if (!cancelled) {
          setSubscriptions([])
          setLoading(false)
          setError(null)
        }
        return
      }
      setLoading(true)
      setError(null)
      try {
        const data = await api.get<BanTrackerSubscription[]>(BASE_PATH)
        if (!cancelled) setSubscriptions(data ?? [])
      } catch (err: unknown) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load subscriptions'
          setError(message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  return { subscriptions, loading, error, refetch }
}
