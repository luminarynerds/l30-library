/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

import type {
  BoardMember,
  BoardMemberCreate,
  BoardMemberUpdate,
  BoardMeeting,
  BoardMeetingCreate,
  BoardMeetingUpdate,
  AgendaItem,
  AgendaItemCreate,
  BoardMinutes,
  BoardMinutesCreate,
  BoardVote,
  BoardVoteCreate,
  VoteChoice,
  VoteCastCreate,
  VoteCastResponse,
  VoteCloseResult,
  BoardDocument,
  BoardDocumentCreate,
  DocumentVersion,
  DocumentVersionCreate,
  MeetingBrief,
  AttendanceStatus,
  RsvpStatus,
  Attendance,
  AttendanceCreate,
  AttendanceCheckIn,
  ActionItemStatus,
  ActionItemPriority,
  ActionItem,
  ActionItemCreate,
  ActionItemUpdate,
  ActionItemStatusUpdate,
  NoticePostingLocation,
  NoticeGenerateRequest,
  NoticeResponse,
  NoticePostRequest,
  NoticePostResult,
  NoticePublishResult,
  MeetingSearchParams,
  MeetingSearchResponse,
} from './board-types'

// Re-export all types for backward compatibility
export type {
  BoardMember,
  BoardMemberCreate,
  BoardMemberUpdate,
  BoardMeeting,
  BoardMeetingCreate,
  BoardMeetingUpdate,
  AgendaItem,
  AgendaItemCreate,
  BoardMinutes,
  BoardMinutesCreate,
  BoardVote,
  BoardVoteCreate,
  VoteChoice,
  VoteCastCreate,
  VoteCastResponse,
  VoteCloseResult,
  BoardDocument,
  BoardDocumentCreate,
  DocumentVersion,
  DocumentVersionCreate,
  MeetingBrief,
  AttendanceStatus,
  RsvpStatus,
  Attendance,
  AttendanceCreate,
  AttendanceCheckIn,
  ActionItemStatus,
  ActionItemPriority,
  ActionItem,
  ActionItemCreate,
  ActionItemUpdate,
  ActionItemStatusUpdate,
  NoticePostingLocation,
  NoticeGenerateRequest,
  NoticeResponse,
  NoticePostRequest,
  NoticePostResult,
  NoticePublishResult,
  MeetingSearchParams,
  MeetingSearchResponse,
}

// ==================== Board Member Functions ====================

export async function createBoardMember(data: BoardMemberCreate): Promise<BoardMember> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMember>('/board/members', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create board member')
    }
    throw error
  }
}

export async function updateBoardMember(
  memberId: number,
  data: BoardMemberUpdate
): Promise<BoardMember> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMember>(`/board/members/${memberId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update board member')
    }
    throw error
  }
}

export async function deleteBoardMember(memberId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/members/${memberId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete board member')
    }
    throw error
  }
}

// ==================== Board Meeting Functions ====================

export async function createMeeting(data: BoardMeetingCreate): Promise<BoardMeeting> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMeeting>('/board/meetings', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create meeting')
    }
    throw error
  }
}

export async function updateMeeting(
  meetingId: number,
  data: BoardMeetingUpdate
): Promise<BoardMeeting> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardMeeting>(`/board/meetings/${meetingId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update meeting')
    }
    throw error
  }
}

export async function cancelMeeting(
  meetingId: number,
  reason: string
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(
      `/board/meetings/${meetingId}/cancel?reason=${encodeURIComponent(reason)}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cancel meeting')
    }
    throw error
  }
}

export async function deleteMeeting(meetingId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/meetings/${meetingId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete meeting')
    }
    throw error
  }
}

export async function searchMeetings(
  params: MeetingSearchParams = {}
): Promise<MeetingSearchResponse> {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.meeting_type) query.set('meeting_type', params.meeting_type)
  if (params.status) query.set('status', params.status)
  if (params.date_from) query.set('date_from', params.date_from)
  if (params.date_to) query.set('date_to', params.date_to)
  if (params.has_recording !== undefined) query.set('has_recording', String(params.has_recording))
  if (params.committee_id !== undefined) query.set('committee_id', String(params.committee_id))
  if (params.skip !== undefined) query.set('skip', String(params.skip))
  if (params.limit !== undefined) query.set('limit', String(params.limit))

  const qs = query.toString()
  try {
    return await fetchApi<MeetingSearchResponse>(`/board/meetings/search${qs ? `?${qs}` : ''}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to search meetings')
    }
    throw error
  }
}

export async function addAgendaItem(
  meetingId: number,
  data: AgendaItemCreate
): Promise<AgendaItem> {
  const token = getAccessToken()
  try {
    return await fetchApi<AgendaItem>(`/board/meetings/${meetingId}/agenda`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add agenda item')
    }
    throw error
  }
}


export async function approveMinutes(
  meetingId: number,
  voteResult: string
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(
      `/board/meetings/${meetingId}/minutes/approve?vote_result=${encodeURIComponent(voteResult)}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to approve minutes')
    }
    throw error
  }
}

// ==================== Board Vote Functions ====================

export async function createVote(data: BoardVoteCreate): Promise<BoardVote> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardVote>('/board/votes', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create vote')
    }
    throw error
  }
}

export async function castVote(
  voteId: number,
  data: VoteCastCreate
): Promise<VoteCastResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<VoteCastResponse>(`/board/votes/${voteId}/cast`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cast vote')
    }
    throw error
  }
}

export async function openVote(voteId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/board/votes/${voteId}/open`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to open vote')
    }
    throw error
  }
}

