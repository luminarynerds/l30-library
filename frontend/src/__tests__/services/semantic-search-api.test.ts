/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Semantic Search API Tests
 *
 * Tests for the semantic search API client including:
 * - Semantic search
 * - Hybrid search
 * - Cross-collection search
 * - Autocomplete
 * - Find similar items
 * - Hidden gems
 * - Similar authors
 * - Health & stats
 * - Helper functions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import {
  semanticSearch,
  hybridSearch,
  crossCollectionSearch,
  autocomplete,
  findSimilarItems,
  getHiddenGems,
  findSimilarAuthors,
  getSemanticHealth,
  getEmbeddingStats,
  getConfidenceLabel,
  getConfidenceColor,
  getSimilarityColor,
  getMatchTypeLabel,
} from '@/api/domains/catalog/semantic-search-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('Semantic Search API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== semanticSearch ====================

  describe('semanticSearch', () => {
    it('should call fetchApi with correct query params', async () => {
      const mockResponse = {
        query: 'space exploration',
        search_type: 'semantic',
        total_results: 5,
        results: [],
        search_time_ms: 100,
        embedding_time_ms: 50,
        was_cached: false,
        has_more: false,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await semanticSearch({ query: 'space exploration' })

      expect(result).toEqual(mockResponse)
      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/semantic')
      expect(callUrl).toContain('q=space+exploration')
    })

    it('should include optional parameters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await semanticSearch({
        query: 'test',
        limit: 10,
        offset: 20,
        entityTypes: ['catalog_item_combined'],
        sources: ['local', 'gutenberg'],
        minSimilarity: 0.5,
      })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('limit=10')
      expect(callUrl).toContain('offset=20')
      expect(callUrl).toContain('entity_types=catalog_item_combined')
      expect(callUrl).toContain('sources=local%2Cgutenberg')
      expect(callUrl).toContain('min_similarity=0.5')
    })

    it('should throw user-friendly error on API error', async () => {
      const apiError = { status: 500, detail: 'Server error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(semanticSearch({ query: 'test' })).rejects.toThrow('Server error')
    })

    it('should throw generic error on non-API error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network failed'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(semanticSearch({ query: 'test' })).rejects.toThrow(
        'Failed to perform semantic search'
      )
    })
  })

  // ==================== hybridSearch ====================

  describe('hybridSearch', () => {
    it('should call fetchApi with correct params', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await hybridSearch({ query: 'time travel' })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/hybrid')
      expect(callUrl).toContain('q=time+travel')
    })

    it('should include weight parameters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await hybridSearch({
        query: 'test',
        semanticWeight: 0.8,
        keywordWeight: 0.2,
      })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('semantic_weight=0.8')
      expect(callUrl).toContain('keyword_weight=0.2')
    })

    it('should throw on API error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue({ status: 500 })
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(hybridSearch({ query: 'test' })).rejects.toThrow()
    })
  })

  // ==================== crossCollectionSearch ====================

  describe('crossCollectionSearch', () => {
    it('should call correct endpoint', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await crossCollectionSearch('classic novels')

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/cross-collection')
      expect(callUrl).toContain('q=classic+novels')
    })

    it('should include pagination params', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await crossCollectionSearch('test', 10, 5)

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('limit=10')
      expect(callUrl).toContain('offset=5')
    })

    it('should throw on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(crossCollectionSearch('test')).rejects.toThrow(
        'Failed to perform cross-collection search'
      )
    })
  })

  // ==================== autocomplete ====================

  describe('autocomplete', () => {
    it('should call correct endpoint', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        query: 'har',
        suggestions: [],
        search_time_ms: 5,
        total_suggestions: 0,
        strategy: 'trigram+prefix',
      })

      await autocomplete({ query: 'har' })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/autocomplete')
      expect(callUrl).toContain('q=har')
    })

    it('should include optional params', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        query: 'test',
        suggestions: [],
        search_time_ms: 0,
        total_suggestions: 0,
        strategy: 'trigram+prefix',
      })

      await autocomplete({
        query: 'test',
        limit: 5,
        includeAuthors: false,
        includeGutenberg: false,
      })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('limit=5')
      expect(callUrl).toContain('include_authors=false')
      expect(callUrl).toContain('include_gutenberg=false')
    })

    it('should return fallback on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))

      const result = await autocomplete({ query: 'test' })

      expect(result.suggestions).toEqual([])
      expect(result.strategy).toBe('error')
    })
  })

  // ==================== findSimilarItems ====================

  describe('findSimilarItems', () => {
    it('should call correct endpoint with source and id', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await findSimilarItems('local', '123')

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/similar/local/123')
    })

    it('should include limit param', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await findSimilarItems('local', '123', 5)

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('limit=5')
    })

    it('should encode special characters in source', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await findSimilarItems('source with space', '123')

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('source%20with%20space')
    })

    it('should throw on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(findSimilarItems('local', '123')).rejects.toThrow()
    })
  })

  // ==================== getHiddenGems ====================

  describe('getHiddenGems', () => {
    it('should call correct endpoint with no params', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        gems: [],
        total: 0,
        filters: {},
        search_time_ms: 5,
      })

      await getHiddenGems()

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/hidden-gems')
    })

    it('should include all filter params', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        gems: [],
        total: 0,
        filters: {},
        search_time_ms: 5,
      })

      await getHiddenGems({
        subject: 'science fiction',
        source: 'gutenberg',
        limit: 10,
        offset: 5,
        minScore: 0.5,
      })

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('subject=science+fiction')
      expect(callUrl).toContain('source=gutenberg')
      expect(callUrl).toContain('limit=10')
      expect(callUrl).toContain('offset=5')
      expect(callUrl).toContain('min_score=0.5')
    })

    it('should return fallback on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))

      const result = await getHiddenGems()

      expect(result.gems).toEqual([])
      expect(result.total).toBe(0)
    })
  })

  // ==================== findSimilarAuthors ====================

  describe('findSimilarAuthors', () => {
    it('should call correct endpoint', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await findSimilarAuthors('Isaac Asimov')

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('/search/similar-authors')
      expect(callUrl).toContain('author=Isaac+Asimov')
    })

    it('should include limit param', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      await findSimilarAuthors('Test Author', 5)

      const callUrl = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(callUrl).toContain('limit=5')
    })

    it('should throw on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue({ status: 500 })
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(findSimilarAuthors('test')).rejects.toThrow()
    })
  })

  // ==================== getSemanticHealth ====================

  describe('getSemanticHealth', () => {
    it('should call health endpoint', async () => {
      const mockHealth = {
        status: 'healthy',
        semantic_search_ready: true,
        embeddings_available: 500,
        minimum_embeddings_required: 100,
        features: { semantic_search: true },
        message: 'All features operational',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockHealth)

      const result = await getSemanticHealth()

      expect(result.status).toBe('healthy')
      expect(result.semantic_search_ready).toBe(true)
    })

    it('should return fallback on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))

      const result = await getSemanticHealth()

      expect(result.status).toBe('initializing')
      expect(result.semantic_search_ready).toBe(false)
      expect(result.message).toContain('Unable to reach')
    })
  })

  // ==================== getEmbeddingStats ====================

  describe('getEmbeddingStats', () => {
    it('should return stats on success', async () => {
      const mockStats = {
        total_embeddings: 1000,
        embedded_count: 900,
        failed_count: 10,
        pending_count: 90,
        author_embeddings_count: 50,
        embedding_coverage_percent: 90.0,
        embedding_model: 'text-embedding-3-small',
        last_embedding_generated_at: '2024-01-01T00:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getEmbeddingStats()

      expect(result).not.toBeNull()
      expect(result!.total_embeddings).toBe(1000)
    })

    it('should return null on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('fail'))

      const result = await getEmbeddingStats()

      expect(result).toBeNull()
    })
  })
})

