/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Source Definitions ====================

export type SearchSource = 'local-catalog' | 'open-library' | 'google-books' | 'worldcat' | 'isbn-search'

export interface SearchSourceConfig {
  /** Unique identifier for the source */
  id: SearchSource
  /** Display name for the source */
  name: string
  /** Description of the source */
  description: string
  /** Icon identifier (lucide-react icon name) */
  icon: string
  /** Whether this source is enabled by default */
  enabled: boolean
  /** Whether this source requires authentication */
  requiresAuth: boolean
  /** Average confidence score (0-100) for this source's results */
  averageConfidence: number
  /** Estimated response time in milliseconds */
  estimatedResponseTime: number
}

// ==================== Search Query & Filters ====================

export interface SearchFilters {
  /** Filter by publication year range */
  yearFrom?: number
  yearTo?: number
  /** Filter by item types (book, ebook, audiobook, etc.) */
  itemTypes?: string[]
  /** Filter by language codes */
  languages?: string[]
  /** Filter by availability status */
  availability?: 'available' | 'checked-out' | 'any'
  /** Filter by rating (minimum star rating) */
  minRating?: number
  /** Filter by specific subjects/topics */
  subjects?: string[]
  /** Filter by authors */
  authors?: string[]
}

export interface FederatedSearchQuery {
  /** Search query string */
  q: string
  /** Sources to query (empty = all enabled sources) */
  sources?: SearchSource[]
  /** Advanced filters */
  filters?: SearchFilters
  /** Current page number (1-based) */
  page?: number
  /** Results per page */
  perPage?: number
  /** Sort field and direction */
  sortBy?: 'relevance' | 'title' | 'author' | 'year' | 'rating'
  sortDirection?: 'asc' | 'desc'
  /** Request timeout in milliseconds */
  timeout?: number
}

// ==================== Search Results ====================

export interface ResultAttribution {
  /** Source ID that provided this result */
  source: SearchSource
  /** Relevance score from this source (0-100) */
  score: number
  /** Whether this result is the primary result for this source */
  isPrimary: boolean
  /** Timestamp when this result was fetched */
  fetchedAt: string
  /** External URL for this result on the source */
  sourceUrl?: string
  /** Additional metadata from the source */
  sourceMetadata?: Record<string, unknown>
}

export interface DeduplicationInfo {
  /** Unique fingerprint identifying this resource */
  fingerprint: string
  /** Whether this result was merged from multiple sources */
  merged: boolean
  /** Number of sources providing this result */
  matchCount: number
  /** List of sources that provided this result */
  matchedSources: SearchSource[]
  /** Confidence score for the merge (0-100) */
  confidence: number
  /** Reason for merge (if applicable) */
  mergeReason?: string
}

export interface FederatedSearchResult {
  /** Unique result identifier (combination of fingerprint and primary source) */
  id: string
  /** Resource title */
  title: string
  /** Primary author(s) */
  author?: string
  /** Extended description */
  description?: string
  /** ISBN-13 identifier */
  isbn?: string
  /** ISBN-10 identifier */
  isbn10?: string
  /** Publication year */
  year?: number
  /** Publisher name */
  publisher?: string
  /** Page count */
  pageCount?: number
  /** Language code(s) */
  language?: string[]
  /** Cover image URL */
  coverUrl?: string
  /** Average rating (0-5 stars) */
  rating?: number
  /** Number of ratings */
  ratingCount?: number
  /** Item type (book, ebook, audiobook, etc.) */
  itemType: string
  /** Item availability status */
  availability?: 'available' | 'checked-out' | 'unknown'
  /** Subject tags/categories */
  subjects?: string[]
  /** Attribution information from sources */
  attribution: ResultAttribution[]
  /** Deduplication metadata */
  deduplication: DeduplicationInfo
  /** Overall relevance score (0-100) */
  relevanceScore: number
  /** Timestamp of result creation */
  createdAt: string
}

