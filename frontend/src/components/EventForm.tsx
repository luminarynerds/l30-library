/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable complexity */
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { listBranches, type Branch } from '@/api/branch-api'
import { formatLanguageName } from '@/pages/events/utils/formatters'
import { AdditionalSections } from './event-form/AdditionalSections'
import {
  ACCESSIBILITY_FLAG_KEYS,
  makeDefaultFormData,
  type EventFormData,
  type EventFormProps,
  type FormErrors,
} from './event-form/model'

export type { EventFormData, Presenter, ProgramPartnerOption } from './event-form/model'

// Program-language options offered to staff: the UI's supported i18n locales.
// Stored as ISO 639-1 codes; '' = unspecified (the common case).
const PROGRAM_LANGUAGE_CODES = ['en', 'es', 'fr', 'de', 'ru', 'zh', 'ar'] as const

// Structured sensory descriptors. `i18n` is the
// shared key segment used by both this form and the patron-facing EventCard;
// `values` is the fixed lowercase vocabulary the backend schema validates.
const SENSORY_FIELDS = [
  { name: 'lighting', i18n: 'lighting', label: 'Lighting', help: 'Brightness level patrons can expect.', values: ['dim', 'moderate', 'bright'] },
  { name: 'noise_level', i18n: 'noise', label: 'Noise level', help: 'Typical sound level during the event.', values: ['quiet', 'moderate', 'lively'] },
  { name: 'crowd_size', i18n: 'crowd', label: 'Expected crowd', help: 'Roughly how busy the space will be.', values: ['small', 'medium', 'large'] },
] as const

function titleCase(token: string): string {
  return token.charAt(0).toUpperCase() + token.slice(1)
}

