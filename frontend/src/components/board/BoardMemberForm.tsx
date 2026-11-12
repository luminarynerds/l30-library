/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import type { BoardMember } from './BoardMembersSection'
import { t } from '@/i18n'

interface BoardMemberFormProps {
  member?: BoardMember | null
  onSubmit: (data: unknown) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

const ROLES: Array<{ value: string; label: string }> = [
  { value: 'Chair', label: 'Chair' },
  { value: 'Vice Chair', label: 'Vice Chair' },
  { value: 'Secretary', label: 'Secretary' },
  { value: 'Treasurer', label: 'Treasurer' },
  { value: 'Member', label: 'Member' },
]

export default function BoardMemberForm({
  member,
  onSubmit,
  onCancel,
  loading = false,
}: BoardMemberFormProps): React.ReactElement {
  const [formData, setFormData] = useState({
    full_name: member?.full_name || '',
    email: member?.email || '',
    phone: member?.phone || '',
    position: member?.position || 'Member',
    
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)

  // Handle Escape key
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !loading && !submitting) {
      onCancel()
    }
  }, [loading, submitting, onCancel])

  // Focus first input when modal opens
  useEffect(() => {
    firstInputRef.current?.focus()
  }, [])

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.full_name.trim()) {
      newErrors.full_name = 'Full name is required'
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }
    if (formData.phone && !/^[\d\s\-()+]+$/.test(formData.phone)) {
      newErrors.phone = 'Please enter a valid phone number'
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
  const dialogTitleId = 'board-member-form-title'

  return (
    <FocusTrap
      focusTrapOptions={{
        initialFocus: () => firstInputRef.current,
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => closeButtonRef.current || document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        role="presentation"
        onKeyDown={handleKeyDown}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={dialogTitleId}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
            <h2
              id={dialogTitleId}
              className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {member ? 'Edit Board Member' : 'Add Board Member'}
            </h2>
            <button
              ref={closeButtonRef}
              onClick={onCancel}
              disabled={isLoading}
              className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.board.closeForm')}
            >
              <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="member-full-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Full Name <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <input
                  ref={firstInputRef}
                  type="text"
                  id="member-full-name"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  disabled={isLoading}
                  aria-required="true"
                  aria-invalid={!!errors.full_name}
                  aria-describedby={errors.full_name ? 'full-name-error' : undefined}
                  className={`w-full px-4 py-2 rounded-lg border ${
                    errors.full_name
                      ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                      : 'border-lsc-border dark:border-earth-700'
                  } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
                  placeholder={t('placeholder.addUserModal.john')}
                />
                {errors.full_name && (
                  <p id="full-name-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.full_name}</p>
                )}
              </div>


            </div>

            {/* Email and Phone */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="member-email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Email <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <input
                  type="email"
                  id="member-email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={isLoading}
                  aria-required="true"
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  className={`w-full px-4 py-2 rounded-lg border ${
                    errors.email
                      ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                      : 'border-lsc-border dark:border-earth-700'
                  } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
                  placeholder={t('placeholder.registrationModal.johnexamplecom')}
                />
                {errors.email && (
                  <p id="email-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.email}</p>
                )}
              </div>

              <div>
                <label htmlFor="member-phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Phone
                </label>
                <input
                  type="tel"
                  id="member-phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  disabled={isLoading}
                  aria-invalid={!!errors.phone}
                  aria-describedby={errors.phone ? 'phone-error' : undefined}
                  className={`w-full px-4 py-2 rounded-lg border ${
                    errors.phone
                      ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                      : 'border-lsc-border dark:border-earth-700'
                  } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
                />
                {errors.phone && (
                  <p id="phone-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.phone}</p>
                )}
              </div>
            </div>

            {/* Role and Position */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="board-member-role" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Role <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <select
                  id="board-member-role"
                  name="position"
                  value={formData.position}
                  onChange={handleChange}
                  disabled={isLoading}
                  aria-required="true"
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                >
                  {ROLES.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>


            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                aria-busy={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
                {member ? 'Update Member' : 'Add Member'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </FocusTrap>
  )
}
