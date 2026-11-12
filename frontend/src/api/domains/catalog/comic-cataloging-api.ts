/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================

export interface ComicSeries {
  id: number
  title: string
  sort_title: string | null
  description: string | null
  publisher: string
  publisher_imprint: string | null
  original_language: string
  comic_format: string
  is_ongoing: boolean
  first_publication_year: number | null
  last_publication_year: number | null
  total_issues_published: number | null
  total_volumes: number | null
  genres: string[] | null
  characters: string[] | null
  is_crossover_series: boolean
  cover_image_url: string | null
  series_logo_url: string | null
  created_at: string
  updated_at: string | null
}

export interface ComicSeriesDetail extends ComicSeries {
  issue_count: number | null
  story_arc_count: number | null
}

export interface ComicSeriesCreate {
  title: string
  sort_title?: string
  description?: string
  publisher: string
  publisher_imprint?: string
  original_language?: string
  comic_format?: string
  is_ongoing?: boolean
  first_publication_year?: number
  last_publication_year?: number
  total_issues_published?: number
  total_volumes?: number
  genres?: string[]
  characters?: string[]
  is_crossover_series?: boolean
  cover_image_url?: string
  series_logo_url?: string
}

export interface ComicSeriesUpdate {
  title?: string
  sort_title?: string
  description?: string
  publisher?: string
  publisher_imprint?: string
  original_language?: string
  comic_format?: string
  is_ongoing?: boolean
  first_publication_year?: number
  last_publication_year?: number
  total_issues_published?: number
  total_volumes?: number
  genres?: string[]
  characters?: string[]
  is_crossover_series?: boolean
  cover_image_url?: string
  series_logo_url?: string
}

export interface ComicIssue {
  id: number
  series_id: number
  catalog_item_id: number
  issue_number: string
  variant_designation: string | null
  issue_title: string | null
  is_annual: boolean
  is_special: boolean
  volume_number: number | null
  collected_issues: string[] | null
  publication_date: string | null
  cover_date: string | null
  isbn: string | null
  upc_code: string | null
  story_synopsis: string | null
  story_arcs_involved: string[] | null
  writers: string[] | null
  artists: string[] | null
  colorists: string[] | null
  letterers: string[] | null
  editor: string | null
  page_count: number | null
  is_color: boolean | null
  content_warnings: string[] | null
  rating: string | null
  parental_advisory: string | null
  has_variant_covers: boolean
  first_appearance_characters: string[] | null
  guest_stars: string[] | null
  is_part_of_crossover: boolean
  crossover_event: string | null
  created_at: string
  updated_at: string | null
}

export interface ComicIssueDetail extends ComicIssue {
  variant_covers: VariantCover[] | null
  creators: ComicIssueCreator[] | null
  content_advisories: ComicContentAdvisory[] | null
}

export interface ComicIssueCreate {
  series_id: number
  catalog_item_id: number
  issue_number: string
  variant_designation?: string
  issue_title?: string
  is_annual?: boolean
  is_special?: boolean
  volume_number?: number
  collected_issues?: string[]
  publication_date?: string
  cover_date?: string
  isbn?: string
  upc_code?: string
  story_synopsis?: string
  story_arcs_involved?: string[]
  writers?: string[]
  artists?: string[]
  colorists?: string[]
  letterers?: string[]
  editor?: string
  page_count?: number
  is_color?: boolean
  content_warnings?: string[]
  rating?: string
  parental_advisory?: string
  has_variant_covers?: boolean
  first_appearance_characters?: string[]
  guest_stars?: string[]
  is_part_of_crossover?: boolean
  crossover_event?: string
}

export interface QuickAddComicIssueRequest {
  series_id: number
  issue_number: string
  catalog_item_id: number
  issue_title?: string
  publication_date?: string
  isbn?: string
  page_count?: number
}

export interface VariantCover {
  id: number
  issue_id: number
  variant_type: string
  variant_name: string | null
  cover_artist: string | null
  print_run: string | null
  retailer_exclusive: string | null
  production_notes: string | null
  cover_image_url: string | null
  thumbnail_url: string | null
  created_at: string
}

export interface VariantCoverCreate {
  issue_id: number
  variant_type: string
  variant_name?: string
  cover_artist?: string
  print_run?: string
  retailer_exclusive?: string
  production_notes?: string
  cover_image_url?: string
  thumbnail_url?: string
}

export interface ComicIssueCreator {
  id: number
  issue_id: number
  creator_name: string
  creator_role: string
  display_order: number | null
  creator_authority_id: string | null
  creator_authority_source: string | null
  created_at: string
}

export interface ComicIssueCreatorCreate {
  issue_id: number
  creator_name: string
  creator_role: string
  display_order?: number
  creator_authority_id?: string
  creator_authority_source?: string
}

export interface StoryArc {
  id: number
  series_id: number
  arc_title: string
  description: string | null
  is_crossover: boolean
  crossover_event_name: string | null
  related_series: string[] | null
  start_issue_number: string | null
  end_issue_number: string | null
  issue_count: number | null
  start_publication_date: string | null
  end_publication_date: string | null
  sequence_number: number | null
  is_prequel: boolean
  is_sequel: boolean
  sequel_to_arc_id: number | null
  themes: string[] | null
  characters_involved: string[] | null
  plot_summary: string | null
  recommended_reading_order: boolean
  skip_notes: string | null
  contains_major_spoilers_for: string[] | null
  created_at: string
  updated_at: string | null
}

