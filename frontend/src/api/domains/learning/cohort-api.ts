/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Learning Path Cohort API (V1): opt-in pair-up + shared thread.
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

export interface CohortMemberPublic {
  user_id: number
  first_name: string
  opted_in_at: string
}

export interface CohortStatus {
  is_member: boolean
  member_count: number
  members: CohortMemberPublic[]
}

export interface CohortDiscussionPost {
  id: number
  learning_path_id: number
  user_id: number | null
  author_display_name: string
  body: string
  created_at: string
}

function rethrow(error: unknown): never {
  if (isApiError(error)) {
    throw new Error(error.detail || 'Request failed')
  }
  throw error instanceof Error ? error : new Error(String(error))
}

export async function getCohortStatus(pathId: number): Promise<CohortStatus> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortStatus>(
      `/learning-paths/${pathId}/cohort/members`,
      { ...(token ? { token } : {}) },
    )
  } catch (error: unknown) {
    rethrow(error)
  }
}

export async function joinCohort(pathId: number): Promise<CohortStatus> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortStatus>(
      `/learning-paths/${pathId}/cohort/join`,
      { method: 'POST', ...(token ? { token } : {}) },
    )
  } catch (error: unknown) {
    rethrow(error)
  }
}

export async function leaveCohort(pathId: number): Promise<CohortStatus> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortStatus>(
      `/learning-paths/${pathId}/cohort/leave`,
      { method: 'POST', ...(token ? { token } : {}) },
    )
  } catch (error: unknown) {
    rethrow(error)
  }
}

export async function listCohortDiscussion(
  pathId: number,
): Promise<CohortDiscussionPost[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortDiscussionPost[]>(
      `/learning-paths/${pathId}/cohort/discussion`,
      { ...(token ? { token } : {}) },
    )
  } catch (error: unknown) {
    rethrow(error)
  }
}

export async function postCohortDiscussion(
  pathId: number,
  body: string,
): Promise<CohortDiscussionPost> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortDiscussionPost>(
      `/learning-paths/${pathId}/cohort/discussion`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: { body },
      },
    )
  } catch (error: unknown) {
    rethrow(error)
  }
}
