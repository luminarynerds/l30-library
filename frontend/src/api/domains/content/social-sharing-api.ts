/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Social Sharing API Service
 * Handles all requests to the /sharing endpoints for tracking and analytics
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Enums ====================

export type SharePlatform =
  | 'bluesky'
  | 'mastodon'
  | 'reddit'
  | 'email'
  | 'copy_link'
  | 'whatsapp'
  | 'telegram'

export type ShareableResourceType =
  | 'book'
  | 'event'
  | 'reading_list'
  | 'author_profile'
  | 'staff_pick'

// ==================== Request/Response Types ====================

export interface TrackShareParams {
  resource_type: ShareableResourceType
  resource_id: number
  platform: SharePlatform
}

export interface TrackShareResponse {
  success: boolean
  message: string
  resource_type: ShareableResourceType
  resource_id: number
  platform: SharePlatform
}

export interface ShareStatistics {
  resource_type: ShareableResourceType
  resource_id: number
  total_shares: number
  bluesky_shares: number
  mastodon_shares: number
  reddit_shares: number
  email_shares: number
  copy_link_shares: number
  whatsapp_shares: number
  telegram_shares: number
  last_shared_at: string | null
}

export interface TopSharedResource {
  resource_type: ShareableResourceType
  resource_id: number
  total_shares: number
  last_shared_at: string | null
}

export interface TopSharedResponse {
  count: number
  resources: TopSharedResource[]
}

export interface GetTopSharedParams {
  resource_type?: ShareableResourceType
  limit?: number
}

export interface PlatformBreakdown {
  bluesky: number
  mastodon: number
  reddit: number
  email: number
  copy_link: number
  whatsapp: number
  telegram: number
}

export interface PlatformBreakdownResponse {
  total_shares: number
  by_platform: PlatformBreakdown
  percentages: PlatformBreakdown
}

export interface GetPlatformBreakdownParams {
  resource_type?: ShareableResourceType
}

export interface ShareHistoryItem {
  id: number
  resource_type: ShareableResourceType
  resource_id: number
  platform: SharePlatform
  is_public_resource: boolean
  created_at: string
}

export interface ShareHistoryResponse {
  total_count: number
  offset: number
  limit: number
  shares: ShareHistoryItem[]
}

export interface GetShareHistoryParams {
  limit?: number
  offset?: number
}

// ==================== API Functions ====================

export async function trackShareEvent(params: TrackShareParams): Promise<TrackShareResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams({
    resource_type: params.resource_type,
    resource_id: params.resource_id.toString(),
    platform: params.platform,
  })

  try {
    return await fetchApi<TrackShareResponse>(
      `/sharing/track?${searchParams}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to track share event')
    }
    throw error
  }
}

export async function getShareStatistics(
  resourceType: ShareableResourceType,
  resourceId: number
): Promise<ShareStatistics> {
  const token = getAccessToken()

  try {
    return await fetchApi<ShareStatistics>(
      `/sharing/stats/${resourceType}/${resourceId}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch share statistics')
    }
    throw error
  }
}

export async function getTopSharedResources(
  params?: GetTopSharedParams
): Promise<TopSharedResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params?.resource_type) {
    searchParams.set('resource_type', params.resource_type)
  }
  if (params?.limit !== undefined) {
    searchParams.set('limit', params.limit.toString())
  }

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<TopSharedResponse>(
      `/sharing/analytics/top-shared${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch top shared resources')
    }
    throw error
  }
}

export async function getPlatformBreakdown(
  params?: GetPlatformBreakdownParams
): Promise<PlatformBreakdownResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params?.resource_type) {
    searchParams.set('resource_type', params.resource_type)
  }

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<PlatformBreakdownResponse>(
      `/sharing/analytics/platform-breakdown${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch platform breakdown')
    }
    throw error
  }
}

export async function getUserShareHistory(
  params?: GetShareHistoryParams
): Promise<ShareHistoryResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params?.limit !== undefined) {
    searchParams.set('limit', params.limit.toString())
  }
  if (params?.offset !== undefined) {
    searchParams.set('offset', params.offset.toString())
  }

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<ShareHistoryResponse>(
      `/sharing/user/share-history${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch share history')
    }
    throw error
  }
}