export async function closeVote(voteId: number): Promise<VoteCloseResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<VoteCloseResult>(`/board/votes/${voteId}/close`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to close vote')
    }
    throw error
  }
}

export async function deleteVote(voteId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/votes/${voteId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete vote')
    }
    throw error
  }
}

// ==================== Board Document Functions ====================

export async function createDocument(data: BoardDocumentCreate): Promise<BoardDocument> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardDocument>('/board/documents', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create document')
    }
    throw error
  }
}

export async function publishDocument(documentId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/board/documents/${documentId}/publish`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to publish document')
    }
    throw error
  }
}

export async function archiveDocument(documentId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/board/documents/${documentId}/archive`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to archive document')
    }
    throw error
  }
}

export async function deleteDocument(documentId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/documents/${documentId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete document')
    }
    throw error
  }
}

// ==================== Document Version Functions ====================

export async function listDocumentVersions(documentId: number): Promise<DocumentVersion[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<DocumentVersion[]>(`/board/documents/${documentId}/versions`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch document versions')
    }
    throw error
  }
}

export async function createDocumentVersion(
  documentId: number,
  data: DocumentVersionCreate
): Promise<DocumentVersion> {
  const token = getAccessToken()
  try {
    return await fetchApi<DocumentVersion>(`/board/documents/${documentId}/versions`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create document version')
    }
    throw error
  }
}

export async function getDocumentVersion(
  documentId: number,
  versionNumber: number
): Promise<DocumentVersion> {
  const token = getAccessToken()
  try {
    return await fetchApi<DocumentVersion>(
      `/board/documents/${documentId}/versions/${versionNumber}`,
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch document version')
    }
    throw error
  }
}

// ==================== Meeting Brief Functions ====================

export async function generateMeetingBrief(meetingId: number): Promise<MeetingBrief> {
  const token = getAccessToken()
  try {
    return await fetchApi<MeetingBrief>(`/board/meetings/${meetingId}/brief`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate meeting brief')
    }
    throw error
  }
}

export async function deleteMeetingBrief(meetingId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/meetings/${meetingId}/brief`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete meeting brief')
    }
    throw error
  }
}

// ==================== Attendance Functions ====================

export async function recordAttendance(
  meetingId: number,
  data: AttendanceCreate
): Promise<Attendance> {
  const token = getAccessToken()
  try {
    return await fetchApi<Attendance>(`/board/meetings/${meetingId}/attendance`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record attendance')
    }
    throw error
  }
}

export async function checkInAttendee(
  meetingId: number,
  attendanceId: number,
  data: AttendanceCheckIn
): Promise<Attendance> {
  const token = getAccessToken()
  try {
    return await fetchApi<Attendance>(
      `/board/meetings/${meetingId}/attendance/${attendanceId}/checkin`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check in attendee')
    }
    throw error
  }
}

export async function checkOutAttendee(
  meetingId: number,
  attendanceId: number
): Promise<Attendance> {
  const token = getAccessToken()
  try {
    return await fetchApi<Attendance>(
      `/board/meetings/${meetingId}/attendance/${attendanceId}/checkout`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check out attendee')
    }
    throw error
  }
}

export async function markAbsent(
  meetingId: number,
  attendanceId: number,
  excused: boolean = false,
  reason?: string
): Promise<{ message: string }> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  params.set('excused', String(excused))
  if (reason) params.set('reason', reason)
  try {
    return await fetchApi<{ message: string }>(
      `/board/meetings/${meetingId}/attendance/${attendanceId}/absent?${params}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark attendee as absent')
    }
    throw error
  }
}

// ==================== Action Item Functions ====================

export async function createActionItem(
  meetingId: number,
  data: ActionItemCreate
): Promise<ActionItem> {
  const token = getAccessToken()
  try {
    return await fetchApi<ActionItem>(`/board/meetings/${meetingId}/action-items`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create action item')
    }
    throw error
  }
}

export async function updateActionItem(
  actionItemId: number,
  data: ActionItemUpdate
): Promise<ActionItem> {
  const token = getAccessToken()
  try {
    return await fetchApi<ActionItem>(`/board/action-items/${actionItemId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update action item')
    }
    throw error
  }
}

export async function updateActionItemStatus(
  actionItemId: number,
  data: ActionItemStatusUpdate
): Promise<ActionItem> {
  const token = getAccessToken()
  try {
    return await fetchApi<ActionItem>(`/board/action-items/${actionItemId}/status`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update action item status')
    }
    throw error
  }
}

export async function deleteActionItem(actionItemId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/board/action-items/${actionItemId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete action item')
    }
    throw error
  }
}

// ==================== Notice Compliance Functions ====================

export async function generateMeetingNotice(
  meetingId: number,
  data: NoticeGenerateRequest = {}
): Promise<NoticeResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<NoticeResponse>(`/board/meetings/${meetingId}/notice/generate`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate meeting notice')
    }
    throw error
  }
}

export async function postMeetingNotice(
  meetingId: number,
  data: NoticePostRequest
): Promise<NoticePostResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<NoticePostResult>(`/board/meetings/${meetingId}/notice/post`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to post meeting notice')
    }
    throw error
  }
}

export async function publishMeetingNotice(meetingId: number): Promise<NoticePublishResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<NoticePublishResult>(`/board/meetings/${meetingId}/notice/publish`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to publish meeting notice')
    }
    throw error
  }
}

export async function removePostingLocation(
  meetingId: number,
  location: string
): Promise<NoticePostResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<NoticePostResult>(
      `/board/meetings/${meetingId}/notice/posting/${encodeURIComponent(location)}`,
      {
        method: 'DELETE',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove posting location')
    }
    throw error
  }
}
