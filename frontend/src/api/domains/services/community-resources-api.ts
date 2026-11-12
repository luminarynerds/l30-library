/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface PublicLink {
  name: string
  url: string
  description: string | null
}

export interface PublicCategory {
  category: string
  title: string
  icon_hint: string | null
  links: PublicLink[]
}

export interface PublicCommunityResourcesResponse {
  categories: PublicCategory[]
}

export async function getCommunityResources(
  pageContext: string
): Promise<PublicCommunityResourcesResponse> {
  return api.get(`/community-resources?page_context=${pageContext}`)
}
