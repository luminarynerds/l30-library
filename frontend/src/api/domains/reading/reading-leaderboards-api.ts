/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================

export type LeaderboardType =
  | 'minutes_read'
  | 'books_completed'
  | 'pages_read'
  | 'consistency'
  | 'points'

export type LeaderboardStatus = 'draft' | 'active' | 'completed' | 'archived'

export interface LeaderboardEntry {
  id: number
  leaderboard_id: number
  user_id: number
  rank: number
  score: number
  display_name: string | null
  updated_at: string
}

export interface Leaderboard {
  id: number
  name: string
  description: string | null
  leaderboard_type: LeaderboardType
  program_id: number | null
  age_group: string | null
  status: LeaderboardStatus
  start_date: string
  end_date: string | null
  is_public: boolean
  created_at: string
  updated_at: string
  participant_count: number
  total_entries: number
}

export interface PaginatedLeaderboards {
  items: Leaderboard[]
  total: number
  limit: number
  offset: number
}

export interface LeaderboardWithEntries extends Leaderboard {
  entries: LeaderboardEntry[]
}

export interface UserRank {
  rank: number
  score: number
  percentile: number
  total_participants: number
  is_top_10: boolean
}

export interface TopEntries {
  leaderboard_id: number
  entries: LeaderboardEntry[]
  limit: number
}

// ==================== API Functions ====================

export async function listActiveLeaderboards(params?: {
  leaderboard_type?: LeaderboardType
  limit?: number
  offset?: number
}): Promise<PaginatedLeaderboards> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.leaderboard_type) searchParams.set('leaderboard_type', params.leaderboard_type)
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.offset) searchParams.set('offset', params.offset.toString())
  const query = searchParams.toString() ? '?' + searchParams.toString() : ''
  try {
    return await fetchApi<PaginatedLeaderboards>('/reading/leaderboards/' + query, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Request failed')
    throw error
  }
}

export async function getLeaderboardEntries(
  leaderboardId: number,
  params?: { limit?: number; offset?: number }
): Promise<LeaderboardWithEntries> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.offset) searchParams.set('offset', params.offset.toString())
  const query = searchParams.toString() ? '?' + searchParams.toString() : ''
  try {
    return await fetchApi<LeaderboardWithEntries>('/reading/leaderboards/' + leaderboardId + query, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Request failed')
    throw error
  }
}

export async function getMyRank(leaderboardId: number): Promise<UserRank> {
  const token = getAccessToken()
  try {
    return await fetchApi<UserRank>('/reading/leaderboards/' + leaderboardId + '/my-rank', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Request failed')
    throw error
  }
}

export async function getTopEntries(
  leaderboardId: number,
  limit?: number
): Promise<TopEntries> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (limit) searchParams.set('limit', limit.toString())
  const query = searchParams.toString() ? '?' + searchParams.toString() : ''
  try {
    return await fetchApi<TopEntries>('/reading/leaderboards/' + leaderboardId + '/top' + query, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Request failed')
    throw error
  }
}