export interface StoryArcCreate {
  series_id: number
  arc_title: string
  description?: string
  is_crossover?: boolean
  crossover_event_name?: string
  related_series?: string[]
  start_issue_number?: string
  end_issue_number?: string
  issue_count?: number
  sequence_number?: number
  is_prequel?: boolean
  is_sequel?: boolean
  themes?: string[]
  characters_involved?: string[]
  plot_summary?: string
  recommended_reading_order?: boolean
  skip_notes?: string
}

export interface ComicContentAdvisory {
  id: number
  issue_id: number
  warning_type: string
  severity: string | null
  description: string
  appears_in_pages: string | null
  recurring: boolean
  created_at: string
}

export interface ComicContentAdvisoryCreate {
  issue_id: number
  warning_type: string
  severity?: string
  description: string
  appears_in_pages?: string
  recurring?: boolean
}

export interface ReadingOrderEvent {
  id: number
  event_name: string
  description: string | null
  event_type: string | null
  primary_series: string[] | null
  crossover_series: string[] | null
  total_issues: number | null
  start_date: string | null
  end_date: string | null
  created_at: string
  updated_at: string | null
}

export interface ReadingOrderEventCreate {
  event_name: string
  description?: string
  event_type?: string
  primary_series?: string[]
  crossover_series?: string[]
  total_issues?: number
  start_date?: string
  end_date?: string
}

// ==================== Comic Series API ====================

export async function listComicSeries(publisher?: string, skip = 0, limit = 20): Promise<ComicSeries[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (publisher) params.set('publisher', publisher)
  params.set('skip', String(skip))
  params.set('limit', String(limit))
  return fetchApi(`/comic-cataloging/series?${params}`, {
    ...(token ? { token } : {}),
  })
}

export async function getComicSeries(seriesId: number): Promise<ComicSeriesDetail> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/series/${seriesId}`, {
    ...(token ? { token } : {}),
  })
}

export async function createComicSeries(data: ComicSeriesCreate): Promise<ComicSeries> {
  const token = getAccessToken()
  return fetchApi('/comic-cataloging/series', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function updateComicSeries(seriesId: number, data: ComicSeriesUpdate): Promise<ComicSeries> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/series/${seriesId}`, {
    method: 'PUT',
    body: data,
    ...(token ? { token } : {}),
  })
}

// ==================== Comic Issues API ====================

export async function listComicIssues(seriesId?: number, skip = 0, limit = 20): Promise<ComicIssue[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (seriesId) params.set('series_id', String(seriesId))
  params.set('skip', String(skip))
  params.set('limit', String(limit))
  return fetchApi(`/comic-cataloging/issues?${params}`, {
    ...(token ? { token } : {}),
  })
}

export async function getComicIssue(issueId: number): Promise<ComicIssueDetail> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}`, {
    ...(token ? { token } : {}),
  })
}

export async function createComicIssue(data: ComicIssueCreate): Promise<ComicIssue> {
  const token = getAccessToken()
  return fetchApi('/comic-cataloging/issues', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function quickAddComicIssue(data: QuickAddComicIssueRequest): Promise<ComicIssue> {
  const token = getAccessToken()
  return fetchApi('/comic-cataloging/issues/quick-add', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}


// ==================== Variant Covers API ====================

export async function listVariantCovers(issueId: number): Promise<VariantCover[]> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/variants`, {
    ...(token ? { token } : {}),
  })
}

export async function createVariantCover(issueId: number, data: Omit<VariantCoverCreate, 'issue_id'>): Promise<VariantCover> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/variants`, {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

// ==================== Creators API ====================

export async function listIssueCreators(issueId: number): Promise<ComicIssueCreator[]> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/creators`, {
    ...(token ? { token } : {}),
  })
}

export async function addIssueCreator(issueId: number, data: Omit<ComicIssueCreatorCreate, 'issue_id'>): Promise<ComicIssueCreator> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/creators`, {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

// ==================== Story Arcs API ====================

export async function listStoryArcs(seriesId: number, skip = 0, limit = 20): Promise<StoryArc[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  params.set('skip', String(skip))
  params.set('limit', String(limit))
  return fetchApi(`/comic-cataloging/series/${seriesId}/story-arcs?${params}`, {
    ...(token ? { token } : {}),
  })
}

export async function createStoryArc(data: StoryArcCreate): Promise<StoryArc> {
  const token = getAccessToken()
  return fetchApi('/comic-cataloging/story-arcs', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}


// ==================== Content Advisories API ====================

export async function listContentAdvisories(issueId: number): Promise<ComicContentAdvisory[]> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/advisories`, {
    ...(token ? { token } : {}),
  })
}

export async function createContentAdvisory(issueId: number, data: Omit<ComicContentAdvisoryCreate, 'issue_id'>): Promise<ComicContentAdvisory> {
  const token = getAccessToken()
  return fetchApi(`/comic-cataloging/issues/${issueId}/advisories`, {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

// ==================== Reading Order Events API ====================

export async function listReadingOrderEvents(skip = 0, limit = 20): Promise<ReadingOrderEvent[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  params.set('skip', String(skip))
  params.set('limit', String(limit))
  return fetchApi(`/comic-cataloging/reading-order-events?${params}`, {
    ...(token ? { token } : {}),
  })
}

export async function createReadingOrderEvent(data: ReadingOrderEventCreate): Promise<ReadingOrderEvent> {
  const token = getAccessToken()
  return fetchApi('/comic-cataloging/reading-order-events', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}
