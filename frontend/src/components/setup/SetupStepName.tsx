/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { BookOpen, User, AlertCircle } from 'lucide-react'
import PageContainer from '@/components/layout/PageContainer'

interface SetupConfig {
  library_name: string
  library_short_name: string
  contact_email: string
  phone: string
  address_line1: string
  address_line2: string
  admin_first_name: string
  admin_last_name: string
  admin_email: string
  admin_password: string
  feature_preset: 'barebones' | 'small_library' | 'full'
  feature_overrides: Record<string, boolean>
  primary_color: string
  accent_color: string
  hero_title: string
  hero_subtitle: string
  tagline: string
}

interface Props {
  config: SetupConfig
  onChange: (config: SetupConfig) => void
  onNext: () => void
  embedded?: boolean
  hideAdminAccount?: boolean
}

function deriveShortName(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase())
    .join('')
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export default function SetupStepName({ config, onChange, onNext, embedded, hideAdminAccount }: Props): React.ReactElement {
  const [shortNameManual, setShortNameManual] = useState(false)
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!shortNameManual && config.library_name) {
      onChange({ ...config, library_short_name: deriveShortName(config.library_name) })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.library_name, shortNameManual])

  const update = useCallback(
    (field: keyof SetupConfig, value: string) => {
      onChange({ ...config, [field]: value })
    },
    [config, onChange],
  )

  const handleBlur = useCallback((field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }))
  }, [])

  const validate = useCallback((): Record<string, string> => {
    const errs: Record<string, string> = {}
    if (!config.library_name.trim()) errs.library_name = 'Library name is required'
    if (!config.contact_email.trim()) errs.contact_email = 'Contact email is required'
    else if (!isValidEmail(config.contact_email)) errs.contact_email = 'Enter a valid email address'
    if (!config.admin_first_name.trim()) errs.admin_first_name = 'First name is required'
    if (!config.admin_last_name.trim()) errs.admin_last_name = 'Last name is required'
    if (!config.admin_email.trim()) errs.admin_email = 'Admin email is required'
    else if (!isValidEmail(config.admin_email)) errs.admin_email = 'Enter a valid email address'
    if (!config.admin_password) errs.admin_password = 'Password is required'
    else if (config.admin_password.length < 8) errs.admin_password = 'Password must be at least 8 characters'
    if (!confirmPassword) errs.confirmPassword = 'Please confirm your password'
    else if (config.admin_password !== confirmPassword) errs.confirmPassword = 'Passwords do not match'
    return errs
  }, [config, confirmPassword])

  const handleNext = useCallback(() => {
    const errs = validate()
    setErrors(errs)
    setTouched({
      library_name: true,
      contact_email: true,
      admin_first_name: true,
      admin_last_name: true,
      admin_email: true,
      admin_password: true,
      confirmPassword: true,
    })
    if (Object.keys(errs).length === 0) onNext()
  }, [validate, onNext])

  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors'
  const labelClass = 'block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1'
  const errorClass = 'text-sm text-status-danger-600 dark:text-status-danger-400 mt-1 flex items-center gap-1'

  const showError = (field: string) =>
    touched[field] && errors[field] ? (
      <p className={errorClass}>
        <AlertCircle aria-hidden="true" className="w-3.5 h-3.5 flex-shrink-0" />
        {errors[field]}
      </p>
    ) : null

  return (
    <PageContainer width="form" className="py-8">
      {!embedded && (
        <>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Let&apos;s set up your library
          </h1>
          <p className="text-lg text-earth-600 dark:text-earth-400 mb-8">
            Tell us about your library and create your admin account.
          </p>
        </>
      )}

      {/* Library info */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-earth-700 flex items-center justify-center">
            <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </div>
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Your Library</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="library_name" className={labelClass}>
              Library name <span className="text-status-danger-500">*</span>
            </label>
            <input
              id="library_name"
              type="text"
              className={inputClass}
              placeholder="Springfield Public Library"
              value={config.library_name}
              onChange={(e) => update('library_name', e.target.value)}
              onBlur={() => handleBlur('library_name')}
            />
            {showError('library_name')}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="library_short_name" className={labelClass}>
                Short name
              </label>
              <input
                id="library_short_name"
                type="text"
                className={inputClass}
                placeholder="SPL"
                value={config.library_short_name}
                onChange={(e) => {
                  setShortNameManual(true)
                  update('library_short_name', e.target.value)
                }}
              />
              <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">Auto-derived from name</p>
            </div>
            <div>
              <label htmlFor="contact_email" className={labelClass}>
                Contact email <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="contact_email"
                type="email"
                className={inputClass}
                placeholder="info@springfieldlibrary.org"
                value={config.contact_email}
                onChange={(e) => update('contact_email', e.target.value)}
                onBlur={() => handleBlur('contact_email')}
              />
              {showError('contact_email')}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="phone" className={labelClass}>Phone</label>
              <input
                id="phone"
                type="tel"
                className={inputClass}
                placeholder="(555) 123-4567"
                value={config.phone}
                onChange={(e) => update('phone', e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="address_line1" className={labelClass}>Address</label>
              <input
                id="address_line1"
                type="text"
                className={inputClass}
                placeholder="123 Main Street"
                value={config.address_line1}
                onChange={(e) => update('address_line1', e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Admin account (hidden on the planner, which never collects credentials) */}
      {!hideAdminAccount && (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm mb-8">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-earth-700 flex items-center justify-center">
            <User aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </div>
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Your Admin Account</h2>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="admin_first_name" className={labelClass}>
                First name <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="admin_first_name"
                type="text"
                className={inputClass}
                placeholder="Jane"
                value={config.admin_first_name}
                onChange={(e) => update('admin_first_name', e.target.value)}
                onBlur={() => handleBlur('admin_first_name')}
              />
              {showError('admin_first_name')}
            </div>
            <div>
              <label htmlFor="admin_last_name" className={labelClass}>
                Last name <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="admin_last_name"
                type="text"
                className={inputClass}
                placeholder="Smith"
                value={config.admin_last_name}
                onChange={(e) => update('admin_last_name', e.target.value)}
                onBlur={() => handleBlur('admin_last_name')}
              />
              {showError('admin_last_name')}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="admin_email" className={labelClass}>
                Email <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="admin_email"
                type="email"
                className={inputClass}
                placeholder="jane@springfieldlibrary.org"
                value={config.admin_email}
                onChange={(e) => update('admin_email', e.target.value)}
                onBlur={() => handleBlur('admin_email')}
              />
              {showError('admin_email')}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="admin_password" className={labelClass}>
                Password <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="admin_password"
                type="password"
                className={inputClass}
                placeholder="At least 8 characters"
                value={config.admin_password}
                onChange={(e) => update('admin_password', e.target.value)}
                onBlur={() => handleBlur('admin_password')}
              />
              {showError('admin_password')}
            </div>
            <div>
              <label htmlFor="confirm_password" className={labelClass}>
                Confirm password <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="confirm_password"
                type="password"
                className={inputClass}
                placeholder="Re-enter password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => handleBlur('confirmPassword')}
              />
              {showError('confirmPassword')}
            </div>
          </div>
        </div>
      </div>
      )}

      {!embedded && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleNext}
            className="px-6 py-3 rounded-xl font-medium text-white bg-lsc-rose hover:bg-lsc-rose/90 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </PageContainer>
  )
}
