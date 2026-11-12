/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Loader2, Play, Zap } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import { triggerEmbeddingGeneration } from '../../semantic-search/semantic-search-api-helpers'
import { AccordionSection } from '../../semantic-search/SemanticSearchPrimitives'
import { ENTITY_TYPES } from '../../semantic-search/semantic-search-admin-data'

interface Props {
  expanded: boolean
  onToggle: () => void
}

const DEFAULT_SELECTED = ['catalog_item_combined', 'gutenberg_combined']

export function BatchGenerationPanel({ expanded, onToggle }: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [selectedEntityTypes, setSelectedEntityTypes] = useState<string[]>(DEFAULT_SELECTED)
  const [batchSize, setBatchSize] = useState(100)
  const [skipExisting, setSkipExisting] = useState(true)

  const generateMutation = useMutation({
    mutationFn: triggerEmbeddingGeneration,
    onSuccess: (data) => {
      toast.success(data.message || t('toast.adminSemanticSearch.embeddingGenerationStarted'))
      queryClient.invalidateQueries({ queryKey: ['embedding-progress'] })
      queryClient.invalidateQueries({ queryKey: ['embedding-stats'] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToStartEmbeddingGeneration')),
  })

  const toggleEntityType = (id: string) => {
    setSelectedEntityTypes((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    )
  }

  const handleGenerate = () => {
    if (selectedEntityTypes.length === 0) {
      toast.error(t('admin.adminSemanticSearch.selectAtLeastOneEntity'))
      return
    }
    generateMutation.mutate({
      entity_types: selectedEntityTypes,
      batch_size: batchSize,
      skip_existing: skipExisting,
    })
  }

  return (
    <AccordionSection
      id="generation"
      title="Batch Embedding Generation"
      icon={<Zap className="h-5 w-5 text-indigo-500" />}
      expanded={expanded}
      onToggle={onToggle}
    >
      <div className="space-y-5">
        <p className="text-sm text-earth-600 dark:text-earth-300">
          Generate vector embeddings for catalog items. Runs in the background using batched API calls.
          Estimated cost: <span className="font-mono">~$0.02 per 1M tokens</span> (text-embedding-3-small).
        </p>

        <div>
          <h4 className="text-sm font-medium text-earth-700 dark:text-earth-200 mb-3">Select Entity Types</h4>
          <div className="grid gap-3">
            {ENTITY_TYPES.map((et) => (
              <label
                key={et.id}
                className={`flex items-start gap-3 p-3 border rounded-xl cursor-pointer transition-colors ${
                  selectedEntityTypes.includes(et.id)
                    ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 dark:border-indigo-700'
                    : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-earth-300 dark:hover:border-earth-600'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedEntityTypes.includes(et.id)}
                  onChange={() => toggleEntityType(et.id)}
                  className="mt-0.5 w-4 h-4 text-indigo-600 focus:ring-indigo-500 rounded"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-earth-900 dark:text-earth-100">{et.label}</span>
                    {et.recommended && (
                      <span className="px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs rounded">Recommended</span>
                    )}
                  </div>
                  <p className="text-xs text-earth-600 dark:text-earth-300 mt-0.5">{et.description}</p>
                  <p className="text-xs font-mono text-earth-600 dark:text-earth-300 mt-1">{et.id}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-earth-700 dark:text-earth-200 mb-1">Batch Size</label>
            <input
              type="number"
              value={batchSize}
              onChange={(e) => setBatchSize(parseInt(e.target.value) || 100)}
              min={10}
              max={500}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <p className="text-xs text-earth-600 dark:text-earth-300 mt-1">{t('admin.adminSemanticSearch.embeddingsProcessedPerApiCall')}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-earth-700 dark:text-earth-200 mb-2">Options</label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={skipExisting}
                onChange={(e) => setSkipExisting(e.target.checked)}
                className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 rounded"
              />
              <span className="text-sm text-earth-700 dark:text-earth-200">Skip already-embedded items</span>
            </label>
            <p className="text-xs text-earth-600 dark:text-earth-300 mt-1 ml-6">Recommended -- only generates embeddings for new items</p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generateMutation.isPending || selectedEntityTypes.length === 0}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors shadow-sm hover:shadow-md"
        >
          {generateMutation.isPending ? (
            <><Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Starting...</>
          ) : (
            <><Play className="w-4 h-4" /> Start Embedding Generation</>
          )}
        </button>

        {generateMutation.isSuccess && (
          <div className="p-3 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl text-sm text-status-success-700 dark:text-status-success-300 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            Generation started in background. Monitor progress below.
          </div>
        )}
      </div>
    </AccordionSection>
  )
}
