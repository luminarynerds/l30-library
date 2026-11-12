/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Modal } from '../ui/Modal'
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

interface StorytimeSeriesData {
  id: number
  title: string
  description: string | null
  series_type: string
  primary_age_group: string
  location: string
  day_of_week: string | null
  start_time: string | null
  duration_minutes: number
  max_capacity: number | null
}

interface Props {
  onClose: () => void
  onCreated: () => void
  editing?: StorytimeSeriesData | null
}

const AGE_GROUPS = [
  { value: 'babies', label: 'Babies (0-12 mo)' },
  { value: 'toddlers', label: 'Toddlers (12-24 mo)' },
  { value: 'twos', label: 'Twos (2-3 yr)' },
  { value: 'threes', label: 'Threes (3-4 yr)' },
  { value: 'fours', label: 'Fours (4-5 yr)' },
  { value: 'fives_and_up', label: 'Fives & Up' },
  { value: 'preschool', label: 'Preschool' },
  { value: 'school_age', label: 'School Age (K-3rd)' },
  { value: 'families', label: 'Families (mixed)' },
]

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export function CreateStorytimeSeriesModal({ onClose, onCreated, editing }: Props) {
  const isEdit = !!editing
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    title: editing?.title ?? '',
    description: editing?.description ?? '',
    series_type: editing?.series_type ?? 'weekly',
    primary_age_group: editing?.primary_age_group ?? 'preschool',
    location: editing?.location ?? '',
    day_of_week: editing?.day_of_week ?? '',
    start_time: editing?.start_time ?? '',
    duration_minutes: editing?.duration_minutes?.toString() ?? '30',
    max_capacity: editing?.max_capacity?.toString() ?? '',
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const token = getAccessToken()
      const url = isEdit ? `/storytime/series/${editing!.id}` : '/storytime/series'
      await fetchApi(url, {
        method: isEdit ? 'PATCH' : 'POST',
        body: JSON.stringify({
          title: formData.title,
          description: formData.description || undefined,
          series_type: formData.series_type,
          primary_age_group: formData.primary_age_group,
          location: formData.location,
          day_of_week: formData.day_of_week || undefined,
          start_time: formData.start_time || undefined,
          duration_minutes: parseInt(formData.duration_minutes),
          max_capacity: formData.max_capacity ? parseInt(formData.max_capacity) : undefined,
        }),
        ...(token ? { token } : {}),
      })
      onCreated()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${isEdit ? 'update' : 'create'} series`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={isEdit ? "Edit Storytime Series" : "New Storytime Series"} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-sm bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="st-title" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Series Title *
          </label>
          <input
            id="st-title"
            name="title"
            type="text"
            value={formData.title}
            onChange={handleChange}
            required
            maxLength={255}
            placeholder="e.g. Toddler Tales Tuesday"
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <div>
          <label htmlFor="st-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Description
          </label>
          <textarea
            id="st-description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={2}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="st-type" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Type *
            </label>
            <select
              id="st-type"
              name="series_type"
              value={formData.series_type}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <option value="weekly">Weekly</option>
              <option value="biweekly">Biweekly</option>
              <option value="monthly">Monthly</option>
              <option value="drop_in">Drop-in</option>
              <option value="special_event">Special Event</option>
              <option value="workshop">Workshop</option>
            </select>
          </div>
          <div>
            <label htmlFor="st-age" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Age Group *
            </label>
            <select
              id="st-age"
              name="primary_age_group"
              value={formData.primary_age_group}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              {AGE_GROUPS.map(ag => (
                <option key={ag.value} value={ag.value}>{ag.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="st-location" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Location *
          </label>
          <input
            id="st-location"
            name="location"
            type="text"
            value={formData.location}
            onChange={handleChange}
            required
            placeholder="e.g. Children's Area, Community Room"
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label htmlFor="st-day" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Day
            </label>
            <select
              id="st-day"
              name="day_of_week"
              value={formData.day_of_week}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <option value="">Not set</option>
              {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="st-time" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Start Time
            </label>
            <input
              id="st-time"
              name="start_time"
              type="time"
              value={formData.start_time}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
          <div>
            <label htmlFor="st-duration" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Duration (min)
            </label>
            <input
              id="st-duration"
              name="duration_minutes"
              type="number"
              min="15"
              max="180"
              value={formData.duration_minutes}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
        </div>

        <div>
          <label htmlFor="st-capacity" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Max Capacity
          </label>
          <input
            id="st-capacity"
            name="max_capacity"
            type="number"
            min="1"
            value={formData.max_capacity}
            onChange={handleChange}
            placeholder="Unlimited"
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
          >
            {loading ? (isEdit ? 'Saving...' : 'Creating...') : (isEdit ? 'Save Changes' : 'Create Series')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
