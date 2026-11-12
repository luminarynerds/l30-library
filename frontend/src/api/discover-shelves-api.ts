/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/api/fetchApi'

export type ShelfAudience = 'kids' | 'teens' | 'adults' | 'all'

export interface DiscoverShelfSummary {
  id: number
  slug: string
  title: string
  description: string | null
  audience: ShelfAudience | null
  display_order: number
  item_count: number
}

export interface DiscoverShelfItem {
  id: number
  title: string
  author: string | null
  cover_url: string | null
  item_type: string
  status: string
}

export interface DiscoverShelfDetail extends DiscoverShelfSummary {
  items: DiscoverShelfItem[]
}

export async function getDiscoverShelves(
  audience?: ShelfAudience,
  lang?: string,
): Promise<DiscoverShelfSummary[]> {
  const params = new URLSearchParams()
  if (audience) params.set('audience', audience)
  if (lang && lang !== 'en') params.set('lang', lang)
  const qs = params.toString()
  return fetchApi(`/discover/shelves${qs ? `?${qs}` : ''}`)
}

export async function getDiscoverShelf(slug: string, lang?: string): Promise<DiscoverShelfDetail> {
  const qs = lang && lang !== 'en' ? `?lang=${encodeURIComponent(lang)}` : ''
  return fetchApi(`/discover/shelves/${encodeURIComponent(slug)}${qs}`)
}
