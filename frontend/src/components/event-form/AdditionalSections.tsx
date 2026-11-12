/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { Dispatch, SetStateAction } from 'react'
import { useTranslation } from '@/i18n'
import type { EventFormData, ProgramPartnerOption } from './model'

type FormChangeHandler = (
  event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
) => void

interface AdditionalSectionsProps {
  formData: EventFormData
  setFormData: Dispatch<SetStateAction<EventFormData>>
  handleChange: FormChangeHandler
  availableProgramPartners: ProgramPartnerOption[]
  ageRangeError: string
}

export function AdditionalSections({
  formData,
  setFormData,
  handleChange,
  availableProgramPartners,
  ageRangeError,
}: AdditionalSectionsProps): React.ReactElement {
  const { t } = useTranslation()

  const updatePresenter = (
    index: number,
    changes: Partial<EventFormData['presenters'][number]>
  ) => {
    setFormData((current) => ({
      ...current,
      presenters: current.presenters.map((presenter, presenterIndex) =>
        presenterIndex === index ? { ...presenter, ...changes } : presenter
      ),
    }))
  }

  return (
    <>
      <details className="border border-lsc-border dark:border-earth-700 rounded-xl p-3">
        <summary className="cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('section.recurrence', 'Recurrence')}
        </summary>
        <div className="mt-3">
          <label htmlFor="recurrence_rule" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
            {t('eventForm.recurrenceLabel', 'Recurrence rule (RFC 5545)')}
          </label>
          <textarea
            id="recurrence_rule"
            name="recurrence_rule"
            rows={2}
            value={formData.recurrence_rule}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono text-sm"
            placeholder="FREQ=WEEKLY;BYDAY=TU;UNTIL=20260815T120000Z"
          />
          <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('eventForm.recurrenceHelp', 'Leave empty for a one-time event. Example: FREQ=WEEKLY;BYDAY=TU;UNTIL=20260815T120000Z.')}
          </p>
        </div>
      </details>

      <details className="border border-lsc-border dark:border-earth-700 rounded-xl p-3">
        <summary className="cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('section.presenters', 'Presenters')}
        </summary>
        <div className="mt-3 space-y-3">
          {formData.presenters.map((presenter, index) => (
            <div key={index} className="border border-lsc-border dark:border-earth-700 rounded-xl p-3 space-y-2">
              <div>
                <label htmlFor={`presenter_name_${index}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                  {t('eventForm.presenterName', 'Name')} <span className="text-status-danger-600">*</span>
                </label>
                <input
                  type="text"
                  id={`presenter_name_${index}`}
                  value={presenter.name}
                  onChange={(event) => updatePresenter(index, { name: event.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div>
                <label htmlFor={`presenter_bio_${index}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                  {t('eventForm.presenterBio', 'Bio')}
                </label>
                <textarea
                  id={`presenter_bio_${index}`}
                  rows={2}
                  value={presenter.bio}
                  onChange={(event) => updatePresenter(index, { bio: event.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div>
                <label htmlFor={`presenter_partner_${index}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
                  {t('eventForm.presenterPartnerOrg', 'Partner organization')}
                </label>
                <select
                  id={`presenter_partner_${index}`}
                  value={presenter.program_partner_id == null ? '' : String(presenter.program_partner_id)}
                  onChange={(event) => updatePresenter(index, {
                    program_partner_id: event.target.value === '' ? null : Number(event.target.value),
                  })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">{t('eventForm.presenterPartnerNone', 'None')}</option>
                  {availableProgramPartners.map((partner) => (
                    <option key={partner.id} value={partner.id}>{partner.name}</option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={() => setFormData((current) => ({
                  ...current,
                  presenters: current.presenters.filter((_, presenterIndex) => presenterIndex !== index),
                }))}
                className="text-sm text-status-danger-600 hover:underline"
              >
                {t('eventForm.presenterRemove', 'Remove presenter')}
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setFormData((current) => ({
              ...current,
              presenters: [...current.presenters, { name: '', bio: '', program_partner_id: null }],
            }))}
            className="px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl text-sm hover:bg-lsc-cream dark:hover:bg-lsc-brown"
          >
            {t('eventForm.presenterAdd', 'Add presenter')}
          </button>
        </div>
      </details>

      <details className="border border-lsc-border dark:border-earth-700 rounded-xl p-3">
        <summary className="cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('section.audience', 'Audience')}
        </summary>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label htmlFor="min_age" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
              {t('eventForm.minAge', 'Min age')}
            </label>
            <input type="number" id="min_age" name="min_age" min={0} max={120} value={formData.min_age} onChange={handleChange} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent" />
          </div>
          <div>
            <label htmlFor="max_age" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
              {t('eventForm.maxAge', 'Max age')}
            </label>
            <input type="number" id="max_age" name="max_age" min={0} max={120} value={formData.max_age} onChange={handleChange} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent" />
          </div>
          <div className="md:col-span-2 flex items-center gap-2">
            <input type="checkbox" id="caregiver_required" name="caregiver_required" checked={formData.caregiver_required} onChange={handleChange} className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose" />
            <label htmlFor="caregiver_required" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
              {t('eventForm.caregiverRequired', 'Caregiver required')}
            </label>
          </div>
          {ageRangeError && (
            <p id="age-range-error" className="md:col-span-2 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
              {ageRangeError}
            </p>
          )}
        </div>
      </details>

      <details className="border border-lsc-border dark:border-earth-700 rounded-xl p-3">
        <summary className="cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('section.photoRelease', 'Photo Release')}
        </summary>
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2">
            <input type="checkbox" id="photos_will_be_taken" name="photos_will_be_taken" checked={formData.photos_will_be_taken} onChange={handleChange} className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose" />
            <label htmlFor="photos_will_be_taken" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
              {t('eventForm.photosWillBeTaken', 'Photos may be taken at this event')}
            </label>
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('eventForm.photoReleaseHelp', 'If checked, patrons will be asked to consent to being photographed when they register.')}
          </p>
        </div>
      </details>
    </>
  )
}
