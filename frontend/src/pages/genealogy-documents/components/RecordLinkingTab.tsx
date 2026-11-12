/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Check, FileText, Link2, Loader, RefreshCw, Search, Users, X } from 'lucide-react'
import type { GenealogyDocument, PersonSummary, RecordLink } from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'

interface RecordLinkingTabProps {
  links: RecordLink[]
  persons: PersonSummary[]
  documents: GenealogyDocument[]
  loading: boolean
  onAnalyze: () => void
  onReview: (linkId: number, status: 'confirmed' | 'rejected') => void
  onRefresh: () => void
}

export function RecordLinkingTab({ links, persons, documents, loading, onAnalyze, onReview, onRefresh }: RecordLinkingTabProps) {
  const { t } = useTranslation()

  function getEntityName(personId: number | null, docId: number | null) {
    if (personId) {
      const p = persons.find(x => x.id === personId)
      return p ? `${p.given_names} ${p.surname || ''}`.trim() : `Person #${personId}`
    }
    if (docId) {
      const d = documents.find(x => x.id === docId)
      return d ? d.title : `Document #${docId}`
    }
    return 'Unknown'
  }

  function getEntityIcon(personId: number | null, docId: number | null) {
    if (personId) return <Users className="w-4 h-4 text-earth-600" />
    if (docId) return <FileText className="w-4 h-4 text-status-warning-500" />
    return null
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-status-success-700 bg-status-success-100 dark:bg-status-success-900/30 dark:text-status-success-300'
    if (score >= 0.6) return 'text-status-warning-700 bg-status-warning-100 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    return 'text-status-danger-700 bg-status-danger-100 dark:bg-status-danger-900/30 dark:text-status-danger-300'
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            The record linking engine analyzes names, dates, and locations to suggest connections between people and documents.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={onRefresh} className="p-2 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={onAnalyze}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm disabled:opacity-50"
          >
            {loading ? <Loader className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? 'Analyzing...' : 'Find Matches'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="text-center">
            <Loader className="w-8 h-8 motion-safe:animate-spin text-status-warning-500 mx-auto mb-3" />
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDocuments.analyzingDocumentsAndPersonsFor')}</p>
          </div>
        </div>
      ) : links.length === 0 ? (
        <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Link2 className="w-14 h-14 mx-auto text-earth-300 mb-4" />
          <h3 className="font-serif font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">No Pending Matches</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-5 max-w-sm mx-auto">
            All suggested links have been reviewed, or none have been found yet. Click "Find Matches" to run the analysis.
          </p>
          <button onClick={onAnalyze} className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700">
            Run Analysis
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{links.length} pending review{links.length !== 1 ? 's' : ''}</p>
          {links.map(link => {
            let matchReasons: string[] = []
            try {
              matchReasons = link.match_reasons ? JSON.parse(link.match_reasons) : []
            } catch {
              matchReasons = []
            }
            return (
              <div key={link.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
                <div className="flex items-start gap-4 justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`text-sm font-bold px-2.5 py-1 rounded-full ${getScoreColor(link.similarity_score)}`}>
                        {Math.round(link.similarity_score * 100)}% match
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <div className="flex items-center gap-1.5 font-medium text-lsc-dark dark:text-lsc-cream">
                        {getEntityIcon(link.source_person_id, link.source_document_id)}
                        {getEntityName(link.source_person_id, link.source_document_id)}
                      </div>
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">matches</span>
                      <div className="flex items-center gap-1.5 font-medium text-lsc-dark dark:text-lsc-cream">
                        {getEntityIcon(link.target_person_id, link.target_document_id)}
                        {getEntityName(link.target_person_id, link.target_document_id)}
                      </div>
                    </div>
                    {matchReasons.length > 0 && (
                      <div className="flex gap-1.5 mt-2 flex-wrap">
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Matched on:</span>
                        {matchReasons.map((reason, i) => (
                          <span key={i} className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                            {reason}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => onReview(link.id, 'confirmed')}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 text-sm"
                    >
                      <Check className="w-4 h-4" />
                      Confirm
                    </button>
                    <button
                      onClick={() => onReview(link.id, 'rejected')}
                      className="flex items-center gap-1.5 px-3 py-1.5 border border-status-danger-300 dark:border-status-danger-700 text-status-danger-600 rounded-lg hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 text-sm"
                    >
                      <X className="w-4 h-4" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
