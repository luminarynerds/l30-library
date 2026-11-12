/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertCircle, Settings, Clock, Zap } from 'lucide-react'
import { type EmbeddingHealthResponse } from '@/api/domains/catalog/semantic-search-api'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import { SOURCE_CONFIG, COLLECTION_OPTIONS } from './semantic-search-data'
import type { SearchMode, SearchModeConfig } from './types'

export function SemanticHealthBanner({ health }: { health: EmbeddingHealthResponse }) {
  if (health.semantic_search_ready) return null

  return (
    <div className="mb-4 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl flex items-start gap-3">
      <AlertCircle className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-status-warning-800 dark:text-status-warning-200">
          AI Search Initializing
        </p>
        <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mt-0.5">
          {health.message} — {health.embeddings_available} / {health.minimum_embeddings_required} embeddings ready.
          Keyword autocomplete is still available.
        </p>
      </div>
    </div>
  )
}

function SourceBreakdown({ breakdown }: { breakdown: Record<string, number> }) {
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {Object.entries(breakdown).map(([source, count]) => {
        const cfg = SOURCE_CONFIG[source] || { label: source, color: '' }
        const pct = Math.round((count / total) * 100)
        return (
          <div key={source} className="flex items-center gap-1.5">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
              {cfg.label}
            </span>
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
              {count} ({pct}%)
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function SearchMetaBar({
  searchTime,
  totalResults,
  mode,
  wasCached,
  crossBreakdown,
  searchModes,
}: {
  searchTime: number
  totalResults: number
  mode: SearchMode
  wasCached?: boolean
  crossBreakdown?: Record<string, number>
  searchModes: SearchModeConfig[]
}) {
  const modeConfig = searchModes.find((m: SearchModeConfig) => m.id === mode)!
  const ModeIcon = modeConfig.icon

  return (
    <div className="flex flex-col gap-1.5 mt-3">
      <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {searchTime < 1 ? '<1' : searchTime.toFixed(0)}ms
        </span>
        <span className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
          {totalResults.toLocaleString()} result{totalResults !== 1 ? 's' : ''}
        </span>
        <span className="flex items-center gap-1">
          <ModeIcon className="w-3 h-3" />
          {modeConfig.label}
        </span>
        {wasCached && (
          <span className="flex items-center gap-1 text-status-success-600 dark:text-status-success-400">
            <Zap className="w-3 h-3" />
            Cached
          </span>
        )}
      </div>
      {crossBreakdown && Object.keys(crossBreakdown).length > 0 && (
        <SourceBreakdown breakdown={crossBreakdown} />
      )}
    </div>
  )
}

export function HybridWeightSlider({
  semanticWeight,
  onChange,
}: {
  semanticWeight: number
  onChange: (w: number) => void
}) {
  const { t } = useTranslation()
  return (
    <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
          <Settings className="w-3 h-3" />
          Hybrid Blend
        </span>
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
          {Math.round(semanticWeight * 100)}% AI / {Math.round((1 - semanticWeight) * 100)}% Keyword
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Keyword</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={semanticWeight}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 h-1.5 accent-lsc-rose"
          aria-label={t('semanticSearch.adjustSemanticVsKeywordWeight')}
        />
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">AI</span>
      </div>
    </div>
  )
}

export function CollectionFilter({
  selected,
  onChange,
}: {
  selected: string[]
  onChange: (sources: string[]) => void
}) {
  const toggle = (id: string) => {
    const next = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]
    onChange(next)
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Collections:</span>
      {COLLECTION_OPTIONS.map(({ id, label, icon: Icon }) => {
        const active = selected.includes(id)
        return (
          <button
            key={id}
            onClick={() => toggle(id)}
            className={clsx(
              'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
              active
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700 hover:border-lsc-rose/30'
            )}
            aria-pressed={active}
          >
            <Icon className="w-3 h-3" />
            {label}
          </button>
        )
      })}
    </div>
  )
}
