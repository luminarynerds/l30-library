/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { BookOpen, Sparkles, Info } from 'lucide-react'
import {
  getConfidenceColor,
  getConfidenceLabel,
  getMatchTypeLabel,
  getSimilarityColor,
  type SemanticSearchResult,
} from '@/api/domains/catalog/semantic-search-api'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'
import { SOURCE_CONFIG } from './semantic-search-data'

export function SimilarityBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const colorClass = getSimilarityColor(score)
  return (
    <span className={`inline-flex items-center text-xs font-semibold tabular-nums ${colorClass}`}>
      {pct}% match
    </span>
  )
}

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colorClass = getConfidenceColor(confidence)
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {getConfidenceLabel(confidence)}
    </span>
  )
}

export function MatchTypeBadge({ matchType }: { matchType: string }) {
  const bgMap: Record<string, string> = {
    semantic: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
    keyword: 'bg-status-info-100 text-status-info-700 dark:bg-status-info-900/30 dark:text-status-info-300',
    both: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light',
  }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        bgMap[matchType] || 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300'
      }`}
    >
      {getMatchTypeLabel(matchType)}
    </span>
  )
}

export function SourceBadge({ source }: { source: string }) {
  const cfg = SOURCE_CONFIG[source] || { label: source, color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300' }
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

interface SearchResultCardProps {
  result: SemanticSearchResult
  onFindSimilar?: (result: SemanticSearchResult) => void
  onAuthorExplore?: (author: string) => void
  showRelevanceExplanation?: boolean
}

export function SearchResultCard({
  result,
  onFindSimilar,
  onAuthorExplore,
  showRelevanceExplanation = true,
}: SearchResultCardProps) {
  const [showExplanation, setShowExplanation] = useState(false)

  const relevanceReason = useMemo(() => {
    if (result.matched_by === 'both') {
      return `Matched by both AI semantic understanding and keyword — strong relevance to your query.`
    }
    if (result.matched_by === 'semantic') {
      return `Matched by AI — the meaning and concepts in this book align closely with your query, even if exact words differ.`
    }
    return `Matched by keyword — contains exact or near-exact terms from your search.`
  }, [result.matched_by])

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 hover:shadow-md transition-shadow bg-lsc-white dark:bg-earth-800 group">
      <div className="flex gap-4">
        <div className="flex-shrink-0 w-16 h-24 bg-earth-100 dark:bg-earth-700 rounded-lg overflow-hidden shadow-sm">
          {result.cover_url ? (
            <CatalogCover
              coverUrl={result.cover_url}
              alt={`Cover of ${result.title}`}
              title={result.title}
              {...(result.item_type ? { itemType: result.item_type } : {})}
              size="sm"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream leading-snug">
              {result.title}
            </h3>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {result.similarity_score !== null && result.similarity_score !== undefined && (
                <SimilarityBadge score={result.similarity_score} />
              )}
            </div>
          </div>

          {result.author && (
            <button
              className="text-xs text-lsc-rose hover:underline mt-0.5 text-left"
              onClick={() => onAuthorExplore?.(result.author!)}
              title="Find similar authors"
            >
              {result.author}
            </button>
          )}

          {result.description && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1.5 line-clamp-2 leading-relaxed" title={result.description}>
              {result.description}
            </p>
          )}

          {result.subjects && result.subjects.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {result.subjects.slice(0, 3).map((subj, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-earth-50 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs rounded border border-lsc-border dark:border-earth-700"
                >
                  {subj}
                </span>
              ))}
              {result.subjects.length > 3 && (
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">+{result.subjects.length - 3} more</span>
              )}
            </div>
          )}

          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            <SourceBadge source={result.source} />
            <MatchTypeBadge matchType={result.matched_by} />
            <ConfidenceBadge confidence={result.search_confidence} />
            {result.is_available ? (
              <span className="text-xs text-status-success-600 dark:text-status-success-400 font-medium">Available</span>
            ) : (
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Not Available</span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-2.5">
            {onFindSimilar && (
              <button
                onClick={() => onFindSimilar(result)}
                className="inline-flex items-center gap-1 text-xs text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:hover:text-lsc-rose-light font-medium"
              >
                <Sparkles className="w-3 h-3" />
                More like this
              </button>
            )}
            {showRelevanceExplanation && (
              <button
                onClick={() => setShowExplanation(!showExplanation)}
                className="inline-flex items-center gap-1 text-xs text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300"
              >
                <Info className="w-3 h-3" />
                Why this result?
              </button>
            )}
          </div>

          {showExplanation && (
            <div className="mt-2 p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 border border-lsc-rose/30 dark:border-lsc-rose/30 rounded-lg">
              <p className="text-xs text-lsc-rose dark:text-lsc-rose-light leading-relaxed">
                {relevanceReason}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
