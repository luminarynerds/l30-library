/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Loader2 } from 'lucide-react'
import { createRole } from '@/api/staff-api'
import { useAuth } from '../contexts/AuthContext'
import { useFormModal } from '../hooks/useFormModal'
import { notifySuccess, TOAST_MESSAGES } from '../utils/toastNotifications'
import { AccessibleModal } from './training/AccessibleModal'
import { useTranslation} from '@/i18n'

interface AddRoleModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddRoleModal({
  isOpen,
  onClose,
  onSuccess,
}: AddRoleModalProps): React.ReactElement | null {
  const { t } = useTranslation()
  const { token } = useAuth()

  const form = useFormModal({
    initialData: {
      name: '',
      description: '',
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}

      if (!data.name.trim()) {
        errors.name = 'Role name is required'
      } else if (data.name.length > 100) {
        errors.name = 'Role name cannot exceed 100 characters'
      }

      if (data.description && data.description.length > 500) {
        errors.description = 'Description cannot exceed 500 characters'
      }

      return errors
    },
    onSuccess: () => {
      notifySuccess(TOAST_MESSAGES.role.createSuccess)
      onSuccess()
      onClose()
    },
  })

  if (!isOpen) return null

  const handleFormSubmit = form.handleSubmit(async (data) => {
    if (!token) throw new Error('Not authenticated')
    await createRole(token, {
      name: data.name,
      ...(data.description ? { description: data.description } : {}),
    })
  })

  const handleClose = () => {
    form.resetForm()
    onClose()
  }

  return (
    <AccessibleModal isOpen={isOpen} onClose={handleClose} title="Create New Role">
          {/* Form */}
          <form onSubmit={handleFormSubmit} className="space-y-4">
            {/* Submit Error */}
            {form.errors.submit && (
              <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg" role="alert">
                <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{form.errors.submit}</p>
              </div>
            )}

            {/* Role Name */}
            <div>
              <label htmlFor="add-role-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Role Name <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
              </label>
              <input
                id="add-role-name"
                type="text"
                name="name"
                value={form.formData.name}
                onChange={form.handleChange}
                placeholder={t('placeholder.addRoleModal.egCatalogManager')}
                aria-required="true"
                aria-invalid={!!form.errors.name}
                aria-describedby={form.errors.name ? 'add-role-name-error' : undefined}
                className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 ${
                  form.errors.name
                    ? 'border-status-danger-500 dark:border-status-danger-500'
                    : 'border-lsc-border dark:border-earth-700'
                }`}
                disabled={form.loading}
                maxLength={100}
              />
              {form.errors.name && (
                <p id="add-role-name-error" role="alert" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{form.errors.name}</p>
              )}
            </div>

            {/* Description */}
            <div>
              <label htmlFor="add-role-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Description
              </label>
              <textarea
                id="add-role-description"
                name="description"
                value={form.formData.description}
                onChange={form.handleChange}
                placeholder={t('components.addRole.describeThePurposeOfThis')}
                rows={4}
                aria-invalid={!!form.errors.description}
                aria-describedby={form.errors.description ? 'add-role-desc-error' : 'add-role-desc-count'}
                className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 resize-none ${
                  form.errors.description
                    ? 'border-status-danger-500 dark:border-status-danger-500'
                    : 'border-lsc-border dark:border-earth-700'
                }`}
                disabled={form.loading}
                maxLength={500}
              />
              <p id="add-role-desc-count" className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {form.formData.description.length}/500
              </p>
              {form.errors.description && (
                <p id="add-role-desc-error" role="alert" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{form.errors.description}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={handleClose}
                disabled={form.loading}
                className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={form.loading}
                className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
              >
                {form.loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
                Create Role
              </button>
            </div>
          </form>
    </AccessibleModal>
  )
}
