/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin Analytics API Service
 *
 * Provides staff/admin endpoints for accessing various analytics dashboards including
 * sharing metrics, circulation stats, reading activity, and more.
 *
 * All endpoints require STAFF+ role authentication.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import type { components } from '@/api/generated/schema';
import { getCurrentLocale } from '@/i18n'

// ==================== Types ====================

export type TrendDirection = components['schemas']['TrendDirection'];
export interface TrendData {
  direction: TrendDirection
  change_percentage: number
  previous_value: number
  current_value: number
}

export interface StatsMetadata {
  generated_at: string
  cached: boolean
  cache_ttl: number
  time_window: string
}

export interface SharedResource {
  resource_id: number
  resource_type: string
  title: string
  author?: string | null
  share_count: number
}

export interface PlatformBreakdown {
  platform: string
  share_count: number
  percentage: number
}

export interface TopSharer {
  user_id: number
  user_name: string
  email: string
  total_shares: number
  favorite_platform?: string | null
}

export interface ShareTrendDataPoint {
  date: string
  total_shares: number
  unique_sharers: number
}

export interface SharingDashboardResponse {
  top_shared_resources: SharedResource[]
  platform_breakdown: PlatformBreakdown[]
  total_shares: number
  unique_sharers: number
  avg_shares_per_user: number
  top_sharers: TopSharer[]
  share_trends: ShareTrendDataPoint[]
  shares_trend?: TrendData | null
  top_platform: string
  top_platform_percentage: number
  metadata: StatsMetadata
}

export interface GetSharingDashboardParams {
  /** Number of days to analyze (7-365, default 30) */
  days?: number
}

// ==================== API Functions ====================

export async function getSharingDashboard(
  params?: GetSharingDashboardParams
): Promise<SharingDashboardResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params?.days !== undefined) {
    // Validate days parameter
    if (params.days < 7 || params.days > 365) {
      throw new Error('Days parameter must be between 7 and 365')
    }
    searchParams.set('days', params.days.toString())
  }

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<SharingDashboardResponse>(
      `/admin/analytics/sharing-dashboard${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 403) {
        throw new Error('Access denied. Staff or admin role required.')
      }
      throw new Error(error.detail || 'Failed to fetch sharing dashboard')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function formatAnalyticsDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function getSharingPlatformColor(platform: string): string {
  const colors: Record<string, string> = {
    facebook: '#1877F2',
    twitter: '#000000',
    linkedin: '#0A66C2',
    reddit: '#FF4500',
    email: '#EA4335',
    copy_link: '#4F46E5',
    whatsapp: '#25D366',
    telegram: '#0088cc',
    pinterest: '#E60023',
    threads: '#000000',
  }
  return colors[platform.toLowerCase()] || '#6B7280'
}

export function getSharingPlatformDisplayName(platform: string): string {
  const names: Record<string, string> = {
    bluesky: 'Bluesky',
    mastodon: 'Mastodon',
    reddit: 'Reddit',
    email: 'Email',
    copy_link: 'Copy Link',
    whatsapp: 'WhatsApp',
    telegram: 'Telegram',
  }
  return names[platform.toLowerCase()] || platform.charAt(0).toUpperCase() + platform.slice(1)
}

export function getTrendDescription(trend: TrendData): string {
  const direction = trend.direction === 'up' ? 'increased' : trend.direction === 'down' ? 'decreased' : 'remained stable'
  const percentage = Math.abs(trend.change_percentage).toFixed(1)

  if (trend.direction === 'stable') {
    return 'Remained stable compared to previous period'
  }

  return `${direction.charAt(0).toUpperCase() + direction.slice(1)} by ${percentage}% compared to previous period`
}

export function getTrendArrow(direction: TrendDirection): string {
  switch (direction) {
    case 'up':
      return '\u2191' // ↑
    case 'down':
      return '\u2193' // ↓
    default:
      return '\u2194' // ↔
  }
}
