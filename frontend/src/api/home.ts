/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Home page admin + public API client.
 *
 * Wraps the endpoints introduced in PR #670 (feat/home-shelves-backend):
 *   - GET    /home/page              public composite payload
 *   - GET    /home/admin/hero-picks  admin list
 *   - POST   /home/admin/hero-picks
 *   - PATCH  /home/admin/hero-picks/{id}
 *   - DELETE /home/admin/hero-picks/{id}
 *   - GET    /home/admin/shelves
 *   - POST   /home/admin/shelves
 *   - PATCH  /home/admin/shelves/{id}
 *   - DELETE /home/admin/shelves/{id}
 *   - GET    /home/admin/config
 *   - PATCH  /home/admin/config
 *
 * Types mirror backend/app/schemas/home.py.
 */
import { fetchApi } from '@/lib/api-client'

// ---- Enum mirror --------------------------------------------------------
// Backend uses HomeShelfQueryKind (lowercase string enum). We type as a
// string-union here so server JSON deserializes cleanly.
export type HomeShelfQueryKind =
  | 'new_arrivals'
  | 'staff_picks'
  | 'subject'
  | 'format'
  | 'circulation_top'
  | 'manual_list'

export const HOME_SHELF_QUERY_KINDS: HomeShelfQueryKind[] = [
  'new_arrivals',
  'staff_picks',
  'subject',
  'format',
  'circulation_top',
  'manual_list',
]

// ---- Item card ----------------------------------------------------------
export interface HomeItemCard {
  id: number
  title: string
  author: string | null
  item_type: string | null
}

// ---- Hero pick ----------------------------------------------------------
export interface HeroPickRead {
  id: number
  item: HomeItemCard
  annotation_md: string
  cta_label: string
  cta_href: string | null
  active_from: string
  active_to: string | null
}

export interface HeroPickCreate {
  item_id: number
  annotation_md: string
  cta_label: string
  cta_href?: string | null
  active_from: string
  active_to?: string | null
}

export type HeroPickUpdate = Partial<HeroPickCreate>

// ---- Shelf --------------------------------------------------------------
export interface ShelfAdminRead {
  id: number
  slug: string
  heading: string
  description: string
  query_kind: HomeShelfQueryKind
  query_params: Record<string, unknown>
  sort_order: number
  is_active: boolean
  max_items: number
  view_all_href: string | null
  updated_at: string
}

export interface ShelfCreate {
  slug: string
  heading: string
  description?: string
  query_kind: HomeShelfQueryKind
  query_params?: Record<string, unknown>
  sort_order?: number
  is_active?: boolean
  max_items?: number
  view_all_href?: string | null
}

export type ShelfUpdate = Partial<ShelfCreate>

// ---- Page config --------------------------------------------------------
export interface HomePageConfigRead {
  eyebrow: string | null
  hero_visible: boolean
  picks_link_label: string | null
  picks_link_href: string | null
  empty_state_message: string | null
}

export type HomePageConfigUpdate = Partial<HomePageConfigRead>

// ---- Public payload -----------------------------------------------------
export interface PublicShelfRead {
  id: number
  slug: string
  heading: string
  description: string
  view_all_href: string | null
  items: HomeItemCard[]
}

export interface HomePageRead {
  config: HomePageConfigRead | null
  hero: HeroPickRead | null
  shelves: PublicShelfRead[]
}

// ---- Endpoints ----------------------------------------------------------

export function getHomePage(): Promise<HomePageRead> {
  return fetchApi<HomePageRead>('/home/page')
}

// Hero picks
export function listHeroPicks(): Promise<HeroPickRead[]> {
  return fetchApi<HeroPickRead[]>('/home/admin/hero-picks')
}

export function createHeroPick(body: HeroPickCreate): Promise<HeroPickRead> {
  return fetchApi<HeroPickRead>('/home/admin/hero-picks', { method: 'POST', body })
}

export function updateHeroPick(id: number, body: HeroPickUpdate): Promise<HeroPickRead> {
  return fetchApi<HeroPickRead>(`/home/admin/hero-picks/${id}`, { method: 'PATCH', body })
}

export function deleteHeroPick(id: number): Promise<void> {
  return fetchApi<void>(`/home/admin/hero-picks/${id}`, { method: 'DELETE' })
}

// Shelves
export function listShelves(): Promise<ShelfAdminRead[]> {
  return fetchApi<ShelfAdminRead[]>('/home/admin/shelves')
}

export function createShelf(body: ShelfCreate): Promise<ShelfAdminRead> {
  return fetchApi<ShelfAdminRead>('/home/admin/shelves', { method: 'POST', body })
}

export function updateShelf(id: number, body: ShelfUpdate): Promise<ShelfAdminRead> {
  return fetchApi<ShelfAdminRead>(`/home/admin/shelves/${id}`, { method: 'PATCH', body })
}

export function deleteShelf(id: number): Promise<void> {
  return fetchApi<void>(`/home/admin/shelves/${id}`, { method: 'DELETE' })
}

// Config (singleton)
export function getHomeConfig(): Promise<HomePageConfigRead> {
  return fetchApi<HomePageConfigRead>('/home/admin/config')
}

export function updateHomeConfig(body: HomePageConfigUpdate): Promise<HomePageConfigRead> {
  return fetchApi<HomePageConfigRead>('/home/admin/config', { method: 'PATCH', body })
}

// ---- Catalog item picker helper ----------------------------------------
// Reuses the catalog search shape: GET /catalog?q=...&limit=N.
export interface CatalogPickerResult {
  id: number
  title: string
  author: string | null
  item_type: string | null
  cover_url?: string | null
}

export async function searchCatalogForPicker(
  q: string,
  limit = 10
): Promise<CatalogPickerResult[]> {
  if (!q.trim()) return []
  const data = await fetchApi<{ items?: CatalogPickerResult[] }>(
    `/catalog?q=${encodeURIComponent(q)}&limit=${limit}`
  )
  return data.items ?? []
}
