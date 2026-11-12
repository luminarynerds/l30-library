/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { CourtLocation } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CourtFormModalProps {
  onClose: () => void
  onSave: (data: Record<string, unknown>) => void
  saving: boolean
  initial?: CourtLocation
}

const INPUT_CLS = 'w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm'
const LABEL_CLS = 'block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1'

export function CourtFormModal({ onClose, onSave, saving, initial }: CourtFormModalProps) {
  const { t } = useTranslation()
  const isEdit = Boolean(initial)

  const [form, setForm] = useState({
    name: initial?.name ?? '',
    court_type: initial?.court_type ?? 'common_pleas',
    jurisdiction: initial?.jurisdiction ?? '',
    address_line1: initial?.address_line1 ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    zip_code: initial?.zip_code ?? '',
    phone: initial?.phone ?? '',
    email: initial?.email ?? '',
    website: initial?.website ?? '',
    has_self_help_center: initial?.has_self_help_center ?? false,
    e_filing_available: initial?.e_filing_available ?? false,
    wheelchair_accessible: initial?.wheelchair_accessible ?? false,
    is_active: initial?.is_active ?? true,
  })

  const titleText = isEdit
    ? t('admin.adminLegal.editCourt2')
    : t('admin.adminLegal.addCourt')

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.adminLegal.closeCourtModal')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="court-name" className={LABEL_CLS}>
                {t('admin.adminLegal.courtName')} *
              </label>
              <input
                id="court-name"
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className={INPUT_CLS}
                placeholder={t('placeholder.adminLegal.egFranklinCountyCommon')}
              />
            </div>
            <div>
              <label htmlFor="court-type" className={LABEL_CLS}>
                {t('admin.adminLegal.courtType')}
              </label>
              <select
                id="court-type"
                value={form.court_type}
                onChange={e => setForm(f => ({ ...f, court_type: e.target.value }))}
                className={INPUT_CLS}
              >
                <option value="common_pleas">Common Pleas</option>
                <option value="municipal">Municipal</option>
                <option value="probate">Probate</option>
                <option value="domestic_relations">Domestic Relations</option>
                <option value="juvenile">Juvenile</option>
                <option value="appeals">Court of Appeals</option>
                <option value="federal">Federal</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="court-jurisdiction" className={LABEL_CLS}>
              {t('admin.adminLegal.jurisdiction')} *
            </label>
            <input
              id="court-jurisdiction"
              type="text"
              value={form.jurisdiction}
              onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
              className={INPUT_CLS}
              placeholder={t('placeholder.adminLegal.egOhioFranklinCounty')}
            />
          </div>

          <div>
            <label htmlFor="court-address" className={LABEL_CLS}>
              {t('admin.adminLegal.streetAddress')} *
            </label>
            <input
              id="court-address"
              type="text"
              value={form.address_line1}
              onChange={e => setForm(f => ({ ...f, address_line1: e.target.value }))}
              className={INPUT_CLS}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-1">
              <label htmlFor="court-city" className={LABEL_CLS}>
                {t('admin.adminLegal.city')} *
              </label>
              <input
                id="court-city"
                type="text"
                value={form.city}
                onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="court-state" className={LABEL_CLS}>
                {t('admin.adminLegal.state')} *
              </label>
              <input
                id="court-state"
                type="text"
                value={form.state}
                onChange={e => setForm(f => ({ ...f, state: e.target.value }))}
                className={INPUT_CLS}
                maxLength={2}
                placeholder="OH"
              />
            </div>
            <div>
              <label htmlFor="court-zip" className={LABEL_CLS}>
                {t('admin.adminLegal.zip')} *
              </label>
              <input
                id="court-zip"
                type="text"
                value={form.zip_code}
                onChange={e => setForm(f => ({ ...f, zip_code: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="court-phone" className={LABEL_CLS}>
                {t('admin.adminLegal.phone')}
              </label>
              <input
                id="court-phone"
                type="tel"
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="court-website" className={LABEL_CLS}>
                {t('admin.adminLegal.website')}
              </label>
              <input
                id="court-website"
                type="url"
                value={form.website}
                onChange={e => setForm(f => ({ ...f, website: e.target.value }))}
                className={INPUT_CLS}
                placeholder="https://"
              />
            </div>
          </div>

          <div className="flex items-center gap-6 flex-wrap">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.has_self_help_center}
                onChange={e => setForm(f => ({ ...f, has_self_help_center: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.selfHelpCenter')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.e_filing_available}
                onChange={e => setForm(f => ({ ...f, e_filing_available: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.eFiling')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.wheelchair_accessible}
                onChange={e => setForm(f => ({ ...f, wheelchair_accessible: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.wheelchairAccessible')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.active')}</span>
            </label>
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
            onClick={() => onSave({ ...form })}
            disabled={saving || !form.name || !form.jurisdiction || !form.address_line1 || !form.city || !form.state || !form.zip_code}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? t('admin.adminLegal.saveChanges') : t('admin.adminLegal.addCourt')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
