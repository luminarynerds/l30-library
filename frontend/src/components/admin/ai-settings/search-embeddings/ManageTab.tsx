/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import { SystemHealthPanel } from './SystemHealthPanel'
import { EmbeddingStatsPanel } from './EmbeddingStatsPanel'
import { BatchGenerationPanel } from './BatchGenerationPanel'
import { GenerationProgressPanel } from './GenerationProgressPanel'
import { DocumentLibraryPanel } from './DocumentLibraryPanel'
import { DiscoveryMaintenancePanel } from './DiscoveryMaintenancePanel'

const DEFAULT_EXPANDED = ['health', 'stats', 'generation']

export function ManageTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [expandedSections, setExpandedSections] = useState<string[]>(DEFAULT_EXPANDED)

  const toggle = (section: string) => () => {
    setExpandedSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section],
    )
  }

  const handleRefreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['semantic-health'] }),
      queryClient.invalidateQueries({ queryKey: ['embedding-stats'] }),
      queryClient.invalidateQueries({ queryKey: ['embedding-progress'] }),
      queryClient.invalidateQueries({ queryKey: ['library-documents'] }),
      queryClient.invalidateQueries({ queryKey: ['library-document-stats'] }),
    ])
    toast.success(t('toast.adminSemanticSearch.refreshed'))
  }

  const isExpanded = (id: string) => expandedSections.includes(id)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end gap-2">
        <Link
          to="/catalog/search"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
        >
          <ArrowRight className="w-4 h-4" />
          Go to Search UI
        </Link>
        <button
          onClick={handleRefreshAll}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 text-earth-600 dark:text-earth-300 rounded-xl hover:border-earth-300 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <SystemHealthPanel expanded={isExpanded('health')} onToggle={toggle('health')} />
      <EmbeddingStatsPanel expanded={isExpanded('stats')} onToggle={toggle('stats')} />
      <BatchGenerationPanel expanded={isExpanded('generation')} onToggle={toggle('generation')} />
      <GenerationProgressPanel expanded={isExpanded('progress')} onToggle={toggle('progress')} />
      <DocumentLibraryPanel expanded={isExpanded('documents')} onToggle={toggle('documents')} />
      <DiscoveryMaintenancePanel expanded={isExpanded('discovery')} onToggle={toggle('discovery')} />

      <div className="pt-4 border-t border-earth-100 dark:border-earth-800 flex items-center justify-between text-xs text-earth-600 dark:text-earth-300">
        <span>{t('admin.adminSemanticSearch.poweredByPgvectorHnswIndex')}</span>
        <Link to="/catalog/search" className="inline-flex items-center gap-1 hover:text-earth-600 dark:text-earth-300 dark:hover:text-earth-300">
          <ArrowRight className="w-3 h-3" />
          Test in Search UI
        </Link>
      </div>
    </div>
  )
}
