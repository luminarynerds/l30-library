/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { buildQueryString, extractErrorMessage } from '@/lib/api-helpers'

// Types
export interface Announcement {
  id: number
  title: string
  content: string
  priority: 'normal' | 'important' | 'urgent'
  active: boolean
  starts_at: string | null
  ends_at: string | null
  show_on_homepage: boolean
  show_banner: boolean
  dismissible: boolean
  target_audience: string | null
  created_at: string
  created_by_name: string | null
}

export interface AnnouncementCreateData {
  title: string
  content: string
  priority?: 'normal' | 'important' | 'urgent'
  active?: boolean
  starts_at?: string
  ends_at?: string
  show_on_homepage?: boolean
  show_banner?: boolean
  dismissible?: boolean
  target_audience?: string
}

export interface AnnouncementUpdateData {
  title?: string
  content?: string
  priority?: 'normal' | 'important' | 'urgent'
  active?: boolean
  starts_at?: string
  ends_at?: string
  show_on_homepage?: boolean
  show_banner?: boolean
  dismissible?: boolean
  target_audience?: string
}

export interface AnnouncementStats {
  total_announcements: number
  active_now: number
  scheduled_future: number
  by_priority: Record<string, number>
}

// Public API
export async function getAnnouncements(params?: {
  active_only?: boolean
  priority?: string
  target_audience?: string
  homepage_only?: boolean
  page?: number
  per_page?: number
}): Promise<{ items: Announcement[]; total: number; page: number }> {
  const token = getAccessToken()
  const query = buildQueryString({
    active_only: params?.active_only,
    priority: params?.priority,
    target_audience: params?.target_audience,
    homepage_only: params?.homepage_only,
    page: params?.page,
    page_size: params?.per_page,
  })
  try {
    const response = await fetchApi<{ data: Announcement[]; pagination: { page: number; total: number } }>(`/announcements${query}`, { ...(token ? { token } : {}) })
    return {
      items: response.data,
      total: response.pagination.total,
      page: response.pagination.page,
    }
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

export async function getAnnouncement(id: number): Promise<Announcement> {
  const token = getAccessToken()
  try {
    return await fetchApi<Announcement>(`/announcements/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

// Admin API
export async function createAnnouncement(data: AnnouncementCreateData): Promise<Announcement> {
  const token = getAccessToken()
  try {
    return await fetchApi<Announcement>('/announcements', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

export async function updateAnnouncement(id: number, data: AnnouncementUpdateData): Promise<Announcement> {
  const token = getAccessToken()
  try {
    return await fetchApi<Announcement>(`/announcements/${id}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

export async function deleteAnnouncement(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/announcements/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

export async function toggleAnnouncement(id: number): Promise<Announcement> {
  const token = getAccessToken()
  try {
    return await fetchApi<Announcement>(`/announcements/admin/announcements/${id}/toggle`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}

export async function getAnnouncementStats(): Promise<AnnouncementStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<AnnouncementStats>('/announcements/admin/announcements/stats/summary', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Request failed'))
  }
}
