/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Search, Link2,
  Check, X, Loader,
  ArrowRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'

export default function RecordLinksTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [links, setLinks] = useState<Array<{
    id: number; similarity_score: number;
    source_person_id?: number; source_document_id?: number;
    target_person_id?: number; target_document_id?: number;
    match_reasons?: string; status: string;
  }>>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadLinks()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function loadLinks() {
    try {
      setLoading(true)
      const { recordLinkingApi } = await import('@/api/genealogy-research-api')
      const data = await recordLinkingApi.list(projectId)
      setLinks(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadRecordLinks'))
    } finally {
      setLoading(false)
    }
  }

  async function handleAnalyze() {
    try {
      setAnalyzing(true)
      const { recordLinkingApi } = await import('@/api/genealogy-research-api')
      const newLinks = await recordLinkingApi.analyze(projectId)
      toast.success(t('toast.genealogyDocuments.foundLengthPotentialMatches', { length: newLinks.length }))
      loadLinks()
    } catch {
      toast.error(t('toast.genealogyDocuments.analysisFailed'))
    } finally {
      setAnalyzing(false)
    }
  }

  async function handleReview(linkId: number, status: string) {
    try {
      const { recordLinkingApi } = await import('@/api/genealogy-research-api')
      await recordLinkingApi.review(projectId, linkId, { status })
      toast.success(status === 'confirmed' ? 'Link confirmed' : 'Link rejected')
      loadLinks()
    } catch {
      toast.error(t('toast.dNALinksTab.reviewFailed'))
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Record Linking Engine</h2>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm disabled:opacity-50"
        >
          {analyzing ? <Loader className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
          {analyzing ? 'Analyzing...' : 'Find Matches'}
        </button>
      </div>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        The record linking engine uses fuzzy matching to automatically suggest connections between people and documents based on name, date, and location similarity.
      </p>

      {links.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Link2 className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noRecordLinksYetClick')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {links.map((link) => (
            <div key={link.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                    link.similarity_score >= 0.8 ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' :
                    link.similarity_score >= 0.6 ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300' :
                    'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'
                  }`}>
                    {Math.round(link.similarity_score * 100)}%
                  </div>
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {link.source_person_id ? `Person #${link.source_person_id}` : `Doc #${link.source_document_id}`}
                      {' '}<ArrowRight className="w-3 h-3 inline" />{' '}
                      {link.target_person_id ? `Person #${link.target_person_id}` : `Doc #${link.target_document_id}`}
                    </p>
                    {link.match_reasons && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                        Matched: {JSON.parse(link.match_reasons).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                {link.status === 'suggested' && (
                  <div className="flex gap-2">
                    <button onClick={() => handleReview(link.id, 'confirmed')}
                      className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:bg-status-success-900/20 rounded" title="Confirm">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleReview(link.id, 'rejected')}
                      className="p-1.5 text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 rounded" title="Reject">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
                {link.status !== 'suggested' && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    link.status === 'confirmed' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-status-danger-100 text-status-danger-700'
                  }`}>
                    {link.status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