function isValidUrl(value: string): boolean {
  try {
    const u = new URL(value)
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}

export default function EventForm({
  onSubmit,
  onCancel,
  initialData,
  isSubmitting = false,
  availableCategories = [],
  availableAudiences = [],
  availableProgramPartners = [],
}: EventFormProps): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const canFeature = !!user && ['admin', 'super_admin', 'staff'].includes(user.role)

  const [formData, setFormData] = useState<EventFormData>(makeDefaultFormData(initialData))
  const [tagsInput, setTagsInput] = useState<string>(
    (initialData?.tags || []).join(', ')
  )

  const [errors, setErrors] = useState<FormErrors>({})
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  // Branches for branch_id select. Use existing API client; do not introduce a new one.
  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ['event-form-branches'],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 5 * 60 * 1000,
  })

  // Auto-expand Accessibility section if any flag is set on existing event
  const initialAnyA11yFlag = ACCESSIBILITY_FLAG_KEYS.some(
    (k) => !!initialData?.[k] || !!initialData?.accessibility_notes
  )
  const [a11yOpen, setA11yOpen] = useState<boolean>(initialAnyA11yFlag)
  const [seriesOpen, setSeriesOpen] = useState<boolean>(
    !!(initialData?.series_id || initialData?.series_name)
  )

  // Client-side mirror of the DB CHECK + Pydantic validator on min/max age.
  const ageRangeError =
    formData.min_age !== '' && formData.max_age !== '' &&
    Number(formData.min_age) > Number(formData.max_age)
      ? t('eventForm.ageRangeError', 'Min age must be less than or equal to max age')
      : ''

  // NOTE: form state is initialized once from initialData (see useState above).
  // We deliberately do NOT re-sync it from initialData on prop change. The
  // parent (EventManagementPage) rebuilds initialData as a fresh object literal
  // on every render, so an effect keyed on initialData would fire on every
  // parent re-render and silently revert the user's in-progress edits. To
  // re-initialize when the edit target actually changes, the parent gives this
  // component a `key` tied to the event id, which remounts it cleanly.

  const validateField = (name: string, value: string | boolean): string | undefined => {
    switch (name) {
      case 'title':
        if (typeof value === 'string' && value.trim().length < 3) {
          return t('eventForm.validation.titleMinLength', 'Title must be at least 3 characters')
        }
        break
      case 'start_time':
        // The "must be in the future" rule only applies when creating a new
        // event. When editing an existing one, staff need to fix or polish the
        // time of events that may already be underway or in the past, so the
        // absolute future check would wrongly block every edit (the relative
        // end-after-start check below still applies).
        if (!initialData && typeof value === 'string' && value) {
          const startDate = new Date(value)
          const now = new Date()
          if (startDate <= now) {
            return t('eventForm.validation.startTimeFuture', 'Start time must be in the future')
          }
        }
        break
      case 'end_time':
        if (typeof value === 'string' && value && formData.start_time) {
          const startDate = new Date(formData.start_time)
          const endDate = new Date(value)
          if (endDate <= startDate) {
            return t('eventForm.validation.endTimeAfterStart', 'End time must be after start time')
          }
        }
        break
      case 'max_attendees':
        if (typeof value === 'string' && value) {
          const num = parseInt(value, 10)
          if (isNaN(num) || num < 1) {
            return t('eventForm.validation.maxAttendeesPositive', 'Max attendees must be a positive number')
          }
        }
        break
      case 'image_url':
        if (typeof value === 'string' && value && !isValidUrl(value)) {
          return t('eventForm.validation.imageUrlInvalid', 'Image URL must be a valid http(s) URL')
        }
        break
    }
    return undefined
  }

  const validateSeries = (data: EventFormData): string | undefined => {
    const hasId = !!data.series_id.trim()
    const hasName = !!data.series_name.trim()
    if (hasId !== hasName) {
      return t(
        'eventForm.validation.seriesPair',
        'Series ID and Series Name must be provided together'
      )
    }
    return undefined
  }

  const validateVirtual = (data: EventFormData): string | undefined => {
    if (!data.is_virtual) return undefined
    const hasLink = !!data.virtual_link.trim()
    const hasNotes = !!data.accessibility_notes.trim()
    if (!hasLink && !hasNotes) {
      return t(
        'eventForm.validation.virtualLinkOrNotes',
        'Provide a virtual link or accessibility notes explaining how patrons join'
      )
    }
    if (hasLink && !isValidUrl(data.virtual_link.trim())) {
      return t('eventForm.validation.virtualLinkInvalid', 'Virtual link must be a valid http(s) URL')
    }
    return undefined
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value

    setFormData(prev => ({
      ...prev,
      [name]: newValue,
    }))

    if (touched[name]) {
      const error = validateField(name, newValue)
      setErrors(prev => ({
        ...prev,
        [name]: error,
      }))
    }
  }

  const handleBlur = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const fieldValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value

    setTouched(prev => ({
      ...prev,
      [name]: true,
    }))

    const error = validateField(name, fieldValue)
    setErrors(prev => ({
      ...prev,
      [name]: error,
    }))
  }

  const handleTagsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value
    setTagsInput(raw)
    const parsed = raw
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    setFormData((prev) => ({ ...prev, tags: parsed }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const newErrors: FormErrors = {}
    const requiredFields = ['title', 'start_time']

    requiredFields.forEach(field => {
      const error = validateField(field, formData[field as keyof EventFormData] as string)
      if (error) {
        newErrors[field as keyof FormErrors] = error
      }
    })

    if (formData.end_time) {
      const error = validateField('end_time', formData.end_time)
      if (error) {
        newErrors.end_time = error
      }
    }

    if (formData.max_attendees) {
      const error = validateField('max_attendees', formData.max_attendees)
      if (error) {
        newErrors.max_attendees = error
      }
    }

    if (formData.image_url) {
      const error = validateField('image_url', formData.image_url)
      if (error) {
        newErrors.image_url = error
      }
    }

    const seriesErr = validateSeries(formData)
    if (seriesErr) newErrors.series = seriesErr

    const virtualErr = validateVirtual(formData)
    if (virtualErr) newErrors.virtual = virtualErr

    if (!formData.title.trim()) {
      newErrors.title = t('eventForm.validation.titleRequired', 'Title is required')
    }

    if (!formData.start_time) {
      newErrors.start_time = t('eventForm.validation.startTimeRequired', 'Start time is required')
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      setTouched({
        title: true,
        start_time: true,
        end_time: !!formData.end_time,
        max_attendees: !!formData.max_attendees,
        image_url: !!formData.image_url,
        series_id: true,
        series_name: true,
        virtual_link: true,
      })
      // Open the relevant sections so the user can see the error
      if (seriesErr) setSeriesOpen(true)
      return
    }

    // Block submission if min/max age range is invalid.
    if (ageRangeError) {
      return
    }

    await onSubmit(formData)
  }

  const showImagePreview = !!formData.image_url && isValidUrl(formData.image_url)

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.title', 'Event Title')} <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
        </label>
        <input
          type="text"
          id="title"
          name="title"
          required
          value={formData.title}
          onChange={handleChange}
          onBlur={handleBlur}
          aria-invalid={touched.title && !!errors.title}
          aria-describedby={touched.title && errors.title ? 'title-error' : undefined}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder={t('components.eventForm.storyTimeForKids')}
        />
        {touched.title && errors.title && (
          <p id="title-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
            {errors.title}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.description', 'Description')}
        </label>
        <textarea
          id="description"
          name="description"
          rows={4}
          value={formData.description}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder={t('components.eventForm.eventDetailsAndWhatTo')}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="category"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.category', 'Category')}
          </label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            <option value="">{t('eventForm.field.categoryPlaceholder', 'Select a category...')}</option>
            {availableCategories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="audience"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.audience', 'Audience')}
          </label>
          <select
            id="audience"
            name="audience"
            value={formData.audience}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            <option value="">{t('eventForm.field.audiencePlaceholder', 'Select an audience...')}</option>
            {availableAudiences.map((audience) => (
              <option key={audience} value={audience}>
                {audience}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="event_language"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.eventLanguage', 'Program language')}
          </label>
          <select
            id="event_language"
            name="event_language"
            value={formData.event_language}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            <option value="">{t('eventForm.field.eventLanguagePlaceholder', 'Not specified')}</option>
            {PROGRAM_LANGUAGE_CODES.map((code) => (
              <option key={code} value={code}>
                {formatLanguageName(code)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label
          htmlFor="location"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.location', 'Location')}
        </label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder={t('placeholder.eventForm.mainReadingRoom')}
        />
      </div>

      <div>
        <label
          htmlFor="branch_id"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.branch', 'Branch')}
        </label>
        <select
          id="branch_id"
          name="branch_id"
          value={formData.branch_id}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">{t('eventForm.field.branchPlaceholder', 'Any branch / system-wide')}</option>
          {branches.map((b) => (
            <option key={b.id} value={String(b.id)}>
              {b.name}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('eventForm.help.branch', 'Which branch is hosting this event. Leave empty for system-wide.')}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="start_time"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.startTime', 'Start Time')} <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <input
            type="datetime-local"
            id="start_time"
            name="start_time"
            required
            value={formData.start_time}
            onChange={handleChange}
            onBlur={handleBlur}
            aria-invalid={touched.start_time && !!errors.start_time}
            aria-describedby={touched.start_time && errors.start_time ? 'start-time-error' : undefined}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
          {touched.start_time && errors.start_time && (
            <p id="start-time-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
              {errors.start_time}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="end_time"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.endTime', 'End Time')}
          </label>
          <input
            type="datetime-local"
            id="end_time"
            name="end_time"
            value={formData.end_time}
            onChange={handleChange}
            onBlur={handleBlur}
            aria-invalid={touched.end_time && !!errors.end_time}
            aria-describedby={touched.end_time && errors.end_time ? 'end-time-error' : undefined}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
          {touched.end_time && errors.end_time && (
            <p id="end-time-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
              {errors.end_time}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="registration_required"
          name="registration_required"
          checked={formData.registration_required}
          onChange={handleChange}
          className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
        />
        <label
          htmlFor="registration_required"
          className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80"
        >
          {t('eventForm.field.registrationRequired', 'Registration Required')}
        </label>
      </div>

      {formData.registration_required && (
        <div>
          <label
            htmlFor="max_attendees"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
          >
            {t('eventForm.field.maxAttendees', 'Max Attendees')} <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('eventForm.help.maxAttendees', '(optional, leave empty for unlimited)')}</span>
          </label>
          <input
            type="number"
            id="max_attendees"
            name="max_attendees"
            min="1"
            value={formData.max_attendees}
            onChange={handleChange}
            onBlur={handleBlur}
            aria-invalid={touched.max_attendees && !!errors.max_attendees}
            aria-describedby={touched.max_attendees && errors.max_attendees ? 'max-attendees-error' : undefined}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            placeholder={t('placeholder.eventForm.25')}
          />
          {touched.max_attendees && errors.max_attendees && (
            <p id="max-attendees-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
              {errors.max_attendees}
            </p>
          )}
        </div>
      )}

      {/* Tags */}
      <div>
        <label
          htmlFor="tags_input"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.tags', 'Tags')}
        </label>
        <input
          type="text"
          id="tags_input"
          name="tags_input"
          value={tagsInput}
          onChange={handleTagsChange}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder={t('eventForm.field.tagsPlaceholder', 'storytime, kids, fall')}
        />
        <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('eventForm.help.tags', 'Comma-separated tags for filtering and discovery.')}
        </p>
        {formData.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1" aria-label={t('eventForm.field.tagsList', 'Tags list')}>
            {formData.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block px-2 py-0.5 text-xs rounded-full bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Image URL */}
      <div>
        <label
          htmlFor="image_url"
          className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
        >
          {t('eventForm.field.imageUrl', 'Image URL')}
        </label>
        <input
          type="url"
          id="image_url"
          name="image_url"
          value={formData.image_url}
          onChange={handleChange}
          onBlur={handleBlur}
          aria-invalid={touched.image_url && !!errors.image_url}
          aria-describedby={touched.image_url && errors.image_url ? 'image-url-error' : undefined}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          placeholder="https://example.com/event.jpg"
        />
        {touched.image_url && errors.image_url && (
          <p id="image-url-error" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
            {errors.image_url}
          </p>
        )}
        {showImagePreview && (
          <div className="mt-2">
            <img
              src={formData.image_url}
              alt={t('eventForm.field.imagePreviewAlt', 'Event image preview')}
              className="max-h-32 rounded-lg border border-lsc-border dark:border-earth-700"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = 'none'
              }}
            />
          </div>
        )}
      </div>

      {/* is_featured (admin/staff only) */}
      {canFeature && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_featured"
            name="is_featured"
            checked={formData.is_featured}
            onChange={handleChange}
            className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
          />
          <label
            htmlFor="is_featured"
            className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80"
          >
            {t('eventForm.field.isFeatured', 'Feature on homepage')}
          </label>
        </div>
      )}

      {/* Virtual event toggle + link */}
      <div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_virtual"
            name="is_virtual"
            checked={formData.is_virtual}
            onChange={handleChange}
            className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
          />
          <label
            htmlFor="is_virtual"
            className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80"
          >
            {t('eventForm.field.isVirtual', 'Virtual event')}
          </label>
        </div>
        {formData.is_virtual && (
          <div className="mt-2">
            <label
              htmlFor="virtual_link"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
            >
              {t('eventForm.field.virtualLink', 'Virtual link')}
            </label>
            <input
              type="url"
              id="virtual_link"
              name="virtual_link"
              value={formData.virtual_link}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder="https://meet.example.com/abc"
            />
            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('eventForm.help.virtualLink', 'Zoom/Jitsi/etc. link patrons use to join. If not posting the link publicly, use Accessibility Notes to explain how to join.')}
            </p>
            {errors.virtual && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
                {errors.virtual}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Series (collapsible) */}
      <details
        className="border border-lsc-border dark:border-earth-700 rounded-xl"
        open={seriesOpen}
        onToggle={(e) => setSeriesOpen((e.currentTarget as HTMLDetailsElement).open)}
      >
        <summary className="px-3 py-2 cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('eventForm.section.series', 'Series (recurring event group)')}
        </summary>
        <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="series_id"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
            >
              {t('eventForm.field.seriesId', 'Series ID')}
            </label>
            <input
              type="text"
              id="series_id"
              name="series_id"
              value={formData.series_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('eventForm.field.seriesIdPlaceholder', 'summer-reading-2026')}
            />
            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('eventForm.help.seriesId', 'Identifier shared by all events in this series.')}
            </p>
          </div>
          <div>
            <label
              htmlFor="series_name"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
            >
              {t('eventForm.field.seriesName', 'Series Name')}
            </label>
            <input
              type="text"
              id="series_name"
              name="series_name"
              value={formData.series_name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('eventForm.field.seriesNamePlaceholder', 'Summer Reading 2026')}
            />
            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('eventForm.help.seriesName', 'Display name for the series.')}
            </p>
          </div>
          {errors.series && (
            <p className="md:col-span-2 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">
              {errors.series}
            </p>
          )}
        </div>
      </details>

      {/* Accessibility (collapsible) */}
      <details
        className="border border-lsc-border dark:border-earth-700 rounded-xl"
        open={a11yOpen}
        onToggle={(e) => setA11yOpen((e.currentTarget as HTMLDetailsElement).open)}
      >
        <summary className="px-3 py-2 cursor-pointer text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          {t('eventForm.section.accessibility', 'Accessibility')}
        </summary>
        <div className="p-3 space-y-3">
          <div>
            <label
              htmlFor="accessibility_notes"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
            >
              {t('eventForm.field.accessibilityNotes', 'Accessibility notes')}
            </label>
            <textarea
              id="accessibility_notes"
              name="accessibility_notes"
              rows={3}
              value={formData.accessibility_notes}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('eventForm.help.accessibilityNotes', 'What to know about accommodations, sensory environment, etc.')}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="wheelchair_accessible"
                  name="wheelchair_accessible"
                  checked={formData.wheelchair_accessible}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.wheelchairAccessible', 'Wheelchair accessible')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.wheelchairAccessible', 'Step-free entry, accessible restrooms and seating.')}
              </p>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="asl_provided"
                  name="asl_provided"
                  checked={formData.asl_provided}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.aslProvided', 'ASL interpretation provided')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.aslProvided', 'A qualified ASL interpreter will be present.')}
              </p>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="captioning_provided"
                  name="captioning_provided"
                  checked={formData.captioning_provided}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.captioningProvided', 'Captioning provided')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.captioningProvided', 'Live captions for spoken content (CART or auto-captions).')}
              </p>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="assistive_listening"
                  name="assistive_listening"
                  checked={formData.assistive_listening}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.assistiveListening', 'Assistive listening available')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.assistiveListening', 'Hearing-loop, FM, or infrared assistive listening devices available.')}
              </p>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="sensory_friendly"
                  name="sensory_friendly"
                  checked={formData.sensory_friendly}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.sensoryFriendly', 'Sensory friendly')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.sensoryFriendly', 'Reduced noise, softer lighting, movement breaks welcome.')}
              </p>
            </div>

            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="large_print_available"
                  name="large_print_available"
                  checked={formData.large_print_available}
                  onChange={handleChange}
                  className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                  {t('eventForm.field.largePrintAvailable', 'Large-print materials available')}
                </span>
              </label>
              <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('eventForm.help.largePrintAvailable', 'Handouts and signage available in large print on request.')}
              </p>
            </div>
          </div>

          {/* Structured sensory environment */}
          <fieldset className="border-t border-lsc-border dark:border-earth-700 pt-3">
            <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
              {t('eventForm.section.sensoryEnvironment', 'Sensory environment')}
            </legend>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t(
                'eventForm.help.sensoryEnvironment',
                'Optional. Helps sensory-sensitive patrons know what to expect before they arrive.',
              )}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {SENSORY_FIELDS.map((f) => (
                <div key={f.name}>
                  <label
                    htmlFor={f.name}
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                  >
                    {t(`events.sensory.${f.i18n}.label`, f.label)}
                  </label>
                  <select
                    id={f.name}
                    name={f.name}
                    value={formData[f.name]}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="">{t('eventForm.field.notSpecified', 'Not specified')}</option>
                    {f.values.map((v) => (
                      <option key={v} value={v}>
                        {t(`events.sensory.${f.i18n}.${v}`, titleCase(v))}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t(`eventForm.help.sensory.${f.i18n}`, f.help)}
                  </p>
                </div>
              ))}
            </div>
            <label className="flex items-center gap-2 mt-3">
              <input
                type="checkbox"
                id="quiet_space_available"
                name="quiet_space_available"
                checked={formData.quiet_space_available}
                onChange={handleChange}
                className="w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
              />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
                {t('eventForm.field.quietSpace', 'Quiet space available')}
              </span>
            </label>
            <p className="ml-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t(
                'eventForm.help.quietSpace',
                'A low-stimulation space patrons can step away to during the event.',
              )}
            </p>
          </fieldset>
        </div>
      </details>

      <AdditionalSections
        formData={formData}
        setFormData={setFormData}
        handleChange={handleChange}
        availableProgramPartners={availableProgramPartners}
        ageRangeError={ageRangeError}
      />

      <div className="flex gap-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t('eventForm.action.cancel', 'Cancel')}
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              {t('eventForm.action.saving', 'Saving...')}
            </>
          ) : (
            initialData ? t('eventForm.action.update', 'Update Event') : t('eventForm.action.create', 'Create Event')
          )}
        </button>
      </div>
    </form>
  )
}
