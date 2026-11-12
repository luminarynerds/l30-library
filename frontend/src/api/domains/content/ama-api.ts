/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AMA (Ask Me Anything) API Client
 * Proxied through L30 backend → MetisLib AMA service.
 * Endpoints: /api/v1/amas/*
 */

import { fetchApi, type RequestOptions } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

function authOpts(extra?: Partial<RequestOptions>): RequestOptions {
  const token = getAccessToken()
  return { ...(token ? { token } : {}), ...extra } as RequestOptions
}

// ==================== Types ====================

export type AmaSessionStatus = 'upcoming' | 'live' | 'grace_period' | 'archived'

export interface AmaAuthorInfo {
  indie_author_id: number | null
  pen_name: string | null
  bio: string | null
  profile_image_url: string | null
  guest_author_name: string | null
  guest_author_bio: string | null
  guest_author_photo_url: string | null
}

export interface AmaSession {
  id: number
  title: string
  // Present on single-session responses; omitted by the list endpoint.
  description?: string | null
  status: AmaSessionStatus
  scheduled_start: string
  scheduled_end: string
  // Author info is nested by the API (list + detail), not flat.
  author: AmaAuthorInfo
  total_questions: number
  total_answered: number
  created_at: string
}

export interface AmaQuestion {
  id: number
  session_id: number
  question_text: string
  display_name: string | null
  upvote_count: number
  is_featured: boolean
  is_answered: boolean
  answer_text: string | null
  answered_at: string | null
  status: 'pending' | 'approved' | 'rejected' | 'hidden'
  patron_has_upvoted?: boolean
  created_at: string
}

export interface AmaSessionDetail extends AmaSession {
  questions: AmaQuestion[]
}

export interface AmaSessionsResponse {
  items: AmaSession[]
  total: number
  page: number
  limit: number
}

export interface AmaSubmitQuestionResponse {
  id: number
  session_id: number
  question_text: string
  display_name: string | null
  status: string
  created_at: string
}

export interface AmaUpvoteResponse {
  question_id: number
  upvoted: boolean
  upvote_count: number
}

// ==================== Public Endpoints ====================

export async function getAmaSessions(
  status?: string,
  page: number = 1,
  limit: number = 20
): Promise<AmaSessionsResponse> {
  return fetchApi<AmaSessionsResponse>('/amas/sessions', {
    params: {
      ...(status ? { status } : {}),
      page,
      limit,
    },
  })
}

export async function getAmaSession(
  sessionId: number
): Promise<AmaSessionDetail> {
  return fetchApi<AmaSessionDetail>(`/amas/sessions/${sessionId}`, authOpts())
}

// ==================== Patron Endpoints (auth required) ====================

export async function submitAmaQuestion(
  sessionId: number,
  questionText: string,
  displayName?: string
): Promise<AmaSubmitQuestionResponse> {
  return fetchApi<AmaSubmitQuestionResponse>(
    `/amas/sessions/${sessionId}/questions`,
    {
      method: 'POST',
      body: JSON.stringify({
        question_text: questionText,
        ...(displayName ? { display_name: displayName } : {}),
      }),
      ...authOpts(),
    }
  )
}

export async function toggleAmaUpvote(
  questionId: number
): Promise<AmaUpvoteResponse> {
  return fetchApi<AmaUpvoteResponse>(
    `/amas/questions/${questionId}/upvote`,
    {
      method: 'POST',
      ...authOpts(),
    }
  )
}

export async function getMyAmaQuestions(
  sessionId: number
): Promise<AmaQuestion[]> {
  return fetchApi<AmaQuestion[]>(
    `/amas/sessions/${sessionId}/my-questions`,
    authOpts()
  )
}

// ==================== Staff Endpoints (staff auth required) ====================

export async function createAmaSession(data: {
  title: string
  description?: string
  author_id?: number
  guest_author_name?: string
  guest_author_bio?: string
  event_id?: number
  scheduled_start?: string
  scheduled_end?: string
}): Promise<AmaSession> {
  return fetchApi<AmaSession>('/amas/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
    ...authOpts(),
  })
}

export async function updateAmaSession(
  sessionId: number,
  data: Partial<{
    title: string
    description: string
    scheduled_start: string
    scheduled_end: string
  }>
): Promise<AmaSession> {
  return fetchApi<AmaSession>(`/amas/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    ...authOpts(),
  })
}

export async function transitionAmaSessionStatus(
  sessionId: number,
  status: string
): Promise<AmaSession> {
  return fetchApi<AmaSession>(`/amas/sessions/${sessionId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
    ...authOpts(),
  })
}

export async function deleteAmaSession(sessionId: number): Promise<void> {
  await fetchApi(`/amas/sessions/${sessionId}`, {
    method: 'DELETE',
    ...authOpts(),
    skipJsonParse: true,
  })
}

export async function getAmaModerationQueue(
  sessionId: number
): Promise<AmaQuestion[]> {
  return fetchApi<AmaQuestion[]>(
    `/amas/sessions/${sessionId}/moderate`,
    authOpts()
  )
}

export async function moderateAmaQuestion(
  questionId: number,
  action: 'approve' | 'reject' | 'hide',
  reason?: string
): Promise<void> {
  await fetchApi(`/amas/questions/${questionId}/moderate`, {
    method: 'POST',
    body: JSON.stringify({ action, ...(reason ? { reason } : {}) }),
    ...authOpts(),
  })
}

export async function toggleAmaQuestionFeatured(
  questionId: number
): Promise<void> {
  await fetchApi(`/amas/questions/${questionId}/feature`, {
    method: 'POST',
    ...authOpts(),
  })
}
