/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { BarChart3 } from 'lucide-react'

import { useTranslation } from '@/i18n'
import { getEmbeddingStats } from '@/api/domains/catalog/semantic-search-api'
import { AccordionSection, StatCard } from '../../semantic-search/SemanticSearchPrimitives'

interface Props {
  expanded: boolean
  onToggle: () => void
}

export function EmbeddingStatsPanel({ expanded, onToggle }: Props) {
  const { t } = useTranslation()

  const { data: stats } = useQuery({
    queryKey: ['embedding-stats'],
    queryFn: getEmbeddingStats,
    staleTime: 1000 * 30,
  })

  return (
    <AccordionSection
      id="stats"
      title="Embedding Statistics"
      icon={<BarChart3 className="h-5 w-5 text-earth-600" />}
      expanded={expanded}
      onToggle={onToggle}
    >
      {stats ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total Entries" value={stats.total_embeddings.toLocaleString()} />
            <StatCard label="Generated" value={stats.embedded_count.toLocaleString()} color="text-status-success-700 dark:text-status-success-300" bg="bg-status-success-50 dark:bg-status-success-900/20" />
            <StatCard label="Pending" value={stats.pending_count.toLocaleString()} color="text-status-warning-700 dark:text-status-warning-300" bg="bg-status-warning-50 dark:bg-status-warning-900/20" />
            <StatCard label="Failed" value={stats.failed_count.toLocaleString()} color="text-status-danger-700 dark:text-status-danger-300" bg="bg-status-danger-50 dark:bg-status-danger-900/20" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-earth-600 dark:text-earth-300">Coverage</span>
              <span className="text-xs text-earth-600 dark:text-earth-300 tabular-nums">{stats.embedding_coverage_percent}%</span>
            </div>
            <div className="w-full bg-earth-100 dark:bg-earth-700 rounded-full h-3 overflow-hidden">
              <div className="h-3 rounded-full bg-gradient-to-r from-indigo-500 to-category-500 transition-all duration-700" style={{ width: `${stats.embedding_coverage_percent}%` }} />
            </div>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Author Embeddings</p>
              <p className="font-semibold text-earth-900 dark:text-earth-100 tabular-nums">{stats.author_embeddings_count.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Embedding Model</p>
              <p className="font-semibold text-earth-900 dark:text-earth-100 font-mono text-sm">{stats.embedding_model}</p>
            </div>
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Last Generated</p>
              <p className="font-semibold text-earth-900 dark:text-earth-100 text-sm">
                {stats.last_embedding_generated_at ? new Date(stats.last_embedding_generated_at).toLocaleString() : 'Never'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-earth-600 dark:text-earth-300">{t('admin.adminSemanticSearch.noEmbeddingStatisticsAvailableYet')}</p>
      )}
    </AccordionSection>
  )
}
