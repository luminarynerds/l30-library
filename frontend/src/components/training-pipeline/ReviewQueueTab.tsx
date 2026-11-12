/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Loader, Check, X, ClipboardCheck,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import {
  getReviewQueue, approveExample, rejectExample, overrideExample,
} from '../../api/training-pipeline-api'
import type { TrainingExample } from '../../api/training-pipeline-api'
import { t } from '@/i18n'
import { BucketBadge, ScoreBar } from './training-primitives'

export function ReviewQueueTab({ onRefresh }: { onRefresh: () => void }) {
  const [examples, setExamples] = useState<TrainingExample[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [overrideId, setOverrideId] = useState<number | null>(null)
  const [overrideReason, setOverrideReason] = useState('')
  const [overrideBucket, setOverrideBucket] = useState('approved')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getReviewQueue(page, 20)
      setExamples(data)
    } catch (e) {
      console.error('Failed to load review queue', e)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { void load() }, [load])

  async function handleAction(id: number, action: 'approve' | 'reject') {
    setActionLoading(id)
    try {
      if (action === 'approve') await approveExample(id)
      else await rejectExample(id)
      setExamples(prev => prev.filter(e => e.id !== id))
      onRefresh()
    } catch (e) {
      console.error(`Failed to ${action} example`, e)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleOverride(id: number) {
    if (!overrideReason.trim()) return
    setActionLoading(id)
    try {
      await overrideExample(id, overrideBucket, overrideReason)
      setExamples(prev => prev.filter(e => e.id !== id))
      setOverrideId(null)
      setOverrideReason('')
      onRefresh()
    } catch (e) {
      console.error('Failed to override', e)
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>

  if (examples.length === 0) {
    return (
      <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
        <ClipboardCheck className="w-12 h-12 text-status-success-500 mx-auto mb-3" />
        <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">Review queue is empty</p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">All training examples have been reviewed.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{examples.length} examples pending review</p>
        <div className="flex gap-2">
          <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
            className="px-3 py-1 text-sm rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-40 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Page {page}</span>
          <button onClick={() => setPage(page + 1)} disabled={examples.length < 20}
            className="px-3 py-1 text-sm rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-40 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
            Next
          </button>
        </div>
      </div>

      {examples.map(ex => (
        <div key={ex.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <BucketBadge bucket={ex.bucket} />
                  <ScoreBar score={ex.quality_score} />
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 capitalize">{ex.source_type.replace(/_/g, ' ')}</span>
                  {ex.persona_domain && <span className="text-xs px-1.5 py-0.5 bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300 rounded capitalize">{ex.persona_domain}</span>}
                </div>
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={ex.instruction}>{ex.instruction}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate mt-0.5" title={ex.response}>{ex.response}</p>
              </div>

              <div className="flex items-center gap-1 flex-shrink-0">
                <button onClick={() => handleAction(ex.id, 'approve')} disabled={actionLoading === ex.id}
                  aria-label="Approve example" className="p-1.5 rounded-lg text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20" title="Approve">
                  <Check className="w-4 h-4" />
                </button>
                <button onClick={() => handleAction(ex.id, 'reject')} disabled={actionLoading === ex.id}
                  aria-label="Reject example" className="p-1.5 rounded-lg text-status-danger-600 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20" title="Reject">
                  <X className="w-4 h-4" />
                </button>
                <button onClick={() => setExpandedId(expandedId === ex.id ? null : ex.id)}
                  className="p-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50" title="Details">
                  {expandedId === ex.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          {expandedId === ex.id && (
            <div className="border-t border-lsc-border dark:border-earth-700 p-4 bg-lsc-cream/30 dark:bg-earth-900/30 space-y-3">
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">Question</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{ex.instruction}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">Answer</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{ex.response}</p>
              </div>
              {ex.quality_breakdown && (
                <div>
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">Quality Breakdown</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(ex.quality_breakdown).map(([k, v]) => (
                      <span key={k} className="text-xs px-2 py-1 bg-lsc-white dark:bg-earth-800 rounded border border-lsc-border dark:border-earth-700 capitalize">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="pt-2 border-t border-lsc-border/50 dark:border-earth-700/50">
                {overrideId === ex.id ? (
                  <div className="flex items-end gap-2">
                    <select value={overrideBucket} onChange={e => setOverrideBucket(e.target.value)}
                      className="text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-2 py-1.5">
                      <option value="approved">Approved</option>
                      <option value="review">Review</option>
                      <option value="rejected">Rejected</option>
                    </select>
                    <input value={overrideReason} onChange={e => setOverrideReason(e.target.value)} placeholder={t('placeholder.adminTrainingPipeline.reasonForOverride')}
                      className="flex-1 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-1.5" />
                    <button onClick={() => handleOverride(ex.id)} disabled={!overrideReason.trim() || actionLoading === ex.id}
                      className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-40">
                      Override
                    </button>
                    <button onClick={() => { setOverrideId(null); setOverrideReason('') }}
                      className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50">
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button onClick={() => setOverrideId(ex.id)}
                    className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose">
                    Override bucket assignment...
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
