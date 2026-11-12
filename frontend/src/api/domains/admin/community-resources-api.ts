/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface CommunityResourceLink {
  id: number
  category: string
  category_label: string
  page_contexts: string[]
  name: string
  url: string | null
  description: string | null
  icon_hint: string | null
  sort_order: number
  is_active: boolean
  source: string
}

export interface CommunityResourceLinkCreate {
  category: string
  category_label: string
  page_contexts: string[]
  name: string
  url?: string | null
  description?: string | null
  icon_hint?: string | null
  sort_order?: number
  is_active?: boolean
  source?: string
}

export interface CommunityResourceLinkUpdate {
  category?: string
  category_label?: string
  page_contexts?: string[]
  name?: string
  url?: string | null
  description?: string | null
  icon_hint?: string | null
  sort_order?: number
  is_active?: boolean
}

export interface DiscoverySuggestion {
  name: string
  url: string
  category: string
  category_label: string
  description: string | null
}

export interface DiscoveryResponse {
  suggestions: DiscoverySuggestion[]
  zip_code: string
  city: string
  state: string
}

export async function getAdminCommunityResources(): Promise<CommunityResourceLink[]> {
  return api.get('/admin/community-resources')
}

export async function createCommunityResource(
  data: CommunityResourceLinkCreate
): Promise<CommunityResourceLink> {
  return api.post('/admin/community-resources', data)
}

export async function updateCommunityResource(
  id: number,
  data: CommunityResourceLinkUpdate
): Promise<CommunityResourceLink> {
  return api.patch(`/admin/community-resources/${id}`, data)
}

export async function deleteCommunityResource(id: number): Promise<void> {
  await api.delete(`/admin/community-resources/${id}`)
}

export async function discoverCommunityResources(): Promise<DiscoveryResponse> {
  return api.post('/admin/community-resources/discover')
}

export async function saveDiscoveredResources(
  suggestions: DiscoverySuggestion[]
): Promise<CommunityResourceLink[]> {
  return api.post('/admin/community-resources/discover/save', suggestions)
}
