/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Recommendations & Similar Items API Service
 *
 * Handles recommendation engine settings, similarity algorithms,
 * and admin configuration for personalized content suggestions.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { buildQueryString } from '@/lib/api-helpers'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Types ====================

export type SimilarityStrategy = 'subject' | 'author' | 'type' | 'mixed' | 'collaborative' | 'content_based'
export type RecommendationSource = 'catalog' | 'indie' | 'events' | 'all'

export interface RecommendationSettings {
  id: number
  enabled: boolean
  default_strategy: SimilarityStrategy
  default_count: number
  max_count: number
  cache_ttl_minutes: number
  include_indie_books: boolean
  include_events: boolean
  weight_subject: number
  weight_author: number
  weight_type: number
  weight_popularity: number
  weight_recency: number
  min_similarity_score: number
  exclude_mature_content: boolean
  personalization_enabled: boolean
  updated_at: string
  updated_by: string | null
}

export interface SimilarityAlgorithm {
  id: string
  name: string
  description: string
  enabled: boolean
  weight: number
  parameters: Record<string, unknown>
}

export interface RecommendationStats {
  total_recommendations_served: number
  unique_users_served: number
  click_through_rate: number
  average_items_shown: number
  most_recommended_items: RecommendedItem[]
  algorithm_performance: AlgorithmPerformance[]
  recommendations_by_source: { source: string; count: number }[]
  daily_stats: DailyStat[]
}

export interface RecommendedItem {
  item_id: number
  title: string
  times_recommended: number
  click_count: number
  ctr: number
}

export interface AlgorithmPerformance {
  algorithm: string
  recommendations_count: number
  click_through_rate: number
  avg_position: number
}

export interface DailyStat {
  date: string
  recommendations: number
  clicks: number
  ctr: number
}

export interface SimilarItemsPreferences {
  enabled: boolean
  count: 3 | 6 | 9
  strategy: SimilarityStrategy
}

export interface IndieRecommendation {
  id: number
  title: string
  description: string
  cover_url: string | null
  genre: string | null
  author_pen_name: string
  average_rating: number | null
  total_borrows: number
}

// ==================== Admin Settings API ====================

export async function getRecommendationSettings(): Promise<RecommendationSettings> {
  const token = getAccessToken()
  try {
    return await fetchApi<RecommendationSettings>('/admin/recommendations/settings', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch recommendation settings')
    }
    throw error
  }
}

export async function updateRecommendationSettings(
  settings: Partial<RecommendationSettings>
): Promise<RecommendationSettings> {
  const token = getAccessToken()
  try {
    return await fetchApi<RecommendationSettings>('/admin/recommendations/settings', {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: settings,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update recommendation settings')
    }
    throw error
  }
}

export async function getSimilarityAlgorithms(): Promise<SimilarityAlgorithm[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<SimilarityAlgorithm[]>('/admin/recommendations/algorithms', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch similarity algorithms')
    }
    throw error
  }
}

export async function updateSimilarityAlgorithm(
  algorithmId: string,
  updates: Partial<SimilarityAlgorithm>
): Promise<SimilarityAlgorithm> {
  const token = getAccessToken()
  try {
    return await fetchApi<SimilarityAlgorithm>(`/admin/recommendations/algorithms/${algorithmId}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: updates,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update similarity algorithm')
    }
    throw error
  }
}

export async function getRecommendationStats(
  days: number = 30
): Promise<RecommendationStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<RecommendationStats>(`/admin/recommendations/stats?days=${days}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch recommendation statistics')
    }
    throw error
  }
}

export async function clearRecommendationCache(): Promise<{ cleared: number; message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ cleared: number; message: string }>('/admin/recommendations/cache/clear', {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to clear recommendation cache')
    }
    throw error
  }
}

export async function rebuildRecommendationIndex(): Promise<{ status: string; message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ status: string; message: string }>('/admin/recommendations/index/rebuild', {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to rebuild recommendation index')
    }
    throw error
  }
}

// ==================== Public Recommendation API ====================

export async function getPersonalizedRecommendations(
  limit: number = 10,
  source: RecommendationSource = 'all'
): Promise<IndieRecommendation[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<IndieRecommendation[]>(
      `/indie/recommendations?limit=${limit}&source=${source}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch personalized recommendations')
    }
    throw error
  }
}

export async function getTrendingItems(limit: number = 20): Promise<IndieRecommendation[]> {
  try {
    return await fetchApi<IndieRecommendation[]>(`/indie/trending?limit=${limit}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch trending items')
    }
    throw error
  }
}

export async function getTopRatedItems(
  limit: number = 20,
  minRatings: number = 5
): Promise<IndieRecommendation[]> {
  try {
    return await fetchApi<IndieRecommendation[]>(
      `/indie/top-rated?limit=${limit}&min_ratings=${minRatings}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch top-rated items')
    }
    throw error
  }
}

export async function getSimilarItems(
  itemId: number,
  limit: number = 10,
  strategy?: SimilarityStrategy
): Promise<IndieRecommendation[]> {
  const queryString = buildQueryString({ limit, strategy })

  try {
    return await fetchApi<IndieRecommendation[]>(`/indie/similar-to/${itemId}${queryString}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch similar items')
    }
    throw error
  }
}

export async function getItemsByGenre(
  genre: string,
  limit: number = 20,
  sortBy: 'rating' | 'popular' | 'new' = 'rating'
): Promise<IndieRecommendation[]> {
  try {
    return await fetchApi<IndieRecommendation[]>(
      `/indie/by-genre/${encodeURIComponent(genre)}?limit=${limit}&sort_by=${sortBy}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch items by genre')
    }
    throw error
  }
}

// ==================== User Preferences API ====================

export function getUserSimilarItemsPreferences(): SimilarItemsPreferences {
  const defaultPrefs: SimilarItemsPreferences = {
    enabled: true,
    count: 3,
    strategy: 'mixed',
  }

  try {
    const stored = localStorage.getItem('similarItemsPreferences')
    if (stored) {
      return { ...defaultPrefs, ...JSON.parse(stored) }
    }
  } catch (err: unknown) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
  }

  return defaultPrefs
}

export function saveUserSimilarItemsPreferences(prefs: SimilarItemsPreferences): void {
  try {
    localStorage.setItem('similarItemsPreferences', JSON.stringify(prefs))
  } catch (err: unknown) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
  }
}

// ==================== Helper Functions ====================

export function getStrategyDisplayName(strategy: SimilarityStrategy): string {
  const names: Record<SimilarityStrategy, string> = {
    subject: 'Subject-Based',
    author: 'Same Author',
    type: 'Same Format',
    mixed: 'Mixed (Recommended)',
    collaborative: 'Collaborative Filtering',
    content_based: 'Content Analysis',
  }
  return names[strategy] || strategy
}

export function getStrategyDescription(strategy: SimilarityStrategy): string {
  const descriptions: Record<SimilarityStrategy, string> = {
    subject: 'Finds items with similar subjects and topics',
    author: 'Shows other works by the same author',
    type: 'Recommends items of the same format (book, DVD, etc.)',
    mixed: 'Combines multiple strategies for balanced recommendations',
    collaborative: 'Based on what similar users have enjoyed',
    content_based: 'Analyzes content features for deep similarity matching',
  }
  return descriptions[strategy] || ''
}
