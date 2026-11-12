/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Loader2 } from 'lucide-react'
import { updateUser, type AdminUser, type UpdateUserData } from '../api/staff-api'
import { useAuth } from '../contexts/AuthContext'
import { useFormModal } from '../hooks/useFormModal'
import { Modal } from './ui/Modal'
import { USER_ROLES, USER_STATUS_OPTION_KEYS } from '../constants/userManagement'
import { notifySuccess, TOAST_MESSAGES } from '../utils/toastNotifications'
import { t } from '@/i18n'

interface EditUserModalProps {
  user: AdminUser
  onClose: () => void
  onSuccess: () => void
}

export default function EditUserModal({
  user,
  onClose,
  onSuccess,
}: EditUserModalProps): React.ReactElement | null {
  const { token } = useAuth()

  const form = useFormModal<{
    first_name: string
    last_name: string
    role: string
    is_active: boolean
  }>({
    initialData: {
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      is_active: user.is_active,
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      if (!data.role) {
        errors.role = 'Role is required'
      }
      return errors
    },
    onSuccess: () => {
      notifySuccess(TOAST_MESSAGES.user.updateSuccess)
      onSuccess()
      onClose()
    },
  })

  const handleFormSubmit = form.handleSubmit(async (data) => {
    if (!token) throw new Error('Not authenticated')

    const updateData: UpdateUserData = {
      first_name: data.first_name,
      last_name: data.last_name,
      role: data.role,
      is_active: data.is_active,
    }

    await updateUser(token, user.id, updateData)
  })

  const hasChanges =
    form.formData.first_name !== user.first_name ||
    form.formData.last_name !== user.last_name ||
    form.formData.role !== user.role ||
    form.formData.is_active !== user.is_active

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Edit User"
      size="md"
    >
      <form onSubmit={handleFormSubmit} className="space-y-4">
        {/* Email (Read-only) */}
        <div>
          <div className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Email
          </div>
          <div className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-700/50 text-earth-700 dark:text-lsc-cream">
            {user.email}
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Email cannot be changed
          </p>
        </div>

        {/* First Name */}
        <div>
          <label htmlFor="edit-first-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            First Name
          </label>
          <input
            type="text"
            id="edit-first-name"
            name="first_name"
            value={form.formData.first_name}
            onChange={form.handleChange}
            placeholder={t('placeholder.addUserModal.john')}
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        {/* Last Name */}
        <div>
          <label htmlFor="edit-last-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Last Name
          </label>
          <input
            id="edit-last-name"
            type="text"
            name="last_name"
            value={form.formData.last_name}
            onChange={form.handleChange}
            placeholder={t('placeholder.addUserModal.doe')}
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        {/* Role */}
        <div>
          <label htmlFor="edit-user-role" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Role <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <select
            id="edit-user-role"
            name="role"
            value={form.formData.role}
            onChange={form.handleChange}
            aria-required="true"
            aria-invalid={!!form.errors.role}
            aria-describedby={form.errors.role ? 'edit-user-role-error' : undefined}
            className={`w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
              form.errors.role
                ? 'border-status-danger-500 dark:border-status-danger-400'
                : 'border-lsc-border dark:border-earth-700'
            }`}
          >
            {USER_ROLES.map((role) => (
              <option key={role} value={role} className="bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream">
                {role}
              </option>
            ))}
          </select>
          {form.errors.role && (
            <p id="edit-user-role-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.role}
            </p>
          )}
        </div>

        {/* Status */}
        <div>
          <label htmlFor="edit-user-status" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Status
          </label>
          <select
            id="edit-user-status"
            name="is_active"
            value={form.formData.is_active ? 'active' : 'inactive'}
            onChange={(e) =>
              form.setFormData((prev) => ({
                ...prev,
                is_active: e.target.value === 'active',
              }))
            }
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          >
            {USER_STATUS_OPTION_KEYS.map(({ value, labelKey }) => (
              <option key={String(value)} value={value ? 'active' : 'inactive'} className="bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream">
                {t(labelKey)}
              </option>
            ))}
          </select>
        </div>

        {/* Account Status Info */}
        <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 border border-lsc-border dark:border-earth-700 rounded-lg">
          <p className="text-xs text-lsc-dark dark:text-lsc-cream space-y-1">
            <span className="block font-semibold">Account Info:</span>
            <span className="block">
              Locked: {user.is_locked ? 'Yes' : 'No'}
            </span>
            <span className="block">
              Active: {form.formData.is_active ? 'Yes' : 'No'}
            </span>
            {user.is_locked && (
              <span className="block text-status-warning-600 dark:text-status-warning-400">
                Use the lock/unlock button in the main table to change lock status
              </span>
            )}
          </p>
        </div>

        {/* Submit Error */}
        {form.errors.submit && (
          <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg" role="alert">
            <p className="text-status-danger-700 dark:text-status-danger-400 text-sm">
              {form.errors.submit}
            </p>
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
          <button
            type="button"
            onClick={onClose}
            disabled={form.loading}
            className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={form.loading || !hasChanges}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {form.loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {form.loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
