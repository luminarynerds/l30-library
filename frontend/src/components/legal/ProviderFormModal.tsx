/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { LegalProvider } from '@/api/legal-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ProviderFormModalProps {
  onClose: () => void
  onSave: (data: Record<string, unknown>) => void
  saving: boolean
  initial?: LegalProvider
}

const INPUT_CLS = 'w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 text-sm'
const LABEL_CLS = 'block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1'

export function ProviderFormModal({ onClose, onSave, saving, initial }: ProviderFormModalProps) {
  const { t } = useTranslation()
  const isEdit = Boolean(initial)

  const [form, setForm] = useState({
    name: initial?.name ?? '',
    slug: initial?.slug ?? '',
    provider_type: initial?.provider_type ?? 'legal_aid',
    description: initial?.description ?? '',
    phone: initial?.phone ?? '',
    email: initial?.email ?? '',
    website: initial?.website ?? '',
    address_line1: initial?.address_line1 ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    zip_code: initial?.zip_code ?? '',
    accepts_walkins: initial?.accepts_walkins ?? false,
    virtual_services: initial?.virtual_services ?? false,
    is_active: initial?.is_active ?? true,
  })

  const handleTitleChange = (name: string) => {
    setForm(f => ({
      ...f,
      name,
      slug: isEdit ? f.slug : name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    }))
  }

  const titleText = isEdit
    ? t('admin.adminLegal.editProvider')
    : t('admin.adminLegal.addProvider')

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{titleText}</h2>
          <button
            onClick={onClose}
            aria-label={t('aria.adminLegal.closeProviderModal')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="provider-name" className={LABEL_CLS}>
                {t('admin.adminLegal.providerName')} *
              </label>
              <input
                id="provider-name"
                type="text"
                value={form.name}
                onChange={e => handleTitleChange(e.target.value)}
                className={INPUT_CLS}
                placeholder={t('placeholder.adminLegal.egLegalAidSociety')}
              />
            </div>
            <div>
              <label htmlFor="provider-type" className={LABEL_CLS}>
                {t('admin.adminLegal.providerType')}
              </label>
              <select
                id="provider-type"
                value={form.provider_type}
                onChange={e => setForm(f => ({ ...f, provider_type: e.target.value }))}
                className={INPUT_CLS}
              >
                <option value="legal_aid">Legal Aid</option>
                <option value="pro_bono">Pro Bono</option>
                <option value="law_school_clinic">Law School Clinic</option>
                <option value="bar_referral">Bar Referral</option>
                <option value="self_help_center">Self-Help Center</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="provider-slug" className={LABEL_CLS}>
              {t('admin.adminLegal.slug')}
            </label>
            <input
              id="provider-slug"
              type="text"
              value={form.slug}
              onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
              className={`${INPUT_CLS} font-mono`}
            />
          </div>

          <div>
            <label htmlFor="provider-description" className={LABEL_CLS}>
              {t('admin.adminLegal.description')}
            </label>
            <textarea
              id="provider-description"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={3}
              className={INPUT_CLS}
              placeholder={t('placeholder.adminLegal.providerDescription')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="provider-phone" className={LABEL_CLS}>
                {t('admin.adminLegal.phone')}
              </label>
              <input
                id="provider-phone"
                type="tel"
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="provider-email" className={LABEL_CLS}>
                {t('admin.adminLegal.email')}
              </label>
              <input
                id="provider-email"
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
          </div>

          <div>
            <label htmlFor="provider-website" className={LABEL_CLS}>
              {t('admin.adminLegal.website')}
            </label>
            <input
              id="provider-website"
              type="url"
              value={form.website}
              onChange={e => setForm(f => ({ ...f, website: e.target.value }))}
              className={INPUT_CLS}
              placeholder="https://"
            />
          </div>

          <div>
            <label htmlFor="provider-address" className={LABEL_CLS}>
              {t('admin.adminLegal.streetAddress')}
            </label>
            <input
              id="provider-address"
              type="text"
              value={form.address_line1}
              onChange={e => setForm(f => ({ ...f, address_line1: e.target.value }))}
              className={INPUT_CLS}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-1">
              <label htmlFor="provider-city" className={LABEL_CLS}>
                {t('admin.adminLegal.city')}
              </label>
              <input
                id="provider-city"
                type="text"
                value={form.city}
                onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label htmlFor="provider-state" className={LABEL_CLS}>
                {t('admin.adminLegal.state')}
              </label>
              <input
                id="provider-state"
                type="text"
                value={form.state}
                onChange={e => setForm(f => ({ ...f, state: e.target.value }))}
                className={INPUT_CLS}
                maxLength={2}
                placeholder="OH"
              />
            </div>
            <div>
              <label htmlFor="provider-zip" className={LABEL_CLS}>
                {t('admin.adminLegal.zip')}
              </label>
              <input
                id="provider-zip"
                type="text"
                value={form.zip_code}
                onChange={e => setForm(f => ({ ...f, zip_code: e.target.value }))}
                className={INPUT_CLS}
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.accepts_walkins}
                onChange={e => setForm(f => ({ ...f, accepts_walkins: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.acceptsWalkins')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.virtual_services}
                onChange={e => setForm(f => ({ ...f, virtual_services: e.target.checked }))}
                className="w-4 h-4 accent-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.virtualServices')}</span>
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
            disabled={saving || !form.name || !form.slug}
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {isEdit ? t('admin.adminLegal.saveChanges') : t('admin.adminLegal.addProvider')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
