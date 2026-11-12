/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Board Committee Types ====================

export interface Committee {
  id: number
  name: string
  description: string | null
  committee_type: string
  status: 'active' | 'inactive' | 'dissolved'
  is_public: boolean
  charter_text: string | null
  meeting_schedule: string | null
  max_members: number | null
  min_members: number | null
  parent_committee_id: number | null
  formation_date: string | null
  dissolution_date: string | null
  dissolution_reason: string | null
  created_at: string
  updated_at: string | null
}


export interface CommitteeMember {
  id: number
  committee_id: number
  board_member_id: number
  role: 'chair' | 'vice_chair' | 'secretary' | 'member'
  appointed_date: string
  term_end_date: string | null
  appointment_notes: string | null
  is_active: boolean
  removed_date: string | null
  removal_reason: string | null
  created_at: string
  updated_at: string | null
  // Joined from board_member
  board_member_name?: string
  board_member_position?: string
}

export interface CommitteeMemberCreate {
  board_member_id: number
  role: 'chair' | 'vice_chair' | 'secretary' | 'member'
  appointed_date: string
  term_end_date?: string | null
  appointment_notes?: string | null
}

export interface CommitteeMemberUpdate {
  role?: 'chair' | 'vice_chair' | 'secretary' | 'member'
  term_end_date?: string | null
  appointment_notes?: string | null
}

export interface CommitteeMemberRemove {
  removal_reason: string
}

export interface CommitteeMeeting {
  id: number
  meeting_type: string
  title: string
  description: string | null
  scheduled_date: string
  start_time: string | null
  end_time: string | null
  location: string | null
  is_virtual: boolean
  virtual_meeting_url: string | null
  is_cancelled: boolean
  committee_id: number
}

export interface CommitteeDocument {
  id: number
  title: string
  description: string | null
  document_type: string
  file_url: string | null
  is_public: boolean
  status: string
  published_date: string | null
  committee_id: number
}

// ==================== Committee Functions ====================

export async function getCommittees(
  includeInactive = false,
  committeeType?: string
): Promise<Committee[]> {
  try {
    let url = `/board/committees?include_inactive=${includeInactive}`
    if (committeeType) {
      url += `&committee_type=${encodeURIComponent(committeeType)}`
    }
    return await fetchApi<Committee[]>(url)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch committees')
    }
    throw error
  }
}

export async function getCommittee(committeeId: number): Promise<Committee> {
  try {
    return await fetchApi<Committee>(`/board/committees/${committeeId}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch committee')
    }
    throw error
  }
}

export async function getCommitteeMembers(
  committeeId: number,
  includeInactive = false
): Promise<CommitteeMember[]> {
  try {
    return await fetchApi<CommitteeMember[]>(
      `/board/committees/${committeeId}/members?include_inactive=${includeInactive}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch committee members')
    }
    throw error
  }
}


export async function dissolveCommittee(
  token: string,
  committeeId: number,
  reason: string
): Promise<{ message: string; dissolution_date: string }> {
  try {
    return await fetchApi<{ message: string; dissolution_date: string }>(
      `/board/committees/${committeeId}/dissolve?reason=${encodeURIComponent(reason)}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to dissolve committee')
    }
    throw error
  }
}

export async function deleteCommittee(
  token: string,
  committeeId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/board/committees/${committeeId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete committee')
    }
    throw error
  }
}

// ==================== Committee Member Functions ====================

export async function addCommitteeMember(
  token: string,
  committeeId: number,
  data: CommitteeMemberCreate
): Promise<CommitteeMember> {
  try {
    return await fetchApi<CommitteeMember>(
      `/board/committees/${committeeId}/members`,
      {
        method: 'POST',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add committee member')
    }
    throw error
  }
}

export async function updateCommitteeMember(
  token: string,
  committeeId: number,
  memberId: number,
  data: CommitteeMemberUpdate
): Promise<CommitteeMember> {
  try {
    return await fetchApi<CommitteeMember>(
      `/board/committees/${committeeId}/members/${memberId}`,
      {
        method: 'PUT',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update committee member')
    }
    throw error
  }
}

export async function removeCommitteeMember(
  token: string,
  committeeId: number,
  memberId: number,
  data: CommitteeMemberRemove
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>(
      `/board/committees/${committeeId}/members/${memberId}/remove`,
      {
        method: 'POST',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove committee member')
    }
    throw error
  }
}

// ==================== Committee Meetings & Documents ====================

export async function getCommitteeMeetings(
  committeeId: number,
  upcomingOnly = false,
  limit = 20
): Promise<CommitteeMeeting[]> {
  try {
    return await fetchApi<CommitteeMeeting[]>(
      `/board/committees/${committeeId}/meetings?upcoming_only=${upcomingOnly}&limit=${limit}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch committee meetings')
    }
    throw error
  }
}

export async function getCommitteeDocuments(
  committeeId: number,
  documentType?: string,
  limit = 50
): Promise<CommitteeDocument[]> {
  try {
    let url = `/board/committees/${committeeId}/documents?limit=${limit}`
    if (documentType) {
      url += `&document_type=${encodeURIComponent(documentType)}`
    }
    return await fetchApi<CommitteeDocument[]>(url)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch committee documents')
    }
    throw error
  }
}
