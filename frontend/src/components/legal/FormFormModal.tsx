/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { LegalForm, LegalTopic } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface FormFormModalProps {
  onClose: () => void
  onSave: (data: Record<string, unknown>) => void
  topics: LegalTopic[]
  saving: boolean
  initial?: LegalForm
}

const INPUT_CLS = 'w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm'
const LABEL_CLS = 'block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1'

export function FormFormModal({ onClose, onSave, topics, saving, initial }: FormFormModalProps) {
  const { t } = useTranslation()
  const isEdit = Boolean(initial)

  const [form, setForm] = useState({
    title: initial?.title ?? '',
    plain_language_title: initial?.plain_language_title ?? '',
    form_number: initial?.form_number ?? '',
    topic_id: initial?.topic_id ? String(initial.topic_id) : '',
    jurisdiction: initial?.jurisdiction ?? '',
    difficulty_level: initial?.difficulty_level ?? 'simple',
    description: initial?.description ?? '',
    when_to_use: initial?.when_to_use ?? '',
    form_url: initial?.form_url ?? '',
    instructions_url: initial?.instructions_url ?? '',
    status: initial?.status ?? 'active',
  })

  const titleText = isEdit
    ? t('admin.adminLegal.editLegalForm')
    : t('admin.adminLegal.addLegalForm')

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.adminLegal.closeFormModal')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label htmlFor="form-title" className={LABEL_CLS}>
              {t('admin.adminLegal.officialTitle')} *
            </label>
            <input
              id="form-title"
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className={INPUT_CLS}
              placeholder={t('placeholder.adminLegal.egMotionToContinue')}
            />
          </div>

          <div>
            <label htmlFor="form-plain-title" className={LABEL_CLS}>
              {t('admin.adminLegal.plainLanguageTitle')}
            </label>
            <input
              id="form-plain-title"
              type="text"
              value={form.plain_language_title}
              onChange={e => setForm(f => ({ ...f, plain_language_title: e.target.value }))}
              className={INPUT_CLS}
              placeholder={t('placeholder.adminLegal.egRequestMoreTimeIn')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="form-number" className={LABEL_CLS}>
                {t('admin.adminLegal.formNumber')}
              </label>
              <input
                id="form-number"
                type="text"
                value={form.form_number}
                onChange={e => setForm(f => ({ ...f, form_number: e.target.value }))}
                className={`${INPUT_CLS} font-mono`}
                placeholder="CV-E-110"
              />
            </div>
            <div>
              <label htmlFor="form-topic" className={LABEL_CLS}>
                {t('admin.adminLegal.topic')}
              </label>
              <select
                id="form-topic"
                value={form.topic_id}
                onChange={e => setForm(f => ({ ...f, topic_id: e.target.value }))}
                className={INPUT_CLS}
              >
                <option value="">{t('placeholder.adminLegal.selectTopic')}</option>
                {topics.map(topic => (
                  <option key={topic.id} value={topic.id}>{topic.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="form-jurisdiction" className={LABEL_CLS}>
                {t('admin.adminLegal.jurisdiction')} *
              </label>
              <input
                id="form-jurisdiction"
                type="text"
                value={form.jurisdiction}
                onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
                className={INPUT_CLS}
                placeholder={t('placeholder.adminLegal.egOhioFranklinCounty')}
              />
            </div>
            <div>
              <label htmlFor="form-difficulty" className={LABEL_CLS}>
                {t('admin.adminLegal.difficulty')}
              </label>
              <select
                id="form-difficulty"
                value={form.difficulty_level}
                onChange={e => setForm(f => ({ ...f, difficulty_level: e.target.value as 'simple' | 'moderate' | 'complex' }))}
                className={INPUT_CLS}
              >
                <option value="simple">{t('admin.adminLegal.simple')}</option>
                <option value="moderate">{t('admin.adminLegal.moderate')}</option>
                <option value="complex">{t('admin.adminLegal.complex')}</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="form-description" className={LABEL_CLS}>
              {t('admin.adminLegal.description')}
            </label>
            <textarea
              id="form-description"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2}
              className={INPUT_CLS}
            />
          </div>

          <div>
            <label htmlFor="form-when-to-use" className={LABEL_CLS}>
              {t('admin.adminLegal.whenToUse')}
            </label>
            <textarea
              id="form-when-to-use"
              value={form.when_to_use}
              onChange={e => setForm(f => ({ ...f, when_to_use: e.target.value }))}
              rows={2}
              className={INPUT_CLS}
              placeholder={t('placeholder.adminLegal.describeWhenPatronsShouldUse')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="form-url" className={LABEL_CLS}>
                {t('admin.adminLegal.formUrl')}
              </label>
              <input
                id="form-url"
                type="url"
                value={form.form_url}
                onChange={e => setForm(f => ({ ...f, form_url: e.target.value }))}
                className={INPUT_CLS}
                placeholder="https://"
              />
            </div>
            <div>
              <label htmlFor="form-instructions-url" className={LABEL_CLS}>
                {t('admin.adminLegal.instructionsUrl')}
              </label>
              <input
                id="form-instructions-url"
                type="url"
                value={form.instructions_url}
                onChange={e => setForm(f => ({ ...f, instructions_url: e.target.value }))}
                className={INPUT_CLS}
                placeholder="https://"
              />
            </div>
          </div>

          <div>
            <label htmlFor="form-status" className={LABEL_CLS}>
              {t('admin.adminLegal.status')}
            </label>
            <select
              id="form-status"
              value={form.status}
              onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              className={INPUT_CLS}
            >
              <option value="active">{t('admin.adminLegal.active')}</option>
              <option value="draft">{t('admin.adminLegal.draft')}</option>
              <option value="archived">{t('admin.adminLegal.archived')}</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 p-6 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
          >
            {t('admin.adminLegal.cancel')}
          </button>
          <button
            onClick={() => onSave({
              ...form,
              topic_id: form.topic_id ? Number(form.topic_id) : null,
            })}
            disabled={saving || !form.title || !form.jurisdiction}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? t('admin.adminLegal.saveChanges') : t('admin.adminLegal.addLegalForm')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
