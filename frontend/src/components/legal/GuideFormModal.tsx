/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { LegalTopic, LegalGuide } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface GuideFormModalProps {
  onClose: () => void
  onSave: (data: Record<string, unknown>) => void
  topics: LegalTopic[]
  saving: boolean
  initial?: LegalGuide
}

export function GuideFormModal({ onClose, onSave, topics, saving, initial }: GuideFormModalProps) {
  const { t } = useTranslation()
  const isEdit = Boolean(initial)
  const [form, setForm] = useState({
    title: initial?.title ?? '',
    slug: initial?.slug ?? '',
    topic_id: initial?.topic_id ? String(initial.topic_id) : '',
    summary: initial?.summary ?? '',
    content: '',
    reading_level: initial?.reading_level ?? 'middle_school',
    is_published: initial?.is_published ?? false,
    is_featured: initial?.is_featured ?? false,
  })

  const titleText = isEdit
    ? t('admin.adminLegal.editGuide2')
    : t('admin.adminLegal.createGuide')

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.adminLegal.closeGuideModal')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Title *</label>
            <input
              type="text"
              value={form.title}
              onChange={e => {
                const title = e.target.value
                setForm(f => ({
                  ...f,
                  title,
                  slug: isEdit ? f.slug : title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
                }))
              }}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('placeholder.adminLegal.egUnderstandingYourEviction')}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Slug</label>
            <input
              type="text"
              value={form.slug}
              onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 font-mono text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Topic</label>
              <select
                value={form.topic_id}
                onChange={e => setForm(f => ({ ...f, topic_id: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="">Select topic...</option>
                {topics.map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Reading Level</label>
              <select
                value={form.reading_level}
                onChange={e => setForm(f => ({ ...f, reading_level: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="elementary">Elementary (grades 3-5)</option>
                <option value="middle_school">Middle school (grades 6-8)</option>
                <option value="high_school">High school (grades 9-12)</option>
                <option value="college">College level</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Summary</label>
            <textarea
              value={form.summary}
              onChange={e => setForm(f => ({ ...f, summary: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('admin.adminLegal.briefSummaryShownInSearch')}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">Content</label>
            <textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              rows={6}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              placeholder={t('admin.adminLegal.fullGuideContentSupportsMarkdown')}
            />
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_featured}
                onChange={e => setForm(f => ({ ...f, is_featured: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">Featured</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_published}
                onChange={e => setForm(f => ({ ...f, is_published: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">Publish immediately</span>
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-lsc-border dark:border-earth-700">
          <button onClick={onClose} className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm">
            Cancel
          </button>
          <button
            onClick={() => onSave({
              ...form,
              topic_id: form.topic_id ? Number(form.topic_id) : null,
            })}
            disabled={saving || !form.title || !form.slug}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? t('admin.adminLegal.saveChanges') : t('admin.adminLegal.createGuide')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
