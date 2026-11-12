/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Loader2 } from 'lucide-react'
import {
  inviteStaff,
  type InviteStaffData,
} from '../api/staff-api'
import { useFormModal } from '../hooks/useFormModal'
import { VALIDATORS } from '../utils/validation'
import { Modal } from './ui/Modal'
import { notifySuccess } from '../utils/toastNotifications'
import { t } from '@/i18n'

const STAFF_ROLES = ['super_admin', 'admin', 'director', 'library_admin', 'staff'] as const

interface InviteStaffModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function InviteStaffModal({
  isOpen,
  onClose,
  onSuccess,
}: InviteStaffModalProps): React.ReactElement | null {
  const form = useFormModal<InviteStaffData>({
    initialData: {
      email: '',
      first_name: '',
      last_name: '',
      role: 'staff',
      staff_role: '',
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      const emailError = VALIDATORS.email(data.email)
      if (emailError) errors.email = emailError
      if (!data.role) errors.role = 'Role is required'
      return errors
    },
    onSuccess: () => {
      form.resetForm()
      notifySuccess('Invitation sent')
      onSuccess()
      onClose()
    },
  })

  if (!isOpen) return null

  const handleFormSubmit = form.handleSubmit(async (data) => {
    const payload: InviteStaffData = {
      email: data.email,
      first_name: data.first_name,
      last_name: data.last_name,
      role: data.role,
    }
    if (data.staff_role) payload.staff_role = data.staff_role
    await inviteStaff(payload)
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Invite Staff Member"
      size="md"
    >
      <form onSubmit={handleFormSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label htmlFor="invite-staff-email" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Email <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <input
            type="email"
            id="invite-staff-email"
            name="email"
            value={form.formData.email}
            onChange={form.handleChange}
            placeholder={t('placeholder.addUserModal.userexamplecom')}
            aria-required="true"
            aria-invalid={!!form.errors.email}
            aria-describedby={form.errors.email ? 'invite-staff-email-error' : undefined}
            className={`w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
              form.errors.email
                ? 'border-status-danger-500 dark:border-status-danger-400'
                : 'border-lsc-border dark:border-earth-700'
            }`}
          />
          {form.errors.email && (
            <p id="invite-staff-email-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.email}
            </p>
          )}
        </div>

        {/* First Name */}
        <div>
          <label htmlFor="invite-staff-first-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            First Name
          </label>
          <input
            id="invite-staff-first-name"
            type="text"
            name="first_name"
            value={form.formData.first_name}
            onChange={form.handleChange}
            placeholder={t('placeholder.addUserModal.john')}
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        {/* Last Name */}
        <div>
          <label htmlFor="invite-staff-last-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Last Name
          </label>
          <input
            id="invite-staff-last-name"
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
          <label htmlFor="invite-staff-role" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Role <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <select
            id="invite-staff-role"
            name="role"
            value={form.formData.role}
            onChange={form.handleChange}
            aria-required="true"
            aria-invalid={!!form.errors.role}
            aria-describedby={form.errors.role ? 'invite-staff-role-error' : undefined}
            className={`w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
              form.errors.role
                ? 'border-status-danger-500 dark:border-status-danger-400'
                : 'border-lsc-border dark:border-earth-700'
            }`}
          >
            {STAFF_ROLES.map((role) => (
              <option key={role} value={role} className="bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream">
                {role}
              </option>
            ))}
          </select>
          {form.errors.role && (
            <p id="invite-staff-role-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.role}
            </p>
          )}
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
            disabled={form.loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {form.loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {form.loading ? 'Sending...' : 'Send Invitation'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
