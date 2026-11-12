/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import {
  createUser,
  setTeacherCard,
  listSchoolPartnersForTeacherCard,
  type CreateUserData,
  type TeacherCardSchoolOption,
} from '../api/staff-api'
import { useAuth } from '../contexts/AuthContext'
import { useFormModal } from '../hooks/useFormModal'
import { VALIDATORS } from '../utils/validation'
import { Modal } from './ui/Modal'
import { USER_ROLES } from '../constants/userManagement'
import { notifySuccess, TOAST_MESSAGES } from '../utils/toastNotifications'
import { t } from '@/i18n'

interface AddUserModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddUserModal({
  isOpen,
  onClose,
  onSuccess,
}: AddUserModalProps): React.ReactElement | null {
  const { token } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [schools, setSchools] = useState<TeacherCardSchoolOption[]>([])
  const [schoolId, setSchoolId] = useState<number | ''>('')
  const [schoolError, setSchoolError] = useState<string | null>(null)
  const [isLoadingSchools, setIsLoadingSchools] = useState(false)
  // A ref (not state) so flipping it doesn't trigger cleanup that would
  // cancel the in-flight school fetch.
  const hasRequestedSchoolsRef = React.useRef(false)

  const form = useFormModal<CreateUserData>({
    initialData: {
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      role: 'patron',
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      const emailError = VALIDATORS.email(data.email)
      if (emailError) errors.email = emailError
      const passwordError = VALIDATORS.password(data.password)
      if (passwordError) errors.password = passwordError
      if (!data.role) errors.role = 'Role is required'
      return errors
    },
    onSuccess: () => {
      form.resetForm()
      notifySuccess(TOAST_MESSAGES.user.createSuccess)
      onSuccess()
      onClose()
    },
  })

  // Lazy-load school list when the staff member selects teacher. The
  // setState calls at the top of the effect body are guarded by the
  // hasRequestedSchools sentinel so we still only fetch once per modal open;
  // the lint suppression mirrors the precedent in
  // components/shelf/ConfettiCelebration.tsx.
  useEffect(() => {
    if (!isOpen || !token) return
    if (form.formData.role !== 'teacher') return
    if (hasRequestedSchoolsRef.current) return
    hasRequestedSchoolsRef.current = true
    let cancelled = false

    setIsLoadingSchools(true)
    listSchoolPartnersForTeacherCard(token)
      .then((rows) => {
        if (!cancelled) setSchools(rows)
      })
      .catch((err: Error) => {
        if (!cancelled) setSchoolError(err.message || 'Failed to load schools')
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSchools(false)
      })
    return () => {
      cancelled = true
    }
  }, [isOpen, token, form.formData.role])

  if (!isOpen) return null

  const handleFormSubmit = form.handleSubmit(async (data) => {
    if (!token) throw new Error('Not authenticated')
    if (data.role === 'teacher') {
      if (!schoolId) {
        throw new Error('Please select a school for the teacher card')
      }
    }
    // Create the user first with the base role. The teacher-card endpoint
    // promotes role to "teacher" + links the school; this keeps create-user
    // schema unchanged on the backend.
    const baseRole = data.role === 'teacher' ? 'patron' : data.role
    const created = await createUser(token, { ...data, role: baseRole })
    if (data.role === 'teacher' && typeof schoolId === 'number') {
      await setTeacherCard(token, created.id, schoolId)
    }
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New User"
      size="md"
    >
      <form onSubmit={handleFormSubmit} className="space-y-4">
        {/* Email */}
        <div>
          <label htmlFor="add-user-email" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Email <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <input
            type="email"
            id="add-user-email"
            name="email"
            value={form.formData.email}
            onChange={form.handleChange}
            placeholder={t('placeholder.addUserModal.userexamplecom')}
            aria-required="true"
            aria-invalid={!!form.errors.email}
            aria-describedby={form.errors.email ? 'add-user-email-error' : undefined}
            className={`w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
              form.errors.email
                ? 'border-status-danger-500 dark:border-status-danger-400'
                : 'border-lsc-border dark:border-earth-700'
            }`}
          />
          {form.errors.email && (
            <p id="add-user-email-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.email}
            </p>
          )}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="add-user-password" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Password <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <div className="relative">
            <input
              id="add-user-password"
              type={showPassword ? 'text' : 'password'}
              name="password"
              value={form.formData.password}
              onChange={form.handleChange}
              placeholder={t('placeholder.addUserModal.atLeast8Characters')}
              maxLength={128}
              aria-required="true"
              aria-invalid={!!form.errors.password}
              aria-describedby={form.errors.password ? 'add-user-password-error' : undefined}
              className={`w-full px-4 py-2 pr-12 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
                form.errors.password
                  ? 'border-status-danger-500 dark:border-status-danger-400'
                  : 'border-lsc-border dark:border-earth-700'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-cream-200"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? (
                <EyeOff className="w-5 h-5" aria-hidden="true" />
              ) : (
                <Eye className="w-5 h-5" aria-hidden="true" />
              )}
            </button>
          </div>
          {form.errors.password && (
            <p id="add-user-password-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.password}
            </p>
          )}
        </div>

        {/* First Name */}
        <div>
          <label htmlFor="add-user-first-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            First Name
          </label>
          <input
            id="add-user-first-name"
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
          <label htmlFor="add-user-last-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Last Name
          </label>
          <input
            id="add-user-last-name"
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
          <label htmlFor="add-user-role" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Role <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
          </label>
          <select
            id="add-user-role"
            name="role"
            value={form.formData.role}
            onChange={form.handleChange}
            aria-required="true"
            aria-invalid={!!form.errors.role}
            aria-describedby={form.errors.role ? 'add-user-role-error' : undefined}
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
            <p id="add-user-role-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
              {form.errors.role}
            </p>
          )}
        </div>

        {/* School (teacher only) */}
        {form.formData.role === 'teacher' && (
          <div>
            <label htmlFor="add-user-school" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              School <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
            </label>
            <select
              id="add-user-school"
              name="school_id"
              value={schoolId === '' ? '' : String(schoolId)}
              onChange={(e) => setSchoolId(e.target.value ? Number(e.target.value) : '')}
              aria-required="true"
              aria-invalid={!!schoolError}
              aria-describedby={schoolError ? 'add-user-school-error' : undefined}
              disabled={isLoadingSchools}
              className={`w-full px-4 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
                schoolError
                  ? 'border-status-danger-500 dark:border-status-danger-400'
                  : 'border-lsc-border dark:border-earth-700'
              }`}
            >
              <option value="">{isLoadingSchools ? 'Loading schools...' : 'Select a school'}</option>
              {schools.map((s) => (
                <option key={s.id} value={s.id} className="bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream">
                  {s.name}
                </option>
              ))}
            </select>
            {schoolError && (
              <p id="add-user-school-error" role="alert" className="text-status-danger-600 dark:text-status-danger-400 text-sm mt-1">
                {schoolError}
              </p>
            )}
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
              Teacher cards link the user to a school partner and grant elevated lending limits.
            </p>
          </div>
        )}

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
            {form.loading ? 'Creating...' : 'Create User'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
