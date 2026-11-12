/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Clock, Star, Plus, Loader2, XCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { LegalReviewCycle, LegalGlossaryTerm, LegalGlossaryTermCreateRequest } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface LegalReviewsTabProps {
  reviewCycles: LegalReviewCycle[]
  reviewsLoading: boolean
  glossaryData: { total: number; terms: LegalGlossaryTerm[] } | undefined
  formatDate: (dateStr: string) => string
  onAddGlossaryTerm: (data: LegalGlossaryTermCreateRequest) => void
  savingGlossaryTerm?: boolean
}

export function LegalReviewsTab({ reviewCycles, reviewsLoading, glossaryData, formatDate, onAddGlossaryTerm, savingGlossaryTerm }: LegalReviewsTabProps) {
  const { t } = useTranslation()
  const [showGlossaryModal, setShowGlossaryModal] = useState(false)
  const [glossaryForm, setGlossaryForm] = useState({ term: '', slug: '', definition_standard: '' })

  return (
    <div className="space-y-6">
      <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Reviews & Moderation</h2>

      <div>
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-earth-50 mb-3">Document Review Cycles</h3>
        {reviewsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : reviewCycles.length > 0 ? (
          <div className="space-y-3">
            {reviewCycles.map(cycle => (
              <div key={cycle.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50 text-sm">{cycle.document?.title || 'Untitled Document'}</p>
                    <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {cycle.due_date && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />Due: {formatDate(cycle.due_date)}</span>}
                      {cycle.assigned_to?.name && <span>Assigned to: {cycle.assigned_to.name}</span>}
                      <span>{cycle.review_count} reviews</span>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${cycle.status === 'completed' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : cycle.status === 'in_progress' ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light' : 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'}`}>
                    {cycle.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Star className="w-10 h-10 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminLegal.noReviewCyclesPending')}</p>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-lsc-dark dark:text-earth-50">Legal Glossary Terms ({glossaryData?.total ?? 0})</h3>
          <button
            onClick={() => { setGlossaryForm({ term: '', slug: '', definition_standard: '' }); setShowGlossaryModal(true) }}
            className="flex items-center gap-1 px-3 py-1.5 bg-lsc-rose text-white rounded-lg text-xs font-medium"
          >
            <Plus className="w-3 h-3" />
            Add Term
          </button>
        </div>
        {glossaryData?.terms && glossaryData.terms.length > 0 ? (
          <div className="grid sm:grid-cols-2 gap-2">
            {glossaryData.terms.slice(0, 10).map(term => (
              <div key={term.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-3 border border-lsc-border dark:border-earth-700 flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-earth-50 text-sm">{term.term}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-1" title={term.definition_standard}>{term.definition_standard}</p>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-xs ${term.is_active ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                  {term.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">No glossary terms.</p>
        )}
      </div>

      {showGlossaryModal && (
        <ModalBackdrop onClose={() => setShowGlossaryModal(false)} title={t('admin.adminLegal.addGlossaryTerm')}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-lsc-border dark:border-earth-700">
              <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.addGlossaryTerm')}</h2>
              <button
                onClick={() => setShowGlossaryModal(false)}
                aria-label={t('aria.adminLegal.closeModal')}
                className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
              >
                <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label htmlFor="glossary-term" className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('admin.adminLegal.term')} *</label>
                <input
                  id="glossary-term"
                  type="text"
                  value={glossaryForm.term}
                  onChange={e => {
                    const term = e.target.value
                    setGlossaryForm(f => ({ ...f, term, slug: f.slug || term.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') }))
                  }}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm"
                />
              </div>
              <div>
                <label htmlFor="glossary-slug" className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Slug</label>
                <input
                  id="glossary-slug"
                  type="text"
                  value={glossaryForm.slug}
                  onChange={e => setGlossaryForm(f => ({ ...f, slug: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm font-mono"
                />
              </div>
              <div>
                <label htmlFor="glossary-definition" className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('admin.adminLegal.definition')} *</label>
                <textarea
                  id="glossary-definition"
                  value={glossaryForm.definition_standard}
                  onChange={e => setGlossaryForm(f => ({ ...f, definition_standard: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-lsc-border dark:border-earth-700">
              <button onClick={() => setShowGlossaryModal(false)} className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm">
                Cancel
              </button>
              <button
                onClick={() => { onAddGlossaryTerm({ term: glossaryForm.term, slug: glossaryForm.slug, definition_standard: glossaryForm.definition_standard }); setShowGlossaryModal(false) }}
                disabled={savingGlossaryTerm || !glossaryForm.term || !glossaryForm.slug || !glossaryForm.definition_standard}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {savingGlossaryTerm && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {t('admin.adminLegal.addTerm')}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}
