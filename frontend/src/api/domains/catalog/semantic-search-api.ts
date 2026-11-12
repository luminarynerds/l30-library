/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Semantic Search API ====================
// Client for AI-powered semantic search, autocomplete, discovery, and similarity

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface SemanticSearchResult {
  id: string
  source: string
  source_id: string
  title: string
  author: string | null
  description: string | null
  cover_url: string | null
  format: string
  item_type?: string
  subjects: string[] | null
  is_available: boolean
  relevance_score: number
  similarity_score: number | null
  search_confidence: 'high' | 'medium' | 'low'
  matched_by: 'semantic' | 'keyword' | 'both'
}

export interface SemanticSearchResponse {
  query: string
  search_type: string
  total_results: number
  results: SemanticSearchResult[]
  search_time_ms: number
  embedding_time_ms: number | null
  was_cached: boolean
  has_more: boolean
}

export interface HybridSearchResponse {
  query: string
  total_results: number
  merged_results: SemanticSearchResult[]
  search_time_ms: number
  semantic_time_ms: number
  keyword_time_ms: number
  merge_strategy: string
  has_more: boolean
}

export interface CrossCollectionResponse {
  query: string
  total_results: number
  results: SemanticSearchResult[]
  source_breakdown: Record<string, number>
  search_time_ms: number
  was_cached: boolean
}

export interface AutocompleteSuggestion {
  id: string
  title: string
  author: string | null
  format: string
  source: string
  cover_url: string | null
  match_type: 'prefix' | 'fuzzy' | 'author_fuzzy'
  similarity_score: number
}

export interface AutocompleteResponse {
  query: string
  suggestions: AutocompleteSuggestion[]
  search_time_ms: number
  total_suggestions: number
  strategy: string
}

export interface SimilarItemsResponse {
  item_id: string
  item_title: string
  similar_items: SemanticSearchResult[]
  similarity_metric: string
  search_time_ms: number
}

export interface HiddenGemResult {
  entity_type: string
  entity_id: number
  source_collection: string
  title: string
  author: string | null
  subjects: string[] | null
  gem_score: number
  avg_similarity_to_popular: number
  popularity_score: number
  circulation_count: number
}

export interface HiddenGemsResponse {
  gems: HiddenGemResult[]
  total: number
  filters: Record<string, unknown>
  search_time_ms: number
}

export interface SimilarAuthor {
  author_name: string
  book_count: number
  source_collections: string[]
  genres: string[]
  shared_subjects: string[]
  similarity_score: number
}

export interface SimilarAuthorsResponse {
  author: string
  author_book_count: number
  author_genres: string[]
  similar_authors: SimilarAuthor[]
  search_time_ms: number
}

export interface EmbeddingHealthResponse {
  status: 'healthy' | 'initializing'
  semantic_search_ready: boolean
  embeddings_available: number
  minimum_embeddings_required: number
  features: Record<string, boolean>
  message: string
}

export interface EmbeddingStatsResponse {
  total_embeddings: number
  embedded_count: number
  failed_count: number
  pending_count: number
  author_embeddings_count: number
  embedding_coverage_percent: number
  embedding_model: string
  last_embedding_generated_at: string | null
}

// ==================== Search Params ====================

export interface SemanticSearchParams {
  query: string
  limit?: number
  offset?: number
  entityTypes?: string[]
  sources?: string[]
  minSimilarity?: number
}

export interface HybridSearchParams {
  query: string
  limit?: number
  offset?: number
  semanticWeight?: number
  keywordWeight?: number
  sources?: string[]
}

export interface AutocompleteParams {
  query: string
  limit?: number
  includeAuthors?: boolean
  includeGutenberg?: boolean
}

export interface HiddenGemsParams {
  subject?: string
  source?: string
  limit?: number
  offset?: number
  minScore?: number
}

// ==================== API Functions ====================

export async function semanticSearch(
  params: SemanticSearchParams
): Promise<SemanticSearchResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('q', params.query)
  if (params.limit !== undefined) urlParams.set('limit', String(params.limit))
  if (params.offset !== undefined) urlParams.set('offset', String(params.offset))
  if (params.entityTypes?.length) urlParams.set('entity_types', params.entityTypes.join(','))
  if (params.sources?.length) urlParams.set('sources', params.sources.join(','))
  if (params.minSimilarity !== undefined)
    urlParams.set('min_similarity', String(params.minSimilarity))

  try {
    return await fetchApi<SemanticSearchResponse>(`/search/semantic?${urlParams}`)
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Semantic search failed')
    throw new Error('Failed to perform semantic search')
  }
}

export async function hybridSearch(
  params: HybridSearchParams
): Promise<HybridSearchResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('q', params.query)
  if (params.limit !== undefined) urlParams.set('limit', String(params.limit))
  if (params.offset !== undefined) urlParams.set('offset', String(params.offset))
  if (params.semanticWeight !== undefined)
    urlParams.set('semantic_weight', String(params.semanticWeight))
  if (params.keywordWeight !== undefined)
    urlParams.set('keyword_weight', String(params.keywordWeight))
  if (params.sources?.length) urlParams.set('sources', params.sources.join(','))

  try {
    return await fetchApi<HybridSearchResponse>(`/search/hybrid?${urlParams}`)
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Hybrid search failed')
    throw new Error('Failed to perform hybrid search')
  }
}

