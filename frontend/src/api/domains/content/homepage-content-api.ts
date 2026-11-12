/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Homepage Content Management API
 * Quick links + library hours — staff-managed homepage content.
 */

import { fetchApi } from '@/lib/api-client'

// ==================== Quick Links ====================

export interface QuickLink {
  id: number
  label: string
  icon: string
  url: string
  sort_order: number
  is_active: boolean
}

export interface QuickLinkCreate {
  label: string
  icon: string
  url: string
  sort_order?: number
  is_active?: boolean
}

export interface QuickLinkUpdate {
  label?: string
  icon?: string
  url?: string
  sort_order?: number
  is_active?: boolean
}

export function getActiveQuickLinks(): Promise<QuickLink[]> {
  return fetchApi<QuickLink[]>('/homepage/quick-links')
}

export function getAllQuickLinks(): Promise<QuickLink[]> {
  return fetchApi<QuickLink[]>('/homepage/quick-links/all')
}

export function createQuickLink(data: QuickLinkCreate): Promise<QuickLink> {
  return fetchApi<QuickLink>('/homepage/quick-links', { method: 'POST', body: data })
}

export function updateQuickLink(id: number, data: QuickLinkUpdate): Promise<QuickLink> {
  return fetchApi<QuickLink>(`/homepage/quick-links/${id}`, { method: 'PUT', body: data })
}

export function deleteQuickLink(id: number): Promise<void> {
  return fetchApi<void>(`/homepage/quick-links/${id}`, { method: 'DELETE' })
}

export function reorderQuickLinks(items: { id: number; sort_order: number }[]): Promise<void> {
  return fetchApi<void>('/homepage/quick-links/reorder', { method: 'PUT', body: { items } })
}

// ==================== Library Hours ====================

export interface DayHours {
  id: number
  day_of_week: number
  open_time: string | null
  close_time: string | null
  is_closed: boolean
  label: string | null
}

export interface HoursOverride {
  id: number
  date: string
  open_time: string | null
  close_time: string | null
  is_closed: boolean
  reason: string | null
  created_at?: string
}

export interface LibraryHoursResponse {
  weekly: DayHours[]
  overrides: HoursOverride[]
}

export interface IsOpenResponse {
  is_open: boolean
  closes_at: string | null
  opens_at: string | null
  reason: string | null
}

export function getLibraryHours(): Promise<LibraryHoursResponse> {
  // Trailing slash required: the backend route lives at "/" under the
  // /library-hours prefix, and FastAPI's 307 redirect drops non-standard
  // ports from the Location header, which kills the fetch on dev/demo hosts.
  return fetchApi<LibraryHoursResponse>('/library-hours/')
}

export function getIsOpen(): Promise<IsOpenResponse> {
  return fetchApi<IsOpenResponse>('/library-hours/is-open')
}

export function updateWeeklyHours(days: {
  day_of_week: number
  open_time: string | null
  close_time: string | null
  is_closed: boolean
  label?: string | null
}[]): Promise<void> {
  return fetchApi<void>('/library-hours/weekly', { method: 'PUT', body: { days } })
}

export function getHoursOverrides(): Promise<HoursOverride[]> {
  return fetchApi<HoursOverride[]>('/library-hours/overrides')
}

export function createHoursOverride(data: {
  date: string
  open_time?: string | null
  close_time?: string | null
  is_closed?: boolean
  reason?: string | null
}): Promise<HoursOverride> {
  return fetchApi<HoursOverride>('/library-hours/overrides', { method: 'POST', body: data })
}

export function updateHoursOverride(id: number, data: {
  open_time?: string | null
  close_time?: string | null
  is_closed?: boolean
  reason?: string | null
}): Promise<HoursOverride> {
  return fetchApi<HoursOverride>(`/library-hours/overrides/${id}`, { method: 'PUT', body: data })
}

export function deleteHoursOverride(id: number): Promise<void> {
  return fetchApi<void>(`/library-hours/overrides/${id}`, { method: 'DELETE' })
}
