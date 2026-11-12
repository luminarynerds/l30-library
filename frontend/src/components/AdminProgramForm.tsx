/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { type ReadingProgram, type ReadingProgramCreateData } from '@/api/api'
import { useTranslation} from '@/i18n'

interface AdminProgramFormProps {
  program?: ReadingProgram
  onSubmit: (data: ReadingProgramCreateData) => Promise<void>
  onCancel: () => void
  isLoading?: boolean
}

interface FormState {
  name: string
  description: string
  program_type: string
  age_group: string
  target_age_min: string
  target_age_max: string
  start_date: string
  end_date: string
  reading_goal_type: string
  reading_goal_value: string
  is_active: boolean | string
}

export default function AdminProgramForm({
  program,
  onSubmit,
  onCancel,
  isLoading = false,
}: AdminProgramFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<FormState>({
    name: program?.name || '',
    description: program?.description || '',
    program_type: program?.program_type || 'year_round',
    age_group: program?.age_group || '',
    target_age_min: program?.target_age_min?.toString() || '',
    target_age_max: program?.target_age_max?.toString() || '',
    start_date: program ? program.start_date.slice(0, 10) : '',
    end_date: program ? program.end_date.slice(0, 10) : '',
    reading_goal_type: program?.reading_goal_type || '',
    reading_goal_value: program?.reading_goal_value?.toString() || '',
    is_active: program?.is_active !== false,
  })
  const [error, setError] = useState<string>('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, type } = e.target
    let value: boolean | string

    if (type === 'checkbox') {
      value = (e.target as HTMLInputElement).checked
    } else {
      value = e.target.value
    }

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validation
    if (!formData.name.trim()) {
      setError('Program name is required')
      return
    }

    if (!formData.start_date || !formData.end_date) {
      setError('Start and end dates are required')
      return
    }

    const startDate = new Date(formData.start_date)
    const endDate = new Date(formData.end_date)

    if (endDate <= startDate) {
      setError('End date must be after start date')
      return
    }

    const minAge = formData.target_age_min ? parseInt(formData.target_age_min, 10) : undefined
    const maxAge = formData.target_age_max ? parseInt(formData.target_age_max, 10) : undefined

    if (minAge && maxAge && minAge > maxAge) {
      setError('Minimum age cannot be greater than maximum age')
      return
    }

    if (formData.reading_goal_type && !formData.reading_goal_value) {
      setError('Reading goal value is required when goal type is set')
      return
    }

    try {
      // Convert form data to proper types
      const submitData: ReadingProgramCreateData = {
        name: formData.name,
        ...(formData.description && { description: formData.description }),
        program_type: formData.program_type as 'summer' | 'winter' | 'year_round' | 'special',
        ...(formData.age_group && { age_group: formData.age_group }),
        ...(minAge && { target_age_min: minAge }),
        ...(maxAge && { target_age_max: maxAge }),
        start_date: formData.start_date,
        end_date: formData.end_date,
        ...(formData.reading_goal_type && { reading_goal_type: formData.reading_goal_type as 'minutes' | 'books' | 'pages' }),
        ...(formData.reading_goal_value && { reading_goal_value: parseInt(formData.reading_goal_value, 10) }),
        is_active: typeof formData.is_active === 'boolean' ? formData.is_active : formData.is_active === 'true',
      }
      await onSubmit(submitData)
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : "Something didn't work as expected. Please try again.")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Program Details</h3>

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
            <div>Program Name *</div>
            <div className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              What is this reading program called?
            </div>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            maxLength={200}
            required
            className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            placeholder={t('placeholder.adminProgramForm.egSummerReadingChallenge')}
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
            <div>Description</div>
            <div className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Explain what this program is about (optional)
            </div>
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description || ''}
            onChange={handleChange}
            rows={3}
            className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            placeholder={t('placeholder.adminProgramForm.egJoinUsFor')}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="program_type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Program Type
            </label>
            <select
              id="program_type"
              name="program_type"
              value={formData.program_type || 'year_round'}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="summer">Summer Reading</option>
              <option value="winter">Winter Reading</option>
              <option value="year_round">Year-Round</option>
              <option value="special">Special Challenge</option>
            </select>
          </div>

          <div>
            <label htmlFor="age_group" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Age Group
            </label>
            <input
              type="text"
              id="age_group"
              name="age_group"
              value={formData.age_group || ''}
              onChange={handleChange}
              maxLength={50}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('placeholder.adminProgramForm.egChildrenTeensAll')}
            />
          </div>
        </div>
      </div>

      {/* Age Range */}
      <div className="space-y-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Age Range (optional)</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="target_age_min" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Minimum Age
            </label>
            <input
              type="number"
              id="target_age_min"
              name="target_age_min"
              value={formData.target_age_min || ''}
              onChange={handleChange}
              min="0"
              max="150"
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('placeholder.adminProgramForm.5')}
            />
          </div>

          <div>
            <label htmlFor="target_age_max" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Maximum Age
            </label>
            <input
              type="number"
              id="target_age_max"
              name="target_age_max"
              value={formData.target_age_max || ''}
              onChange={handleChange}
              min="0"
              max="150"
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('placeholder.adminProgramForm.12')}
            />
          </div>
        </div>
      </div>

      {/* Dates */}
      <div className="space-y-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Program Dates *</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="start_date" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Start Date <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
            </label>
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              required
              min={!program ? new Date().toISOString().split('T')[0] : undefined}
              aria-required="true"
              aria-describedby="start-date-hint"
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            <p id="start-date-hint" className="sr-only">{t('components.adminProgramForm.whenTheReadingProgramBegins')}</p>
          </div>

          <div>
            <label htmlFor="end_date" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              End Date <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
            </label>
            <input
              type="date"
              id="end_date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              required
              min={formData.start_date || new Date().toISOString().split('T')[0]}
              aria-required="true"
              aria-describedby="end-date-hint"
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            <p id="end-date-hint" className="sr-only">{t('components.adminProgramForm.whenTheReadingProgramEnds')}</p>
          </div>
        </div>
      </div>

      {/* Reading Goal */}
      <div className="space-y-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Reading Goal (optional)</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="reading_goal_type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Goal Type
            </label>
            <select
              id="reading_goal_type"
              name="reading_goal_type"
              value={formData.reading_goal_type || ''}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">No goal</option>
              <option value="minutes">Minutes</option>
              <option value="books">Books</option>
              <option value="pages">Pages</option>
            </select>
          </div>

          <div>
            <label htmlFor="reading_goal_value" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              Goal Value
            </label>
            <input
              type="number"
              id="reading_goal_value"
              name="reading_goal_value"
              value={formData.reading_goal_value || ''}
              onChange={handleChange}
              min="1"
              disabled={!formData.reading_goal_type}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
              placeholder={t('placeholder.adminProgramForm.100')}
            />
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="space-y-4">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            name="is_active"
            checked={typeof formData.is_active === 'boolean' ? formData.is_active : formData.is_active === 'true'}
            onChange={handleChange}
            className="w-5 h-5 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
          />
          <div>
            <div className="font-medium text-lsc-dark dark:text-lsc-cream">Active</div>
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.adminProgramForm.patronsCanRegisterForThis')}</div>
          </div>
        </label>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/30 rounded-xl flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-700 dark:text-status-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-status-danger-700 dark:text-status-danger-400 text-sm">{error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="flex-1 px-4 py-3 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="flex-1 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose disabled:opacity-50 text-white rounded-xl transition-colors flex items-center justify-center gap-2 font-medium"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              Saving...
            </>
          ) : program ? (
            'Update Program'
          ) : (
            'Create Program'
          )}
        </button>
      </div>
    </form>
  )
}
