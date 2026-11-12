/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Tag Types ====================

export type TagColor = 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'orange' | 'pink' | 'gray'

export interface Tag {
  id: number
  name: string
  color: string
  description: string | null
  is_custom: boolean
  is_active: boolean
  created_at: string
  patron_count: number
}

export interface TagListResponse {
  tags: Tag[]
  total: number
}

export interface TagCreate {
  name: string
  color?: string
  description?: string
}

export interface TagUpdate {
  name?: string
  color?: string
  description?: string
  is_active?: boolean
}

export interface PatronTag {
  id: number
  tag_id: number
  tag_name: string
  tag_color: string
  assigned_at: string
  notes: string | null
}

export interface PatronTagAssignment {
  patron_id: number
  tag_id: number
  notes?: string
}

export interface BulkTagAssignment {
  patron_ids: number[]
  tag_id: number
  notes?: string
}

export interface BulkTagAssignmentResponse {
  assigned: number
  skipped: number
  total_requested: number
}

// ==================== Group Types ====================

export interface PatronGroup {
  id: number
  name: string
  description: string | null
  is_active: boolean
  allow_self_join: boolean
  max_members: number | null
  member_count: number
  created_at: string
  created_by_name: string | null
}

export interface GroupListResponse {
  groups: PatronGroup[]
  total: number
}

export interface GroupCreate {
  name: string
  description?: string
  allow_self_join?: boolean
  max_members?: number
}

export interface GroupUpdate {
  name?: string
  description?: string
  is_active?: boolean
  allow_self_join?: boolean
  max_members?: number
}

export interface GroupMember {
  id: number
  patron_id: number
  patron_name: string
  patron_email: string
  joined_at: string
  role: string | null
  notes: string | null
}

export interface GroupDetail extends PatronGroup {
  members: GroupMember[]
}

export interface GroupMemberAdd {
  patron_id: number
  role?: string
  notes?: string
}

export interface BulkGroupMemberAdd {
  patron_ids: number[]
  role?: string
}

export interface BulkGroupMemberResponse {
  added: number
  skipped: number
  total_requested: number
}

export interface GroupStats {
  group_id: number
  group_name: string
  member_count: number
  total_checkouts: number
  active_checkouts: number
  total_fines: string
  unpaid_fines: string
}

export interface GroupMessageRequest {
  subject: string
  message: string
}

export interface GroupMessageResponse {
  status: string
  group_id: number
  group_name: string
  recipient_count: number
  subject: string
  message_preview: string
}

export interface GroupExportResponse {
  group_name: string
  exported_at: string
  member_count: number
  members: Array<{
    id: number
    first_name: string
    last_name: string
    email: string
    phone: string | null
    library_card: string | null
    joined_group_at: string | null
    role: string | null
  }>
}

// ==================== Patrons by Tag/Group Types ====================

export interface PatronByTagResponse {
  tag: {
    id: number
    name: string
    color: string
  }
  patrons: Array<{
    id: number
    first_name: string
    last_name: string
    email: string
    library_card: string | null
    is_active: boolean
  }>
  total: number
}

export interface PatronByGroupResponse {
  group: {
    id: number
    name: string
  }
  patrons: Array<{
    id: number
    first_name: string
    last_name: string
    email: string
    library_card: string | null
    is_active: boolean
    role_in_group: string | null
  }>
  total: number
}

// ==================== Tag Management Functions ====================

export async function listTags(
  token: string,
  options?: {
    search?: string
    include_inactive?: boolean
  }
): Promise<TagListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.search) params.set('search', options.search)
    if (options?.include_inactive) params.set('include_inactive', 'true')
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<TagListResponse>(`/staff/tags${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch tags')
    }
    throw error
  }
}

export async function createTag(token: string, data: TagCreate): Promise<Tag> {
  try {
    return await fetchApi<Tag>('/staff/tags', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create tag')
    }
    throw error
  }
}

export async function updateTag(token: string, tagId: number, data: TagUpdate): Promise<Tag> {
  try {
    return await fetchApi<Tag>(`/staff/tags/${tagId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update tag')
    }
    throw error
  }
}

export async function deleteTag(token: string, tagId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/tags/${tagId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete tag')
    }
    throw error
  }
}

export async function seedSystemTags(token: string): Promise<TagListResponse> {
  try {
    return await fetchApi<TagListResponse>('/staff/tags/seed', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to seed system tags')
    }
    throw error
  }
}

// ==================== Patron Tag Assignment Functions ====================

export async function getPatronTags(token: string, patronId: number): Promise<PatronTag[]> {
  try {
    return await fetchApi<PatronTag[]>(`/staff/patrons/${patronId}/tags`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron tags')
    }
    throw error
  }
}

