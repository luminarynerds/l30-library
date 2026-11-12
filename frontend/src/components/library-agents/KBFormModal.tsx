/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { X, Loader } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  KNOWLEDGE_CATEGORIES,
  AGENT_DEPARTMENTS,
} from '../../api/library-agents-api'
import type { KnowledgeBaseCreateData } from '../../api/library-agents-api'
import FocusTrap from 'focus-trap-react'

interface KBFormProps {
  onSave: (data: KnowledgeBaseCreateData) => Promise<void>
  onClose: () => void
  isSaving: boolean
}

export function KBFormModal({ onSave, onClose, isSaving }: KBFormProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState<KnowledgeBaseCreateData>({
    category: KNOWLEDGE_CATEGORIES[0],
    question: '',
    answer: '',
    tags: [],
    department: null,
  })
  const [tagInput, setTagInput] = useState('')
  const [error, setError] = useState<string | null>(null)

  const inputClass = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-900/50 text-sm text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:border-lsc-rose"
  const labelClass = "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

  const addTag = () => {
    if (tagInput.trim() && !form.tags?.includes(tagInput.trim())) {
      setForm(p => ({ ...p, tags: [...(p.tags || []), tagInput.trim()] }))
      setTagInput('')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.question.trim() || !form.answer.trim()) {
      setError('Question and answer are required.')
      return
    }
    setError(null)
    await onSave(form)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}>
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      <div
        className="bg-lsc-white dark:bg-earth-900 rounded-xl shadow-lg w-full max-w-lg max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-label={t('admin.adminLibraryAgents.addKnowledgeBaseEntry')}
      >
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between">
          <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream text-lg">
            Add Knowledge Base Entry
          </h2>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-800 transition-colors" aria-label={t('aria.authModals.close')}>
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="kb-category" className={labelClass}>Category *</label>
              <select id="kb-category" value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} className={inputClass}>
                {KNOWLEDGE_CATEGORIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="kb-department" className={labelClass}>Department</label>
              <select id="kb-department" value={form.department || ''} onChange={e => setForm(p => ({ ...p, department: e.target.value || null }))} className={inputClass}>
                <option value="">All departments</option>
                {AGENT_DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="kb-question" className={labelClass}>Question *</label>
            <input id="kb-question" type="text" value={form.question} onChange={e => setForm(p => ({ ...p, question: e.target.value }))} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egWhatAreThe')} required />
          </div>

          <div>
            <label htmlFor="kb-answer" className={labelClass}>Answer *</label>
            <textarea id="kb-answer" rows={4} value={form.answer} onChange={e => setForm(p => ({ ...p, answer: e.target.value }))} className={inputClass} placeholder={t('admin.adminLibraryAgents.theAnswerToThisQuestion')} required />
          </div>

          <div>
            <label className={labelClass}>Tags</label>
            <div className="flex gap-2 mb-2">
              <input type="text" value={tagInput} onChange={e => setTagInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.addATag')} />
              <button type="button" onClick={addTag} className="px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90 transition-colors">Add</button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {form.tags?.map(t => (
                <span key={t} className="flex items-center gap-1 px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded-lg text-xs text-lsc-dark dark:text-lsc-cream">
                  {t}
                  <button type="button" onClick={() => setForm(p => ({ ...p, ...(p.tags ? { tags: p.tags.filter(x => x !== t) } : {}) }))} className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-600" aria-label={`Remove tag: ${t}`}>
                    <X className="w-3 h-3" aria-hidden="true" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-800 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={isSaving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2 transition-colors">
              {isSaving && <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
              Add Entry
            </button>
          </div>
        </form>
      </div>
      </FocusTrap>
    </div>
  )
}
