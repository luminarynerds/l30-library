/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

import { getSemanticHealth } from '@/api/domains/catalog/semantic-search-api'
import { AccordionSection } from '../../semantic-search/SemanticSearchPrimitives'

interface Props {
  expanded: boolean
  onToggle: () => void
}

export function SystemHealthPanel({ expanded, onToggle }: Props) {
  const { data: health } = useQuery({
    queryKey: ['semantic-health'],
    queryFn: getSemanticHealth,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 60,
  })

  return (
    <AccordionSection
      id="health"
      title="System Health"
      icon={<Activity className="h-5 w-5 text-status-success-500" />}
      badge={
        health ? (
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
              health.semantic_search_ready
                ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300'
            }`}
          >
            {health.semantic_search_ready ? (
              <><CheckCircle className="w-3 h-3" /> Healthy</>
            ) : (
              <><AlertCircle className="w-3 h-3" /> Initializing</>
            )}
          </span>
        ) : undefined
      }
      expanded={expanded}
      onToggle={onToggle}
    >
      {health && (
        <div className="space-y-4">
          <p className="text-sm text-earth-600 dark:text-earth-300">{health.message}</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Status</p>
              <p className="font-semibold text-sm text-earth-900 dark:text-earth-100 capitalize mt-0.5">{health.status}</p>
            </div>
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Embeddings Available</p>
              <p className="font-semibold text-sm text-earth-900 dark:text-earth-100 tabular-nums mt-0.5">{health.embeddings_available.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-xl">
              <p className="text-xs text-earth-600 dark:text-earth-300">Minimum Required</p>
              <p className="font-semibold text-sm text-earth-900 dark:text-earth-100 tabular-nums mt-0.5">{health.minimum_embeddings_required}</p>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-earth-600 dark:text-earth-300 uppercase tracking-wide mb-2">Feature Readiness</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {Object.entries(health.features).map(([feature, ready]) => (
                <div
                  key={feature}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${
                    ready
                      ? 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300'
                      : 'bg-earth-50 dark:bg-earth-700/50 text-earth-600 dark:text-earth-300'
                  }`}
                >
                  {ready ? <CheckCircle className="w-3 h-3 flex-shrink-0" /> : <XCircle className="w-3 h-3 flex-shrink-0" />}
                  <span className="capitalize">{feature.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AccordionSection>
  )
}
