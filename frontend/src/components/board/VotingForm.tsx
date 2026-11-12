/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import type { VoteItem } from './VotingSection'
import { useTranslation} from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface VotingFormProps {
  vote?: VoteItem | null
  onSubmit: (data: unknown) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export default function VotingForm({
  vote,
  onSubmit,
  onCancel,
  loading = false,
}: VotingFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: vote?.title || '',
    description: vote?.description || '',
    vote_type: vote?.vote_type || 'simple_majority',
    opens_at: vote?.opens_at ? new Date(vote.opens_at).toISOString().slice(0, 16) : '',
    closes_at: vote?.closes_at ? new Date(vote.closes_at).toISOString().slice(0, 16) : '',
    quorum_required: vote?.quorum_required ?? 4,
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Vote title is required'
    }
    if (!formData.opens_at) {
      newErrors.opens_at = 'Opens at date/time is required'
    }
    if (!formData.closes_at) {
      newErrors.closes_at = 'Closes at date/time is required'
    }
    if (formData.opens_at && formData.closes_at && formData.opens_at >= formData.closes_at) {
      newErrors.closes_at = 'Closes at must be after opens at'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      setSubmitting(true)
      await onSubmit(formData)
    } finally {
      setSubmitting(false)
    }
  }

  const isLoading = submitting || loading

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onCancel]);

  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="vote-form-title">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-earth-200 dark:border-earth-700 p-6 flex items-center justify-between">
          <h2 id="vote-form-title" className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {vote ? "Edit Vote Item" : "Create Vote Item"}
          </h2>
          <button
            onClick={onCancel}
            aria-label="Close vote form"
            disabled={isLoading}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label htmlFor="vote-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Vote Title *
            </label>
            <input
              type="text"
              id="vote-title" name="title"
              value={formData.title}
              onChange={handleChange}
              disabled={isLoading}
              className={`w-full px-4 py-2 rounded-lg border ${
                errors.title
                  ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                  : 'border-earth-200 dark:border-earth-700'
              } bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
              placeholder={t('placeholder.board.egApprove2026Budget')}
            />
            {errors.title && (
              <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.title}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label htmlFor="vote-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Description
            </label>
            <textarea
              id="vote-description" name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={isLoading}
              rows={4}
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              placeholder={t('components.board.votingForm.provideDetailsAboutWhatBoard')}
            />
          </div>

          {/* Vote Type */}
          <div>
            <label htmlFor="vote-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Vote Type
            </label>
            <select
              id="vote-type"
              name="vote_type"
              value={formData.vote_type}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
            >
              <option value="simple_majority">Simple Majority</option>
              <option value="two_thirds">Two-Thirds Majority</option>
              <option value="unanimous">Unanimous</option>
            </select>
          </div>

          {/* Opens At */}
          <div>
            <label htmlFor="vote-opens-at" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Opens At *
            </label>
            <input
              type="datetime-local"
              id="vote-opens-at"
              name="opens_at"
              value={formData.opens_at}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
            />
          </div>

          {/* Closes At */}
          <div>
            <label htmlFor="vote-closes-at" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Closes At *
            </label>
            <input
              type="datetime-local"
              id="vote-closes-at"
              name="closes_at"
              value={formData.closes_at}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
            />
          </div>

          {/* Quorum Required */}
          <div>
            <label htmlFor="vote-quorum" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Quorum Required
            </label>
            <input
              type="number"
              id="vote-quorum"
              name="quorum_required"
              value={formData.quorum_required}
              onChange={handleChange}
              disabled={isLoading}
              min={1}
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Minimum number of members required to participate
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4 border-t border-earth-200 dark:border-earth-700">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="flex-1 px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {vote ? "Update Vote" : "Create Vote"}
            </button>
          </div>
        </form>
      </div>
    </div>
    </FocusTrap>
  )
}
