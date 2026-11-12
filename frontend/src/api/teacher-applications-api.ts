/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type TeacherApplicationStatus = 'pending' | 'approved' | 'denied'

export interface TeacherApplication {
  id: number
  user_id: number
  user_email: string | null
  user_name: string | null
  school_id: number | null
  school_name: string | null
  school_name_freetext: string | null
  grade_level: string | null
  subject: string | null
  classroom_size: number | null
  notes: string | null
  status: TeacherApplicationStatus
  created_at: string
  reviewed_at: string | null
  reviewed_by_id: number | null
  reviewed_by_name: string | null
  review_notes: string | null
  denial_reason: string | null
}

export interface TeacherApplicationCreate {
  school_id?: number | null
  school_name_freetext?: string | null
  grade_level?: string | null
  subject?: string | null
  classroom_size?: number | null
  notes?: string | null
}

export interface TeacherApplicationReview {
  status: 'approved' | 'denied'
  school_id?: number | null
  review_notes?: string
  denial_reason?: string
}

export interface TeacherApplicationListResponse {
  applications: TeacherApplication[]
  total: number
  limit: number
  offset: number
}

export interface TeacherSchoolOption {
  id: number
  name: string
}

// ==================== Patron ====================

export async function listTeacherSchools(token: string): Promise<TeacherSchoolOption[]> {
  try {
    return await fetchApi<TeacherSchoolOption[]>('/teacher-applications/schools', { token })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to load schools')
    throw error
  }
}

export async function submitTeacherApplication(
  token: string,
  data: TeacherApplicationCreate
): Promise<TeacherApplication> {
  try {
    return await fetchApi<TeacherApplication>('/teacher-applications', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to submit application')
    throw error
  }
}

export async function getMyTeacherApplication(
  token: string
): Promise<TeacherApplication | null> {
  try {
    return await fetchApi<TeacherApplication | null>('/teacher-applications/me', { token })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to load application')
    throw error
  }
}

// ==================== Staff ====================

export async function listTeacherApplications(
  token: string,
  params?: {
    status?: TeacherApplicationStatus
    search?: string
    limit?: number
    offset?: number
  }
): Promise<TeacherApplicationListResponse> {
  const sp = new URLSearchParams()
  if (params?.status) sp.set('status', params.status)
  if (params?.search) sp.set('search', params.search)
  if (params?.limit) sp.set('limit', String(params.limit))
  if (params?.offset) sp.set('offset', String(params.offset))
  const q = sp.toString()
  const url = `/teacher-applications/staff${q ? `?${q}` : ''}`
  try {
    return await fetchApi<TeacherApplicationListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to list applications')
    throw error
  }
}

export async function approveTeacherApplication(
  token: string,
  applicationId: number,
  body: { school_id?: number | null; review_notes?: string }
): Promise<TeacherApplication> {
  try {
    return await fetchApi<TeacherApplication>(
      `/teacher-applications/staff/${applicationId}/approve`,
      { method: 'POST', token, body: { status: 'approved', ...body } }
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to approve')
    throw error
  }
}

export async function denyTeacherApplication(
  token: string,
  applicationId: number,
  body: { denial_reason: string; review_notes?: string }
): Promise<TeacherApplication> {
  try {
    return await fetchApi<TeacherApplication>(
      `/teacher-applications/staff/${applicationId}/deny`,
      { method: 'POST', token, body: { status: 'denied', ...body } }
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to deny')
    throw error
  }
}
