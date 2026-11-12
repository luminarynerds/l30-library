/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// Types — aligned with backend schemas (reading.py)
export interface ReadingBalance {
  minutes_owed: number
  minutes_logged: number
  minutes_pending: number
  balance: number
  pending_logs: number
}

export interface ReadingLog {
  id: number
  user_id: number
  minutes: number
  book_title: string | null
  notes: string | null
  status: 'pending' | 'approved' | 'rejected'
  logged_at: string
  reviewed_at: string | null
  reviewed_by: number | null
}

export interface ReadingStats {
  streak: number
  longest_streak: number
  xp: number
  level: number
  xp_to_next_level: number
  total_approved_minutes: number
  total_submissions: number
  unique_books: number
  notes_written: number
  last_log_date: string | null
}

export interface ReadingAchievement {
  id: number
  slug: string
  name: string
  description: string
  icon: string
  xp: number
  earned: boolean
  earned_at: string | null
}

export interface CommunityReadingData {
  monthly_minutes: number
  total_minutes: number
  active_readers_this_month: number
  message: string
}

export interface LeaderboardEntry {
  rank: number
  display_name: string
  minutes_read: number
  books_completed: number
  achievements_count: number
}

export interface ReadingLogCreateData {
  minutes: number
  reading_date: string
  book_title?: string
  notes?: string
}

// Reading Balance & Logs
export async function getReadingBalance(): Promise<ReadingBalance> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReadingBalance>('/reading/balance', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function logReading(data: ReadingLogCreateData): Promise<ReadingLog> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReadingLog>('/reading/log', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingLogs(params?: {
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: ReadingLog[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: ReadingLog[]; total: number }>(`/reading/logs${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Stats & Achievements
export async function getMyReadingStats(): Promise<ReadingStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReadingStats>('/reading/my-stats', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingAchievements(): Promise<ReadingAchievement[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReadingAchievement[]>('/reading/achievements', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Community & Leaderboard
export async function getCommunityReadingData(): Promise<CommunityReadingData> {
  const token = getAccessToken()
  try {
    return await fetchApi<CommunityReadingData>('/reading/community', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingLeaderboard(params?: {
  period?: 'day' | 'week' | 'month' | 'year' | 'all'
  limit?: number
}): Promise<LeaderboardEntry[]> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.period) searchParams.set('period', params.period)
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<LeaderboardEntry[]>(`/reading/leaderboard${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Export & Verification
export async function exportReadingReport(params: {
  format: 'pdf' | 'csv'
  start_date?: string
  end_date?: string
}): Promise<Blob> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  searchParams.set('format', params.format)
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)

  const res = await fetch(`${API_BASE}/reading/export?${searchParams}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Export failed')
  return res.blob()
}

export async function verifyReadingCode(code: string): Promise<{ valid: boolean; minutes?: number; message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ valid: boolean; minutes?: number; message: string }>(`/reading/verify/${encodeURIComponent(code)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Staff Review
export async function getPendingReadingLogs(params?: {
  page?: number
  per_page?: number
}): Promise<{ items: (ReadingLog & { user_name: string })[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: (ReadingLog & { user_name: string })[]; total: number }>(`/reading/pending${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function reviewReadingLog(logId: number, data: { status: 'approved' | 'rejected'; notes?: string }): Promise<ReadingLog> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReadingLog>(`/reading/${logId}/review`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingStatistics(): Promise<{
  total_logs: number
  pending_logs: number
  approved_logs: number
  rejected_logs: number
  total_minutes_logged: number
  avg_minutes_per_log: number
}> {
  const token = getAccessToken()
  try {
    return await fetchApi<{
      total_logs: number
      pending_logs: number
      approved_logs: number
      rejected_logs: number
      total_minutes_logged: number
      avg_minutes_per_log: number
    }>('/reading/stats', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}