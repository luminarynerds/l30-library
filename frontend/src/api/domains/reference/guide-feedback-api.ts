/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types for guide feedback
export type FeedbackType = 'helpful' | 'not_helpful' | 'outdated' | 'broken_link' | 'suggestion' | 'content_request';
export interface GuideFeedbackSubmit {
  content_type: string
  content_id: number
  page_url?: string
  feedback_type: FeedbackType
  was_helpful?: boolean
  comments?: string
  what_looking_for?: string
  suggestion?: string
  email?: string
}

export interface GuideFeedbackResponse {
  id: number
  content_type: string
  content_id: number
  feedback_type: FeedbackType
  was_helpful?: boolean
  comments?: string
  what_looking_for?: string
  suggestion?: string
  email?: string
  created_at: string
}

export async function submitGuideFeedback(
  guideId: number,
  helpful: boolean,
  comment?: string
): Promise<GuideFeedbackResponse> {
  const token = getAccessToken()

  const feedbackData: GuideFeedbackSubmit = {
    content_type: 'guide',
    content_id: guideId,
    feedback_type: helpful ? 'helpful' : 'not_helpful',
    was_helpful: helpful,
    ...(comment ? { comments: comment } : {}),
  }

  try {
    return await fetchApi<GuideFeedbackResponse>('/legal/feedback', {
      method: 'POST',
      body: feedbackData,
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit feedback')
    }
    throw error
  }
}

export async function recordGuideHelpful(guideId: number, wasHelpful: boolean): Promise<{ status: string }> {
  try {
    const response = await fetchApi<{ status: string }>(`/legal/guides/${guideId}/helpful?was_helpful=${wasHelpful}`, {
      method: 'POST',
    })
    return response
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record feedback')
    }
    throw error
  }
}