// ==================== Helper Functions ====================

describe('Helper Functions', () => {
  describe('getConfidenceLabel', () => {
    it('should return correct labels', () => {
      expect(getConfidenceLabel('high')).toBe('Strong match')
      expect(getConfidenceLabel('medium')).toBe('Good match')
      expect(getConfidenceLabel('low')).toBe('Possible match')
    })

    it('should return raw value for unknown confidence', () => {
      expect(getConfidenceLabel('unknown')).toBe('unknown')
    })
  })

  // Raw Tailwind color names (green/yellow/gray) were replaced by the
  // status-success/status-warning/earth design tokens (c3bf42e73).
  describe('getConfidenceColor', () => {
    it('should return the success token for high confidence', () => {
      expect(getConfidenceColor('high')).toContain('status-success')
    })

    it('should return the warning token for medium confidence', () => {
      expect(getConfidenceColor('medium')).toContain('status-warning')
    })

    it('should return the earth (neutral) token for low confidence', () => {
      expect(getConfidenceColor('low')).toContain('earth')
    })

    it('should return the earth (neutral) token for unknown', () => {
      expect(getConfidenceColor('unknown')).toContain('earth')
    })
  })

  describe('getSimilarityColor', () => {
    it('should return the success token for high scores', () => {
      expect(getSimilarityColor(0.8)).toContain('status-success')
      expect(getSimilarityColor(0.7)).toContain('status-success')
    })

    it('should return the warning token for medium scores', () => {
      expect(getSimilarityColor(0.6)).toContain('status-warning')
      expect(getSimilarityColor(0.5)).toContain('status-warning')
    })

    it('should return the earth (neutral) token for low scores', () => {
      expect(getSimilarityColor(0.3)).toContain('earth')
    })
  })

  describe('getMatchTypeLabel', () => {
    it('should return correct labels', () => {
      expect(getMatchTypeLabel('semantic')).toBe('AI Match')
      expect(getMatchTypeLabel('keyword')).toBe('Keyword')
      expect(getMatchTypeLabel('both')).toBe('AI + Keyword')
      expect(getMatchTypeLabel('prefix')).toBe('Exact')
      expect(getMatchTypeLabel('fuzzy')).toBe('Fuzzy')
      expect(getMatchTypeLabel('author_fuzzy')).toBe('Author Match')
    })

    it('should return raw value for unknown type', () => {
      expect(getMatchTypeLabel('unknown_type')).toBe('unknown_type')
    })
  })
})