export async function crossCollectionSearch(
  query: string,
  limit?: number,
  offset?: number
): Promise<CrossCollectionResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('q', query)
  if (limit !== undefined) urlParams.set('limit', String(limit))
  if (offset !== undefined) urlParams.set('offset', String(offset))

  try {
    return await fetchApi<CrossCollectionResponse>(`/search/cross-collection?${urlParams}`)
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Cross-collection search failed')
    throw new Error('Failed to perform cross-collection search')
  }
}

export async function autocomplete(
  params: AutocompleteParams
): Promise<AutocompleteResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('q', params.query)
  if (params.limit !== undefined) urlParams.set('limit', String(params.limit))
  if (params.includeAuthors !== undefined)
    urlParams.set('include_authors', String(params.includeAuthors))
  if (params.includeGutenberg !== undefined)
    urlParams.set('include_gutenberg', String(params.includeGutenberg))

  try {
    return await fetchApi<AutocompleteResponse>(`/search/autocomplete?${urlParams}`)
  } catch {
    return { query: params.query, suggestions: [], search_time_ms: 0, total_suggestions: 0, strategy: 'error' }
  }
}

export async function findSimilarItems(
  source: string,
  sourceId: string,
  limit?: number
): Promise<SimilarItemsResponse> {
  const urlParams = new URLSearchParams()
  if (limit !== undefined) urlParams.set('limit', String(limit))

  const url = `/search/similar/${encodeURIComponent(source)}/${encodeURIComponent(sourceId)}?${urlParams}`
  try {
    return await fetchApi<SimilarItemsResponse>(url)
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Similar items search failed')
    throw new Error('Failed to find similar items')
  }
}

export async function getHiddenGems(
  params: HiddenGemsParams = {}
): Promise<HiddenGemsResponse> {
  const urlParams = new URLSearchParams()
  if (params.subject) urlParams.set('subject', params.subject)
  if (params.source) urlParams.set('source', params.source)
  if (params.limit !== undefined) urlParams.set('limit', String(params.limit))
  if (params.offset !== undefined) urlParams.set('offset', String(params.offset))
  if (params.minScore !== undefined) urlParams.set('min_score', String(params.minScore))

  try {
    return await fetchApi<HiddenGemsResponse>(`/search/hidden-gems?${urlParams}`)
  } catch {
    return { gems: [], total: 0, filters: {}, search_time_ms: 0 }
  }
}

export async function findSimilarAuthors(
  author: string,
  limit?: number
): Promise<SimilarAuthorsResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('author', author)
  if (limit !== undefined) urlParams.set('limit', String(limit))

  try {
    return await fetchApi<SimilarAuthorsResponse>(`/search/similar-authors?${urlParams}`)
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Author similarity search failed')
    throw new Error('Failed to find similar authors')
  }
}

export async function getSemanticHealth(): Promise<EmbeddingHealthResponse> {
  try {
    return await fetchApi<EmbeddingHealthResponse>('/search/embeddings/health')
  } catch {
    return {
      status: 'initializing',
      semantic_search_ready: false,
      embeddings_available: 0,
      minimum_embeddings_required: 100,
      features: {},
      message: 'Unable to reach semantic search service',
    }
  }
}

export async function getEmbeddingStats(): Promise<EmbeddingStatsResponse | null> {
  try {
    return await fetchApi<EmbeddingStatsResponse>('/search/embeddings/stats')
  } catch {
    return null
  }
}

// ==================== Helpers ====================

export function getConfidenceLabel(confidence: string): string {
  const labels: Record<string, string> = {
    high: 'Strong match',
    medium: 'Good match',
    low: 'Possible match',
  }
  return labels[confidence] || confidence
}

export function getConfidenceColor(confidence: string): string {
  const colors: Record<string, string> = {
    high: 'text-status-success-700 bg-status-success-100',
    medium: 'text-status-warning-700 bg-status-warning-100',
    low: 'text-earth-600 dark:text-earth-200 bg-earth-100',
  }
  return colors[confidence] || 'text-earth-600 dark:text-earth-200 bg-earth-100'
}

export function getSimilarityColor(score: number): string {
  if (score >= 0.7) return 'text-status-success-600'
  if (score >= 0.5) return 'text-status-warning-600'
  return 'text-earth-600 dark:text-earth-200'
}

export function getMatchTypeLabel(matchType: string): string {
  const labels: Record<string, string> = {
    semantic: 'AI Match',
    keyword: 'Keyword',
    both: 'AI + Keyword',
    prefix: 'Exact',
    fuzzy: 'Fuzzy',
    author_fuzzy: 'Author Match',
  }
  return labels[matchType] || matchType
}
