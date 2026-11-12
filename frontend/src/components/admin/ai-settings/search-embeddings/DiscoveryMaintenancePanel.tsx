/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CheckCircle, Gem, Loader2, Play, Users } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  triggerAuthorEmbeddingRebuild,
  triggerGemRecalculation,
} from '../../semantic-search/semantic-search-api-helpers'
import { AccordionSection } from '../../semantic-search/SemanticSearchPrimitives'
import { clean } from '@/lib/utils'

interface Props {
  expanded: boolean
  onToggle: () => void
}

export function DiscoveryMaintenancePanel({ expanded, onToggle }: Props) {
  const { t } = useTranslation()

  const [gemSource, setGemSource] = useState('')
  const [authorBatchSize, setAuthorBatchSize] = useState(100)

  const gemMutation = useMutation({
    mutationFn: triggerGemRecalculation,
    onSuccess: (data) => toast.success(data.message || t('toast.adminSemanticSearch.hiddenGemRecalculationStarted')),
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToStartGemRecalculation')),
  })

  const authorMutation = useMutation({
    mutationFn: triggerAuthorEmbeddingRebuild,
    onSuccess: (data) => toast.success(data.message || t('toast.adminSemanticSearch.authorEmbeddingRebuildStarted')),
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToStartAuthorEmbedding')),
  })

  return (
    <AccordionSection
      id="discovery"
      title="Discovery Maintenance"
      icon={<Gem className="h-5 w-5 text-status-warning-500" />}
      expanded={expanded}
      onToggle={onToggle}
    >
      <div className="space-y-6">
        <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <div className="flex items-start gap-3 mb-3">
            <Gem className="w-5 h-5 text-status-warning-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-earth-900 dark:text-earth-100">Recalculate Hidden Gem Scores</h4>
              <p className="text-xs text-earth-600 dark:text-earth-300 mt-0.5">
                Updates gem scores based on semantic similarity to popular books and current checkout counts. Run weekly or after new items are cataloged.
              </p>
              <p className="text-xs font-mono text-earth-600 dark:text-earth-300 mt-1">
                gem_score = avg_similarity / (1 + log(circulation + 1))
              </p>
            </div>
          </div>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Source Collection (optional)</label>
              <select
                value={gemSource}
                onChange={(e) => setGemSource(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              >
                <option value="">All Collections</option>
                <option value="local">Library Catalog</option>
                <option value="gutenberg">Gutenberg</option>
              </select>
            </div>
            <button
              onClick={() => gemMutation.mutate(clean({ source_collection: gemSource || undefined, batch_size: 500 }))}
              disabled={gemMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-status-warning-600 hover:bg-status-warning-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
            >
              {gemMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Play className="w-4 h-4" />}
              Recalculate
            </button>
          </div>
        </div>

        <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <div className="flex items-start gap-3 mb-3">
            <Users className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-earth-900 dark:text-earth-100">Rebuild Author Embeddings</h4>
              <p className="text-xs text-earth-600 dark:text-earth-300 mt-0.5">
                Rebuilds author vector embeddings from individual book embeddings using centroid aggregation. Run after bulk embedding generation completes.
              </p>
            </div>
          </div>
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Batch Size</label>
              <input
                type="number"
                value={authorBatchSize}
                onChange={(e) => setAuthorBatchSize(parseInt(e.target.value) || 100)}
                min={10}
                max={500}
                className="w-32 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              />
            </div>
            <button
              onClick={() => authorMutation.mutate({ batch_size: authorBatchSize })}
              disabled={authorMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
            >
              {authorMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Play className="w-4 h-4" />}
              Rebuild Authors
            </button>
          </div>
          {authorMutation.isSuccess && (
            <p className="text-xs text-status-success-600 dark:text-status-success-400 mt-2 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" />
              Author rebuild started in background
            </p>
          )}
        </div>
      </div>
    </AccordionSection>
  )
}
