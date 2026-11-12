/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Reading Minutes Types ====================

export interface ReadingMinutesStatus {
  minutes_owed: number
  minutes_logged: number
  minutes_remaining: number
  is_clear: boolean
  message: string
}

export interface LogReadingRequest {
  minutes: number // 5-120 minutes
  note?: string // Optional note, max 200 characters
}

export interface LogReadingResponse {
  minutes_logged: number
  minutes_remaining: number
  is_clear: boolean
  message: string
}

export interface LeaderboardEntry {
  rank: number
  name: string
  minutes_logged: number
  is_you: boolean
}

// ==================== Reading Minutes Functions ====================

export async function getReadingMinutesStatus(token: string): Promise<ReadingMinutesStatus> {
  try {
    return await fetchApi<ReadingMinutesStatus>('/reading-minutes/status', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch reading minutes status')
    }
    throw new Error('Failed to fetch reading minutes status')
  }
}

export async function logReadingTime(
  token: string,
  data: LogReadingRequest
): Promise<LogReadingResponse> {
  try {
    return await fetchApi<LogReadingResponse>('/reading-minutes/log', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to log reading time')
    }
    throw new Error('Failed to log reading time')
  }
}

export async function getReadingLeaderboard(token: string): Promise<LeaderboardEntry[]> {
  try {
    return await fetchApi<LeaderboardEntry[]>('/reading-minutes/leaderboard', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch leaderboard')
    }
    throw new Error('Failed to fetch leaderboard')
  }
}
