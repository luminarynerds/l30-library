/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Types ====================

export type MotionStatus =
  | 'draft'
  | 'pending'
  | 'seconded'
  | 'under_discussion'
  | 'called_to_vote'
  | 'passed'
  | 'failed'
  | 'tabled'
  | 'referred'
  | 'withdrawn'

export type MotionType =
  | 'main'
  | 'amendment'
  | 'subsidiary'
  | 'privileged'
  | 'incidental'

export interface BoardMotion {
  id: number
  meeting_id: number
  motion_type: MotionType
  motion_number: string
  title: string
  motion_text: string
  rationale?: string
  moved_by_id: number
  moved_by_name?: string
  seconded_by_id?: number
  seconded_by_name?: string
  parent_motion_id?: number
  amended_text?: string
  status: MotionStatus
  moved_at?: string
  seconded_at?: string
  discussion_opened_at?: string
  discussion_closed_at?: string
  discussion_notes?: string
  vote_called_at?: string
  vote_id?: number
  outcome_recorded_at?: string
  outcome_notes?: string
  tabled_at?: string
  tabled_until?: string
  tabled_reason?: string
  referred_to_committee_id?: number
  referred_to_committee_name?: string
  referred_at?: string
  referred_notes?: string
  withdrawn_at?: string
  withdrawn_reason?: string
  created_by_id: number
  created_at: string
  updated_at: string
}

export interface MotionCreateData {
  motion_type: MotionType
  motion_number: string
  title: string
  motion_text: string
  rationale?: string
  moved_by_id: number
  parent_motion_id?: number
  amended_text?: string
}


export interface MotionSecondData {
  seconded_by_id: number
}

export interface MotionTableData {
  tabled_until?: string
  tabled_reason?: string
}

export interface MotionReferData {
  referred_to_committee_id: number
  referred_notes?: string
}

export interface MotionWithdrawData {
  withdrawn_reason?: string
}

export type ResolutionStatus =
  | 'draft'
  | 'proposed'
  | 'under_review'
  | 'adopted'
  | 'superseded'
  | 'rescinded'

export interface BoardResolution {
  id: number
  resolution_number: string
  title: string
  resolution_text: string
  summary?: string
  category?: string
  status: ResolutionStatus
  is_public: boolean
  proposed_by_id?: number
  proposed_by_name?: string
  proposed_date?: string
  adopted_date?: string
  adopted_vote_id?: number
  effective_date?: string
  published_date?: string
  published_by_id?: number
  supersedes_resolution_id?: number
  superseded_by_resolution_id?: number
  superseded_date?: string
  rescinded_date?: string
  rescinded_by_motion_id?: number
  rescinded_reason?: string
  created_by_id: number
  created_at: string
  updated_at: string
}

export interface ResolutionCreateData {
  resolution_number: string
  title: string
  resolution_text: string
  summary?: string
  category?: string
  is_public?: boolean
}

export interface ResolutionUpdateData {
  title?: string
  resolution_text?: string
  summary?: string
  category?: string
  is_public?: boolean
}

export interface ResolutionAdoptData {
  adopted_vote_id: number
  effective_date?: string
}

export interface ResolutionSupersedeData {
  supersedes_resolution_id: number
}

export interface ResolutionRescindData {
  rescinded_by_motion_id: number
  rescinded_reason?: string
}

// ==================== Motion API ====================

export async function getMeetingMotions(
  meetingId: number,
  statusFilter?: MotionStatus
): Promise<BoardMotion[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (statusFilter) params.set('status_filter', statusFilter)
  const query = params.toString() ? `?${params}` : ''
  try {
    return await fetchApi<BoardMotion[]>(
      `/board/meetings/${meetingId}/motions${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch motions')
    }
    throw error
  }
}

export async function createMotion(
  meetingId: number,
  data: MotionCreateData
): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/meetings/${meetingId}/motions`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create motion')
    }
    throw error
  }
}


export async function deleteMotion(motionId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/motions/${motionId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete motion')
    }
    throw error
  }
}

export async function secondMotion(
  motionId: number,
  data: MotionSecondData
): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/second`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to second motion')
    }
    throw error
  }
}

export async function openDiscussion(motionId: number): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/open-discussion`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to open discussion')
    }
    throw error
  }
}

export async function closeDiscussion(
  motionId: number,
  discussionNotes?: string
): Promise<BoardMotion> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (discussionNotes) params.set('discussion_notes', discussionNotes)
  const query = params.toString() ? `?${params}` : ''
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/close-discussion${query}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to close discussion')
    }
    throw error
  }
}

export async function recordOutcome(
  motionId: number,
  passed: boolean,
  voteId?: number,
  outcomeNotes?: string
): Promise<BoardMotion> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  params.set('passed', String(passed))
  if (voteId) params.set('vote_id', String(voteId))
  if (outcomeNotes) params.set('outcome_notes', outcomeNotes)
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/record-outcome?${params}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record outcome')
    }
    throw error
  }
}

export async function tableMotion(
  motionId: number,
  data: MotionTableData
): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/table`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to table motion')
    }
    throw error
  }
}

export async function referMotion(
  motionId: number,
  data: MotionReferData
): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/refer`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to refer motion')
    }
    throw error
  }
}

export async function withdrawMotion(
  motionId: number,
  data: MotionWithdrawData
): Promise<BoardMotion> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMotion>(`/board/motions/${motionId}/withdraw`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to withdraw motion')
    }
    throw error
  }
}

// ==================== Resolution API ====================

export async function getResolutions(params?: {
  status_filter?: ResolutionStatus
  category?: string
  is_public?: boolean
  limit?: number
}): Promise<BoardResolution[]> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status_filter) searchParams.set('status_filter', params.status_filter)
  if (params?.category) searchParams.set('category', params.category)
  if (params?.is_public !== undefined) searchParams.set('is_public', String(params.is_public))
  if (params?.limit) searchParams.set('limit', String(params.limit))
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<BoardResolution[]>(`/board/resolutions${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch resolutions')
    }
    throw error
  }
}

export async function getResolution(resolutionId: number): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch resolution')
    }
    throw error
  }
}

export async function createResolution(data: ResolutionCreateData): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>('/board/resolutions', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create resolution')
    }
    throw error
  }
}

export async function updateResolution(
  resolutionId: number,
  data: ResolutionUpdateData
): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update resolution')
    }
    throw error
  }
}

export async function deleteResolution(resolutionId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/resolutions/${resolutionId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete resolution')
    }
    throw error
  }
}

export async function proposeResolution(
  resolutionId: number,
  proposedById: number
): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(
      `/board/resolutions/${resolutionId}/propose?proposed_by_id=${proposedById}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to propose resolution')
    }
    throw error
  }
}

export async function adoptResolution(
  resolutionId: number,
  data: ResolutionAdoptData
): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}/adopt`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to adopt resolution')
    }
    throw error
  }
}

export async function publishResolution(resolutionId: number): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}/publish`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to publish resolution')
    }
    throw error
  }
}

export async function supersedeResolution(
  resolutionId: number,
  data: ResolutionSupersedeData
): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}/supersede`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to supersede resolution')
    }
    throw error
  }
}

export async function rescindResolution(
  resolutionId: number,
  data: ResolutionRescindData
): Promise<BoardResolution> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardResolution>(`/board/resolutions/${resolutionId}/rescind`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to rescind resolution')
    }
    throw error
  }
}
