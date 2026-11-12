/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type CardApplicationStatus = 'pending' | 'under_review' | 'approved' | 'denied'

export interface CardApplication {
  id: number
  user_id: number | null
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string | null
  date_of_birth: string | null
  address_line1: string
  address_line2: string | null
  city: string
  state: string
  zip_code: string
  id_type: string | null
  id_number_last4: string | null
  status: CardApplicationStatus
  submitted_at: string
  reviewed_by_id: number | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  review_notes: string | null
  denial_reason: string | null
  assigned_card_number: string | null
}

export interface CardApplicationCreate {
  first_name: string
  last_name: string
  email: string
  phone?: string
  date_of_birth?: string
  address_line1: string
  address_line2?: string
  city: string
  state: string
  zip_code: string
  id_type?: string
  id_number_last4?: string
  turnstile_token?: string
}

export interface CardApplicationReview {
  status: 'under_review' | 'approved' | 'denied'
  review_notes?: string
  denial_reason?: string
}

export interface CardApplicationListResponse {
  applications: CardApplication[]
  total: number
  limit: number
  offset: number
}

export interface CardApplicationStats {
  total_pending: number
  total_under_review: number
  total_approved: number
  total_denied: number
  total_this_week: number
  total_this_month: number
  average_review_time_hours: number | null
}

export interface CardApplicationPublicStatus {
  status: CardApplicationStatus
  submitted_at: string
  reviewed_at: string | null
}

// ==================== Error Formatting ====================

export function formatCardApplicationError(error: unknown, fallback: string): string {
  if (!isApiError(error)) {
    return fallback
  }
  const body = error.body as Record<string, unknown> | undefined
  const rawDetail = body && (body as { detail?: unknown }).detail
  if (rawDetail && typeof rawDetail === 'object' && !Array.isArray(rawDetail)) {
    const d = rawDetail as Record<string, unknown>
    const parts: string[] = []
    if (typeof d.message === 'string') parts.push(d.message)
    if (typeof d.existing_card_number === 'string') {
      parts.push(`Existing card: ${d.existing_card_number}.`)
    }
    if (typeof d.contact_branch === 'string') {
      parts.push(`Contact branch: ${d.contact_branch}.`)
    }
    if (typeof d.existing_status === 'string') {
      parts.push(`Current status: ${d.existing_status}.`)
    }
    if (typeof d.guidance === 'string') parts.push(d.guidance)
    if (parts.length > 0) return parts.join(' ')
  }
  return error.detail || fallback
}

// ==================== Public API Functions ====================

export async function submitCardApplication(
  data: CardApplicationCreate
): Promise<CardApplication> {
  try {
    return await fetchApi<CardApplication>('/card-applications', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(formatCardApplicationError(error, 'Failed to submit application'))
    }
    throw error
  }
}

export async function checkApplicationByToken(
  token: string,
): Promise<CardApplicationPublicStatus> {
  try {
    return await fetchApi<CardApplicationPublicStatus>(
      `/card-applications/check-by-token/${encodeURIComponent(token)}`,
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('This status link is invalid or has expired.')
      }
      throw new Error(error.detail || 'Failed to check application status')
    }
    throw error
  }
}

export async function checkApplicationStatus(email: string): Promise<CardApplication> {
  try {
    return await fetchApi<CardApplication>(`/card-applications/check/${encodeURIComponent(email)}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('No application found with this email')
      }
      throw new Error(formatCardApplicationError(error, 'Failed to check application status'))
    }
    throw error
  }
}

// ==================== Authenticated User Functions ====================

export async function getMyApplications(token: string): Promise<CardApplication[]> {
  try {
    return await fetchApi<CardApplication[]>('/card-applications/my', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(formatCardApplicationError(error, 'Failed to fetch your applications'))
    }
    throw error
  }
}

// ==================== Staff API Functions ====================

export async function listCardApplications(
  token: string,
  params?: {
    status?: CardApplicationStatus
    search?: string
    limit?: number
    offset?: number
  }
): Promise<CardApplicationListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.offset) searchParams.set('offset', params.offset.toString())

  const query = searchParams.toString()
  const url = `/card-applications/staff${query ? `?${query}` : ''}`

  try {
    return await fetchApi<CardApplicationListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(formatCardApplicationError(error, 'Failed to fetch applications'))
    }
    throw error
  }
}

export async function getCardApplicationStats(token: string): Promise<CardApplicationStats> {
  try {
    return await fetchApi<CardApplicationStats>('/card-applications/staff/stats', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(formatCardApplicationError(error, 'Failed to fetch statistics'))
    }
    throw error
  }
}

export async function getCardApplication(
  token: string,
  applicationId: number
): Promise<CardApplication> {
  try {
    return await fetchApi<CardApplication>(`/card-applications/staff/${applicationId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Application not found')
      }
      throw new Error(formatCardApplicationError(error, 'Failed to fetch application'))
    }
    throw error
  }
}

export async function reviewCardApplication(
  token: string,
  applicationId: number,
  review: CardApplicationReview
): Promise<CardApplication> {
  try {
    return await fetchApi<CardApplication>(`/card-applications/staff/${applicationId}/review`, {
      method: 'POST',
      token,
      body: review,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Application not found')
      }
      throw new Error(formatCardApplicationError(error, 'Failed to review application'))
    }
    throw error
  }
}
