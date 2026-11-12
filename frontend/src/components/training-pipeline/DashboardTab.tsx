/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Loader, AlertTriangle, ClipboardCheck, Database,
  TrendingUp, Users, FileText, Zap, BarChart3,
} from 'lucide-react'
import type {
  TrainingStats, PipelineStats, ReadinessResult,
} from '../../api/training-pipeline-api'
import { StatCard, ProgressBar } from './training-primitives'

export function DashboardTab({ training, pipeline, readiness, loading }: {
  training: TrainingStats | null; pipeline: PipelineStats | null; readiness: Record<string, ReadinessResult>; loading: boolean
}) {
  if (loading) return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!training || !pipeline) return null

  const domains = Object.keys(training.by_persona)
  const sources = Object.entries(training.by_source)

  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Examples" value={training.total_examples} icon={Database} />
        <StatCard label="Pending Review" value={training.pending_review} icon={ClipboardCheck}
          {...(training.pending_review > 0 && { color: 'text-status-warning-600 dark:text-status-warning-400' })} />
        <StatCard label="Avg Quality" value={`${training.average_quality_score}`} icon={TrendingUp}
          sublabel="out of 100" />
        <StatCard label="Knowledge Entries" value={pipeline.total_entries} icon={FileText} />
      </div>

      {/* Per-persona breakdown */}
      {domains.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Users className="w-4 h-4" /> Per-Persona Breakdown
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lsc-dark/70 dark:text-lsc-cream/60 border-b border-lsc-border dark:border-earth-700">
                  <th className="pb-2 pr-4">Persona</th>
                  <th className="pb-2 pr-4 text-right">Approved</th>
                  <th className="pb-2 pr-4 text-right">Review</th>
                  <th className="pb-2 pr-4 text-right">Rejected</th>
                  <th className="pb-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {domains.map(domain => {
                  const d = training.by_persona[domain]
                  if (!d) return null
                  return (
                    <tr key={domain} className="border-b border-lsc-border/50 dark:border-earth-700/50">
                      <td className="py-2 pr-4 font-medium text-lsc-dark dark:text-lsc-cream capitalize">{domain}</td>
                      <td className="py-2 pr-4 text-right text-status-success-600 dark:text-status-success-400">{d.approved}</td>
                      <td className="py-2 pr-4 text-right text-status-warning-600 dark:text-status-warning-400">{d.review}</td>
                      <td className="py-2 pr-4 text-right text-status-danger-600 dark:text-status-danger-400">{d.rejected}</td>
                      <td className="py-2 text-right font-medium text-lsc-dark dark:text-lsc-cream">{d.total}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Readiness meters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4" /> Fine-Tuning Readiness
        </h3>
        {Object.keys(readiness).length === 0 ? (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">No persona data yet. Process a batch to see readiness.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(readiness).map(([domain, r]) => (
              <div key={domain}>
                <ProgressBar value={r.approved_count} max={r.threshold} label={domain} />
                {!r.source_diversity.compliant && (
                  <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Source diversity violation: {r.source_diversity.violations.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Source breakdown */}
      {sources.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Source Breakdown
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {sources.map(([source, count]) => (
              <div key={source} className="text-center p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{count}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 capitalize">{source.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
