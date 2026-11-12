/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { RecommendationSettings, SimilarityAlgorithm, RecommendationStats } from '../../api/recommendations-api'

export const DEFAULT_SETTINGS: RecommendationSettings = {
  id: 1,
  enabled: true,
  default_strategy: 'mixed',
  default_count: 6,
  max_count: 12,
  cache_ttl_minutes: 60,
  include_indie_books: true,
  include_events: false,
  weight_subject: 0.35,
  weight_author: 0.25,
  weight_type: 0.15,
  weight_popularity: 0.15,
  weight_recency: 0.10,
  min_similarity_score: 0.3,
  exclude_mature_content: false,
  personalization_enabled: true,
  updated_at: new Date().toISOString(),
  updated_by: null,
}

export const DEFAULT_ALGORITHMS: SimilarityAlgorithm[] = [
  {
    id: 'subject',
    name: 'Subject-Based Matching',
    description: 'Matches items with similar subjects, topics, and categories',
    enabled: true,
    weight: 0.35,
    parameters: { min_overlap: 2, boost_exact_match: true },
  },
  {
    id: 'author',
    name: 'Author Matching',
    description: 'Recommends other works by the same author or similar authors',
    enabled: true,
    weight: 0.25,
    parameters: { include_similar_authors: false },
  },
  {
    id: 'type',
    name: 'Format/Type Matching',
    description: 'Suggests items of the same format (book, audiobook, DVD, etc.)',
    enabled: true,
    weight: 0.15,
    parameters: {},
  },
  {
    id: 'collaborative',
    name: 'Collaborative Filtering',
    description: 'Based on borrowing patterns of users with similar interests',
    enabled: false,
    weight: 0.0,
    parameters: { min_common_items: 3, similarity_threshold: 0.5 },
  },
  {
    id: 'content_based',
    name: 'Content Analysis',
    description: 'Uses text analysis to find semantically similar items',
    enabled: false,
    weight: 0.0,
    parameters: { use_embeddings: false, model: 'tfidf' },
  },
]

export const DEFAULT_STATS: RecommendationStats = {
  total_recommendations_served: 0,
  unique_users_served: 0,
  click_through_rate: 0,
  average_items_shown: 0,
  most_recommended_items: [],
  algorithm_performance: [],
  recommendations_by_source: [],
  daily_stats: [],
}
