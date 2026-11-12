/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { CatalogItem } from '../catalog-api'

// ==================== Catalog Types ====================

export interface CatalogItemCreate {
  title: string
  author?: string
  item_type: string
  isbn?: string
  publisher?: string
  publication_year?: number
  description?: string
  subjects?: string
  cover_url?: string
  page_count?: number
  location?: string
  barcode?: string
  status?: string
  edition?: string
  series_name?: string
  series_number?: string
  is_large_print?: boolean
  cataloging_status?: string
  lexile_measure?: string

  // Multimedia fields - DVD/Blu-ray/Video
  director?: string
  actors?: string
  runtime_minutes?: number
  media_format?: string
  content_rating?: string
  disc_count?: number
  studio?: string

  // Multimedia fields - CD/Vinyl/Audio
  artist?: string
  track_count?: number
  music_genre?: string

  // Multimedia fields - Games
  platform?: string
  player_count?: string
  game_genre?: string

  // Multimedia fields - Equipment/Kits
  brand?: string
  model_number?: string
  dimensions?: string
  material?: string
  kit_contents?: string
}

// ==================== Catalog Functions ====================

export async function createCatalogItem(token: string, data: CatalogItemCreate): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>('/staff/catalog', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create item')
    }
    throw error
  }
}

export async function updateCatalogItem(token: string, itemId: number, data: Partial<CatalogItemCreate>): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>(`/staff/catalog/${itemId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update item')
    }
    throw error
  }
}

export async function deleteCatalogItem(token: string, itemId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/catalog/${itemId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete item')
    }
    throw error
  }
}


// ==================== Catalog Stats ====================

export interface CatalogStatsResponse {
  status_counts: Record<string, number>
  missing_covers: number
  added_this_week: number
}

export async function getCatalogStats(): Promise<CatalogStatsResponse> {
  return await fetchApi<CatalogStatsResponse>("/staff/catalog/stats")
}