export interface FederatedSearchResponse {
  /** Array of search results */
  results: FederatedSearchResult[]
  /** Total number of results (approximate for federated searches) */
  total: number
  /** Current page number */
  page: number
  /** Results per page */
  perPage: number
  /** Total number of pages */
  pages: number
  /** Query that was executed */
  query: string
  /** Sources that were queried */
  queriedSources: SearchSource[]
  /** Number of sources that returned results */
  sourcesWithResults: number
  /** Timestamp of the search */
  searchedAt: string
  /** Time taken to complete search in milliseconds */
  executionTimeMs: number
}

// ==================== Search State & UI ====================

export interface SourceSearchStatus {
  /** Source identifier */
  source: SearchSource
  /** Current status */
  status: 'pending' | 'loading' | 'success' | 'error' | 'cancelled'
  /** Error message if status is 'error' */
  error?: string
  /** Number of results from this source */
  resultCount?: number
  /** Time taken in milliseconds */
  timeMs?: number
}

export interface FederatedSearchState {
  /** Current search query */
  query: string
  /** Search filters */
  filters?: SearchFilters
  /** Overall search status */
  status: 'idle' | 'searching' | 'success' | 'error' | 'cancelled'
  /** Current page */
  page: number
  /** Search results */
  results: FederatedSearchResult[]
  /** Total results count */
  total: number
  /** Per-source search status */
  sourceStatus: SourceSearchStatus[]
  /** Overall error message */
  error?: string
  /** Time taken in milliseconds */
  timeMs?: number
  /** Search timestamp */
  searchedAt?: string
}

export interface SearchHistoryEntry {
  /** Query string */
  query: string
  /** Sources used */
  sources: SearchSource[]
  /** Filters applied */
  filters?: SearchFilters
  /** Timestamp of search */
  timestamp: string
  /** Number of results found */
  resultCount?: number
  /** Search ID for reference */
  searchId: string
}

export interface CachedSearchResult {
  /** Cache key (hash of query + filters + sources) */
  cacheKey: string
  /** Search result data */
  data: FederatedSearchResponse
  /** Time when cache was created */
  createdAt: string
  /** Time when cache expires */
  expiresAt: string
  /** Hit count (number of times used) */
  hitCount: number
  /** Last time this cache was accessed */
  lastAccessedAt: string
}

// ==================== Source Selection & Preferences ====================

export interface FederatedSearchPreferences {
  /** Enabled sources for this user */
  enabledSources: SearchSource[]
  /** Default sort order */
  defaultSort: 'relevance' | 'title' | 'author' | 'year' | 'rating'
  /** Results per page preference */
  resultsPerPage: number
  /** Show attribution info */
  showAttribution: boolean
  /** Show deduplication confidence */
  showConfidence: boolean
  /** Enable auto-deduplication */
  autoDeduplication: boolean
  /** Cache results */
  cacheResults: boolean
  /** Cache duration in seconds */
  cacheDurationSeconds: number
}

// ==================== Error Types ====================

export interface FederatedSearchError {
  /** Error code */
  code: 'timeout' | 'network' | 'invalid-query' | 'permission-denied' | 'unknown'
  /** Human-readable error message */
  message: string
  /** Source that generated the error (if applicable) */
  source?: SearchSource
  /** Additional error details */
  details?: Record<string, unknown>
}

// ==================== Type Guards ====================

export function isSearchSource(value: unknown): value is SearchSource {
  return typeof value === 'string' && ['local-catalog', 'open-library', 'google-books', 'worldcat', 'isbn-search'].includes(value)
}

export function isFederatedSearchResult(value: unknown): value is FederatedSearchResult {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'title' in value &&
    'itemType' in value &&
    'attribution' in value &&
    'deduplication' in value &&
    'relevanceScore' in value &&
    'createdAt' in value
  )
}

export function isFederatedSearchResponse(value: unknown): value is FederatedSearchResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    'results' in value &&
    'total' in value &&
    'page' in value &&
    'query' in value &&
    'searchedAt' in value
  )
}
