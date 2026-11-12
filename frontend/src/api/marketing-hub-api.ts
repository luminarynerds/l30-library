/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Marketing Hub API Service
 *
 * Handles AI-powered marketing content generation endpoints:
 * - Content generation with program/event context
 * - Saving and managing generated content history
 * - Fetching programs and events for context pickers
 * - AI service availability checks
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type ContentType = 'social_post' | 'newsletter' | 'flyer' | 'program_promo' | 'event_promo'

export interface GenerateContentRequest {
  content_type: ContentType
  instructions: string
  program_id?: number
  event_id?: number
  tone?: string
  temperature?: number
}

export interface GenerateContentResponse {
  success: boolean
  generated_text: string | null
  content_type: string
  model_used: string | null
  generation_time_ms: number | null
  context_data: Record<string, unknown> | null
  error: string | null
}

export interface SaveContentRequest {
  content_type: string
  title?: string
  generated_text: string
  user_prompt: string
  model_used?: string
  temperature?: number
  generation_time_ms?: number
  program_id?: number
  event_id?: number
  context_data?: Record<string, unknown>
}

export interface SavedContent {
  id: number
  content_type: string
  title: string | null
  generated_text: string
  user_prompt: string
  model_used: string | null
  temperature: number
  generation_time_ms: number | null
  program_id: number | null
  event_id: number | null
  context_data: Record<string, unknown> | null
  is_favorite: boolean
  created_at: string
}

export interface SavedContentListResponse {
  items: SavedContent[]
  total: number
}

export interface ProgramSummary {
  id: number
  name: string
  program_type: string
  age_group: string | null
  start_date: string
  end_date: string
  is_active: boolean
}

export interface EventSummary {
  id: number
  name: string
  start_time: string | null
  location: string | null
}

export interface AIStatusResponse {
  available: boolean
  models: string[]
}

// ==================== Content Type Helpers ====================

export const CONTENT_TYPE_OPTIONS: { value: ContentType; label: string; description: string }[] = [
  { value: 'social_post', label: 'Social Media Post', description: 'Bluesky, Mastodon posts' },
  { value: 'newsletter', label: 'Newsletter Content', description: 'Email newsletter sections and articles' },
  { value: 'flyer', label: 'Flyer Copy', description: 'Headlines and body text for printed flyers' },
  { value: 'program_promo', label: 'Program Promotion', description: 'Reading program promotional content' },
  { value: 'event_promo', label: 'Event Promotion', description: 'Event announcements and promotions' },
]

export function getContentTypeLabel(type: string): string {
  const option = CONTENT_TYPE_OPTIONS.find((o) => o.value === type)
  return option?.label ?? type.replace(/_/g, ' ')
}

// ==================== API Functions ====================

export async function checkAIStatus(authToken: string): Promise<AIStatusResponse> {
  try {
    return await fetchApi<AIStatusResponse>('/marketing-hub/ai-status', {
      token: authToken,
    })
  } catch {
    return { available: false, models: [] }
  }
}

export async function generateContent(
  authToken: string,
  data: GenerateContentRequest,
): Promise<GenerateContentResponse> {
  try {
    return await fetchApi<GenerateContentResponse>('/marketing-hub/generate', {
      method: 'POST',
      token: authToken,
      body: data,
      timeoutMs: 120000,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate content')
    }
    throw error
  }
}

export async function saveContent(
  authToken: string,
  data: SaveContentRequest,
): Promise<SavedContent> {
  try {
    return await fetchApi<SavedContent>('/marketing-hub/save', {
      method: 'POST',
      token: authToken,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to save content')
    }
    throw error
  }
}

export async function getSavedContent(
  authToken: string,
  options?: {
    content_type?: ContentType
    favorites_only?: boolean
    limit?: number
    offset?: number
  },
): Promise<SavedContentListResponse> {
  const params = new URLSearchParams()
  if (options?.content_type) params.set('content_type', options.content_type)
  if (options?.favorites_only) params.set('favorites_only', 'true')
  if (options?.limit) params.set('limit', options.limit.toString())
  if (options?.offset) params.set('offset', options.offset.toString())
  const queryString = params.toString() ? `?${params.toString()}` : ''
  try {
    return await fetchApi<SavedContentListResponse>(`/marketing-hub/history${queryString}`, {
      token: authToken,
    })
  } catch {
    return { items: [], total: 0 }
  }
}

export async function deleteSavedContent(
  authToken: string,
  contentId: number,
): Promise<void> {
  try {
    await fetchApi(`/marketing-hub/history/${contentId}`, {
      method: 'DELETE',
      token: authToken,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete content')
    }
    throw error
  }
}

export async function toggleFavorite(
  authToken: string,
  contentId: number,
): Promise<{ id: number; is_favorite: boolean }> {
  try {
    return await fetchApi<{ id: number; is_favorite: boolean }>(
      `/marketing-hub/history/${contentId}/favorite`,
      {
        method: 'PUT',
        token: authToken,
      },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to toggle favorite')
    }
    throw error
  }
}

export async function getPrograms(
  authToken: string,
  activeOnly: boolean = true,
): Promise<ProgramSummary[]> {
  try {
    return await fetchApi<ProgramSummary[]>(
      `/marketing-hub/programs?active_only=${activeOnly}`,
      { token: authToken },
    )
  } catch {
    return []
  }
}

export async function getEvents(
  authToken: string,
  upcomingOnly: boolean = true,
): Promise<EventSummary[]> {
  try {
    return await fetchApi<EventSummary[]>(
      `/marketing-hub/events?upcoming_only=${upcomingOnly}`,
      { token: authToken },
    )
  } catch {
    return []
  }
}