export async function assignTagToPatron(
  token: string,
  patronId: number,
  tagId: number,
  notes?: string
): Promise<PatronTag> {
  try {
    return await fetchApi<PatronTag>(`/staff/patrons/${patronId}/tags`, {
      method: 'POST',
      token,
      body: {
        patron_id: patronId,
        tag_id: tagId,
        notes,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to assign tag')
    }
    throw error
  }
}

export async function removeTagFromPatron(
  token: string,
  patronId: number,
  tagId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/staff/patrons/${patronId}/tags/${tagId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove tag')
    }
    throw error
  }
}

export async function bulkAssignTag(
  token: string,
  data: BulkTagAssignment
): Promise<BulkTagAssignmentResponse> {
  try {
    return await fetchApi<BulkTagAssignmentResponse>('/staff/tags/bulk-assign', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to bulk assign tags')
    }
    throw error
  }
}

// ==================== Group Management Functions ====================

export async function listGroups(
  token: string,
  options?: {
    search?: string
    include_inactive?: boolean
    limit?: number
    offset?: number
  }
): Promise<GroupListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.search) params.set('search', options.search)
    if (options?.include_inactive) params.set('include_inactive', 'true')
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<GroupListResponse>(`/staff/patron-groups${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch groups')
    }
    throw error
  }
}

export async function createGroup(token: string, data: GroupCreate): Promise<PatronGroup> {
  try {
    return await fetchApi<PatronGroup>('/staff/patron-groups', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create group')
    }
    throw error
  }
}

export async function getGroupDetail(token: string, groupId: number): Promise<GroupDetail> {
  try {
    return await fetchApi<GroupDetail>(`/staff/patron-groups/${groupId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch group details')
    }
    throw error
  }
}

export async function updateGroup(
  token: string,
  groupId: number,
  data: GroupUpdate
): Promise<PatronGroup> {
  try {
    return await fetchApi<PatronGroup>(`/staff/patron-groups/${groupId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update group')
    }
    throw error
  }
}

export async function deleteGroup(token: string, groupId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/patron-groups/${groupId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete group')
    }
    throw error
  }
}

// ==================== Group Member Functions ====================

export async function addGroupMember(
  token: string,
  groupId: number,
  data: GroupMemberAdd
): Promise<GroupMember> {
  try {
    return await fetchApi<GroupMember>(`/staff/patron-groups/${groupId}/members`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add member to group')
    }
    throw error
  }
}

export async function bulkAddGroupMembers(
  token: string,
  groupId: number,
  data: BulkGroupMemberAdd
): Promise<BulkGroupMemberResponse> {
  try {
    return await fetchApi<BulkGroupMemberResponse>(`/staff/patron-groups/${groupId}/members/bulk`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to bulk add members')
    }
    throw error
  }
}

export async function removeGroupMember(
  token: string,
  groupId: number,
  patronId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/staff/patron-groups/${groupId}/members/${patronId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove member from group')
    }
    throw error
  }
}

// ==================== Group Feature Functions ====================

export async function getGroupStats(token: string, groupId: number): Promise<GroupStats> {
  try {
    return await fetchApi<GroupStats>(`/staff/patron-groups/${groupId}/stats`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch group statistics')
    }
    throw error
  }
}

export async function sendGroupMessage(
  token: string,
  groupId: number,
  data: GroupMessageRequest
): Promise<GroupMessageResponse> {
  try {
    return await fetchApi<GroupMessageResponse>(`/staff/patron-groups/${groupId}/message`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send group message')
    }
    throw error
  }
}

export async function exportGroupMembers(
  token: string,
  groupId: number
): Promise<GroupExportResponse> {
  try {
    return await fetchApi<GroupExportResponse>(`/staff/patron-groups/${groupId}/export`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to export group members')
    }
    throw error
  }
}

// ==================== Patron Search by Tag/Group ====================

export async function getPatronsByTag(
  token: string,
  tagId: number,
  options?: {
    limit?: number
    offset?: number
  }
): Promise<PatronByTagResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronByTagResponse>(`/staff/patrons/by-tag/${tagId}${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patrons by tag')
    }
    throw error
  }
}

export async function getPatronsByGroup(
  token: string,
  groupId: number,
  options?: {
    limit?: number
    offset?: number
  }
): Promise<PatronByGroupResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronByGroupResponse>(`/staff/patrons/by-group/${groupId}${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patrons by group')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getTagColorClasses(color: string): string {
  const colorMap: Record<string, string> = {
    blue: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
    green: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    yellow: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    red: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    purple: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
    orange: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    pink: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400',
    gray: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
  }
  return colorMap[color] ?? colorMap.gray ?? ''
}

/**
 * Available tag colors for selection
 */
export const TAG_COLORS: { value: TagColor; label: string; classes: string }[] = [
  { value: 'blue', label: 'Blue', classes: 'bg-earth-500' },
  { value: 'green', label: 'Green', classes: 'bg-status-success-500' },
  { value: 'yellow', label: 'Yellow', classes: 'bg-status-warning-500' },
  { value: 'red', label: 'Red', classes: 'bg-status-danger-500' },
  { value: 'purple', label: 'Purple', classes: 'bg-category-500' },
  { value: 'orange', label: 'Orange', classes: 'bg-status-warning-500' },
  { value: 'pink', label: 'Pink', classes: 'bg-pink-500' },
  { value: 'gray', label: 'Gray', classes: 'bg-earth-500' },
]
