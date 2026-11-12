/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================

export interface MangaCatalogingTemplate {
  id: number
  name: string
  description: string | null
  series_title: string
  author: string | null
  original_language: string
  publisher: string | null
  genre: string
  subjects: string
  catalog_series_type: string
  format: string
  isbn_pattern: string | null
  covers_color: boolean
  page_count_average: number | null
  default_fields: Record<string, string>
  auto_increment_volume: boolean
  auto_fetch_cover: boolean
  auto_populate_series_info: boolean
  is_shared: boolean
  created_at: string
  updated_at: string | null
}

export interface MangaVolumeRecord {
  id: number
  catalog_item_id: number
  series_title: string
  volume_number: number
  template_id: number | null
  volume_title: string | null
  isbn: string | null
  cover_image_url: string | null
  cover_fetch_source: string | null
  publication_date: string | null
  publisher: string | null
  original_language: string | null
  page_count: number | null
  is_color: boolean | null
  previous_volume_id: number | null
  created_at: string
  updated_at: string | null
}

export interface ISBNLookupResult {
  isbn: string
  found: boolean
  source: string | null
  title: string | null
  author: string | null
  publisher: string | null
  publish_date: string | null
  page_count: number | null
  cover_url: string | null
  description: string | null
  language: string | null
  subjects: string | null
}

export interface SeriesInfo {
  series_title: string
  total_volumes: number
  next_volume_number: number
  auto_populate_info: Record<string, string | boolean | null>
}

export interface QuickAddVolumeRequest {
  series_title: string
  volume_number: number
  title: string
  author?: string
  isbn?: string
  publisher?: string
  original_language?: string
  publication_date?: string
  template_id?: number
  copy_from_volume_id?: number
  auto_fetch_cover?: boolean
}

export interface CopyIncrementRequest {
  source_volume_id: number
  new_volume_number: number
  isbn?: string
}

export interface BatchCreateRequest {
  series_title: string
  template_id?: number
  start_volume?: number
  volumes: Array<{
    volume_number: number
    title: string
    isbn?: string
    author?: string
    publisher?: string
    publication_date?: string
  }>
}

export interface BatchCreateResult {
  series_title: string
  total_volumes: number
  created: number
  failed: number
  results: Array<Record<string, unknown>>
  errors: Array<Record<string, unknown>>
}

export interface MangaCatalogingStats {
  total_templates: number
  total_volumes: number
  total_series: number
  avg_volumes_per_series: number
  templates_with_auto_cover: number
}

// ==================== Template Endpoints ====================

export async function listMangaTemplates(): Promise<MangaCatalogingTemplate[]> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/templates', {
    ...(token ? { token } : {}),
  })
}

export async function getMangaTemplate(templateId: number): Promise<MangaCatalogingTemplate> {
  const token = getAccessToken()
  return fetchApi(`/manga-cataloging/templates/${templateId}`, {
    ...(token ? { token } : {}),
  })
}

export async function createMangaTemplate(
  data: Partial<MangaCatalogingTemplate>
): Promise<MangaCatalogingTemplate> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/templates', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}


export async function deleteMangaTemplate(templateId: number): Promise<void> {
  const token = getAccessToken()
  return fetchApi(`/manga-cataloging/templates/${templateId}`, {
    method: 'DELETE',
    ...(token ? { token } : {}),
    skipJsonParse: true,
  })
}

// ==================== Volume Endpoints ====================

export async function listMangaVolumes(
  seriesTitle?: string,
  page = 1,
  perPage = 20
): Promise<MangaVolumeRecord[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (seriesTitle) params.set('series_title', seriesTitle)
  params.set('page', String(page))
  params.set('per_page', String(perPage))
  return fetchApi(`/manga-cataloging/volumes?${params}`, {
    ...(token ? { token } : {}),
  })
}

// ==================== Efficiency Endpoints ====================

export async function quickAddMangaVolume(
  data: QuickAddVolumeRequest
): Promise<Record<string, unknown>> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/quick-add-volume', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function copyAndIncrementVolume(
  data: CopyIncrementRequest
): Promise<Record<string, unknown>> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/copy-and-increment', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function batchCreateMangaVolumes(
  data: BatchCreateRequest
): Promise<BatchCreateResult> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/batch-create-volumes', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function isbnLookup(isbn: string): Promise<ISBNLookupResult> {
  const token = getAccessToken()
  return fetchApi(`/manga-cataloging/isbn/${isbn}/lookup`, {
    ...(token ? { token } : {}),
  })
}

export async function fetchCoverFromISBN(isbn: string): Promise<{ isbn: string; cover_url: string | null; source: string | null }> {
  const token = getAccessToken()
  return fetchApi(`/manga-cataloging/isbn/${isbn}/cover`, {
    ...(token ? { token } : {}),
  })
}

export async function getSeriesInfo(seriesTitle: string): Promise<SeriesInfo> {
  const token = getAccessToken()
  return fetchApi(`/manga-cataloging/series/${encodeURIComponent(seriesTitle)}/info`,
    token ? { token } : {}
  )
}

export async function getMangaCatalogingStats(): Promise<MangaCatalogingStats> {
  const token = getAccessToken()
  return fetchApi('/manga-cataloging/stats', {
    ...(token ? { token } : {}),
  })
}
