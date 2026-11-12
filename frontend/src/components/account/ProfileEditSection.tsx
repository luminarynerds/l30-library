/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Profile Edit Section for patron self-service account settings.
 *
 * Allows patrons to edit: phone, address, contact preferences.
 * Email change requires password verification and triggers re-verification.
 */
import { useState, useRef, useEffect } from 'react'
import { Save, Mail, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { fetchApi } from '../../api/fetchApi'
import { useTranslation} from '@/i18n'

export function ProfileEditSection() {
  const { t } = useTranslation()
  const { user, token, updateProfile } = useAuth()

  const [phone, setPhone] = useState(user?.phone || '')
  const [address, setAddress] = useState(user?.address || '')
  const [pronouns, setPronouns] = useState(user?.pronouns || '')
  const [isSaving, setIsSaving] = useState(false)

  // Email change state
  const [showEmailChange, setShowEmailChange] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [isChangingEmail, setIsChangingEmail] = useState(false)
  const [emailChangeError, setEmailChangeError] = useState('')
  const emailChangeErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    if (emailChangeError && emailChangeErrorRef.current) {
      emailChangeErrorRef.current.focus()
    }
  }, [emailChangeError])

  const handleSaveProfile = async () => {
    if (!token) return
    setIsSaving(true)
    try {
      await updateProfile({ phone, address, pronouns: pronouns || undefined })
      toast.success(t('toast.account.profileUpdatedSuccessfully'))
    } catch {
      toast.error(t('components.account.profileEditSection.failedToUpdateProfile'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleEmailChange = async () => {
    if (!token || !newEmail || !currentPassword) return
    setIsChangingEmail(true)
    setEmailChangeError('')
    try {
      await fetchApi('/patron/profile/change-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          new_email: newEmail,
          current_password: currentPassword,
        }),
      })
      toast.success(t('components.account.profileEditSection.verificationEmailSentToYour'))
      setShowEmailChange(false)
      setNewEmail('')
      setCurrentPassword('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('toast.account.failedToChangeEmail')
      setEmailChangeError(msg)
      toast.error(msg)
    } finally {
      setIsChangingEmail(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Profile Information */}
      <div className="p-4 bg-cream dark:bg-earth-800 rounded-xl">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          Profile Information
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          Update your account details and contact information.
        </p>
        <fieldset className="space-y-3">
          <legend className="sr-only">Profile Information</legend>
          <div>
            <label htmlFor="profile-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Name
            </label>
            <input
              id="profile-name"
              type="text"
              value={`${user?.first_name || ''} ${user?.last_name || ''}`}
              disabled
              aria-disabled="true"
              className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white/50 dark:bg-earth-800/50 text-lsc-dark/70 dark:text-lsc-cream/60"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
              To change your name, please visit the circulation desk.
            </p>
          </div>

          <div>
            <label htmlFor="profile-email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Email
            </label>
            <div className="flex items-center gap-2">
              <input
                id="profile-email"
                type="email"
                value={user?.email || ''}
                disabled
                aria-disabled="true"
                className="flex-1 px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white/50 dark:bg-earth-800/50 text-lsc-dark/70 dark:text-lsc-cream/60"
              />
              <button
                onClick={() => setShowEmailChange(!showEmailChange)}
                className="px-3 py-2 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 border border-lsc-rose/30 rounded-xl hover:bg-lsc-rose/5 transition-colors"
              >
                <Mail className="w-4 h-4 inline mr-1" />
                Change
              </button>
            </div>
          </div>

          {showEmailChange && (
            <fieldset className="p-3 bg-lsc-rose/5 border border-lsc-rose/20 rounded-xl space-y-2">
              <legend className="sr-only">Change email address</legend>
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                Enter your new email and current password to request a change.
                A verification link will be sent to your new email.
              </p>
              {emailChangeError && (
                <p
                  ref={emailChangeErrorRef}
                  id="email-change-error"
                  tabIndex={-1}
                  role="alert"
                  className="text-sm text-status-danger-600 dark:text-status-danger-400"
                >
                  {emailChangeError}
                </p>
              )}
              <div>
                <label htmlFor="new-email" className="sr-only">New email address</label>
                <input
                  id="new-email"
                  type="email"
                  placeholder={t('placeholder.account.newEmailAddress')}
                  value={newEmail}
                  onChange={(e) => { setNewEmail(e.target.value); if (emailChangeError) setEmailChangeError('') }}
                  aria-invalid={!!emailChangeError}
                  aria-describedby={emailChangeError ? 'email-change-error' : undefined}
                  className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-800"
                />
              </div>
              <div>
                <label htmlFor="current-password-for-email" className="sr-only">Current password</label>
                <input
                  id="current-password-for-email"
                  type="password"
                  placeholder={t('placeholder.account.currentPassword')}
                  value={currentPassword}
                  onChange={(e) => { setCurrentPassword(e.target.value); if (emailChangeError) setEmailChangeError('') }}
                  aria-invalid={!!emailChangeError}
                  aria-describedby={emailChangeError ? 'email-change-error' : undefined}
                  className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-800"
                />
              </div>
              <button
                onClick={handleEmailChange}
                disabled={isChangingEmail || !newEmail || !currentPassword}
                className="px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
              >
                {isChangingEmail ? (
                  <Loader2 className="w-4 h-4 inline motion-safe:animate-spin mr-1" />
                ) : null}
                Send Verification
              </button>
            </fieldset>
          )}

          <div>
            <label htmlFor="profile-phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Phone
            </label>
            <input
              id="profile-phone"
              type="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder={t('placeholder.account.5555555555')}
              maxLength={50}
              className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/50 focus:border-lsc-rose"
            />
          </div>

          <div>
            <label htmlFor="profile-address" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Address
            </label>
            <textarea
              id="profile-address"
              autoComplete="street-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder={t('components.account.profileEditSection.streetAddressCityStateZip')}
              maxLength={500}
              rows={2}
              className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/50 focus:border-lsc-rose resize-none"
            />
          </div>

          <div>
            <label htmlFor="profile-pronouns" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Pronouns <span className="text-lsc-dark/50 dark:text-lsc-cream/50 font-normal">(optional)</span>
            </label>
            <input
              id="profile-pronouns"
              type="text"
              autoComplete="off"
              value={pronouns}
              onChange={(e) => setPronouns(e.target.value)}
              placeholder="e.g. she/her, they/them"
              maxLength={50}
              className="w-full px-4 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/50 focus:border-lsc-rose"
            />
          </div>

          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-lsc-green rounded-xl hover:bg-lsc-green/90 disabled:opacity-50 transition-colors"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 inline motion-safe:animate-spin mr-1" />
            ) : (
              <Save className="w-4 h-4 inline mr-1" />
            )}
            Save Changes
          </button>
        </fieldset>
      </div>
    </div>
  )
}
