/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { updateRole, deleteRole, type Role } from '@/api/staff-api'
import { useAuth } from '../contexts/AuthContext'
import { useFormModal } from '../hooks/useFormModal'
import { notifySuccess, notifyError, TOAST_MESSAGES } from '../utils/toastNotifications'
import { AccessibleModal } from './training/AccessibleModal'
import ConfirmDialog from './ConfirmDialog'
import { t } from '@/i18n'

interface EditRoleModalProps {
  role: Role
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function EditRoleModal({
  role,
  isOpen,
  onClose,
  onSuccess,
}: EditRoleModalProps): React.ReactElement | null {
  const { token } = useAuth()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const form = useFormModal({
    initialData: {
      name: role.name,
      description: role.description || '',
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
      notifySuccess(TOAST_MESSAGES.role.updateSuccess)
      onSuccess()
      onClose()
    },
  })

  if (!isOpen) return null

  const handleFormSubmit = form.handleSubmit(async (data) => {
    if (!token) throw new Error('Not authenticated')

    await updateRole(token, role.id, {
      name: data.name,
      ...(data.description ? { description: data.description } : {}),
    })
  })

  const handleDelete = async () => {
    if (!token) return

    setDeleting(true)
    try {
      await deleteRole(token, role.id)
      notifySuccess(TOAST_MESSAGES.role.deleteSuccess)
      setShowDeleteConfirm(false)
      onSuccess()
      onClose()
    } catch (err) {
      notifyError(err, TOAST_MESSAGES.role.deleteError)
    } finally {
      setDeleting(false)
    }
  }

  const isModified =
    form.formData.name !== role.name || form.formData.description !== (role.description || '')

  return (
    <>
      <AccessibleModal isOpen={isOpen} onClose={onClose} title={`Edit ${role.name}`}>
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
                <label htmlFor="edit-role-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Role Name <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <input
                  id="edit-role-name"
                  type="text"
                  name="name"
                  value={form.formData.name}
                  onChange={form.handleChange}
                  aria-required="true"
                  aria-invalid={!!form.errors.name}
                  aria-describedby={form.errors.name ? 'edit-role-name-error' : undefined}
                  className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream ${
                    form.errors.name
                      ? 'border-status-danger-500 dark:border-status-danger-500'
                      : 'border-lsc-border dark:border-earth-700'
                  }`}
                  disabled={form.loading || deleting}
                  maxLength={100}
                />
                {form.errors.name && (
                  <p id="edit-role-name-error" role="alert" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{form.errors.name}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label htmlFor="edit-role-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Description
                </label>
                <textarea
                  id="edit-role-description"
                  name="description"
                  value={form.formData.description}
                  onChange={form.handleChange}
                  rows={4}
                  aria-invalid={!!form.errors.description}
                  aria-describedby={form.errors.description ? 'edit-role-desc-error' : 'edit-role-desc-count'}
                  className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream resize-none ${
                    form.errors.description
                      ? 'border-status-danger-500 dark:border-status-danger-500'
                      : 'border-lsc-border dark:border-earth-700'
                  }`}
                  disabled={form.loading || deleting}
                  maxLength={500}
                />
                <p id="edit-role-desc-count" className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {form.formData.description.length}/500
                </p>
                {form.errors.description && (
                  <p id="edit-role-desc-error" role="alert" className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">
                    {form.errors.description}
                  </p>
                )}
              </div>

              {/* Info Box */}
              <div className="p-3 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg flex gap-2">
                <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
                <p className="text-xs text-lsc-rose dark:text-lsc-rose-light">
                  {role.permissions.length} permission{role.permissions.length !== 1 ? 's' : ''} assigned to this role
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-3 pt-4">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={form.loading || deleting}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!isModified || form.loading || deleting}
                    className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                  >
                    {form.loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                    Save Changes
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={form.loading || deleting}
                  className="px-4 py-2 border border-status-danger-200 dark:border-status-danger-800 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  Delete Role
                </button>
              </div>
            </form>
      </AccessibleModal>

      {showDeleteConfirm && (
        <ConfirmDialog
          isOpen={true}
          title="Delete Role"
          message={`Are you sure you want to delete the "${role.name}" role? This action cannot be undone.${
            role.permissions.length > 0
              ? ` This role currently has ${role.permissions.length} permission${role.permissions.length !== 1 ? 's' : ''} assigned.`
              : ''
          }`}
          confirmText="Delete"
          confirmVariant="danger"
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </>
  )
}
