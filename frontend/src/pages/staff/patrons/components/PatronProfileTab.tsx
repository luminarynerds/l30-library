/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2, Pencil, Save, X, BookOpen, Plus, Clock, ChevronDown, ChevronUp } from "lucide-react"
import toast from "react-hot-toast"
import type { PatronDetail } from "../types"
import type { PatronFamilyResponse } from "../../../../api/staff-api/patrons"
import { useAuth } from "../../../../contexts/AuthContext"
import { fetchApi } from "../../../../api/fetchApi"
import { useTranslation } from '@/i18n'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ResetPasswordButton } from "./ResetPasswordButton"
import { PatronTagsSection } from "./PatronTagsSection"
import { PatronOnboardingStatus } from "./PatronOnboardingStatus"

import { PatronAccountSection } from "./PatronAccountSection"
import { TeacherCardSection } from "./TeacherCardSection"
interface PatronProfileTabProps {
  patron: PatronDetail
  isLoadingFamily: boolean
  familyData: (PatronFamilyResponse & { linked_accounts?: Array<{ id: number; first_name: string; last_name: string; relationship?: string }> }) | null
  onPatronUpdated?: (patron: PatronDetail) => void
}

export function PatronProfileTab({ patron, isLoadingFamily, familyData, onPatronUpdated }: PatronProfileTabProps) {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Edit form state
  const [firstName, setFirstName] = useState(patron.first_name)
  const [lastName, setLastName] = useState(patron.last_name)
  const [phone, setPhone] = useState(patron.phone || '')
  const [address, setAddress] = useState(patron.address || '')

  // Additional profile fields
  const [dateOfBirth, setDateOfBirth] = useState(patron.date_of_birth || '')
  const [preferredContact, setPreferredContact] = useState(patron.preferred_contact_method || '')
  const [languagePreference, setLanguagePreference] = useState(patron.language_preference || '')
  const [accessibilityNeeds, setAccessibilityNeeds] = useState(patron.accessibility_needs || '')
  const [emergencyContactName, setEmergencyContactName] = useState(patron.emergency_contact_name || '')
  const [emergencyContactPhone, setEmergencyContactPhone] = useState(patron.emergency_contact_phone || '')
  const [showAdditionalDetails, setShowAdditionalDetails] = useState(false)

  // Reading minutes state
  const [showAddMinutes, setShowAddMinutes] = useState(false)
  const [showLogMinutes, setShowLogMinutes] = useState(false)
  const [addMinutesValue, setAddMinutesValue] = useState('')
  const [addMinutesReason, setAddMinutesReason] = useState('')
  const [logMinutesValue, setLogMinutesValue] = useState('')
  const [logMinutesNote, setLogMinutesNote] = useState('')
  const [readingMinutes, setReadingMinutes] = useState<{
    minutes_owed: number; minutes_logged: number; minutes_remaining: number; is_clear: boolean
  } | null>(null)
  const [isLoadingMinutes, setIsLoadingMinutes] = useState(false)
  const [isSubmittingMinutes, setIsSubmittingMinutes] = useState(false)
  const [confirmAddMinutesOpen, setConfirmAddMinutesOpen] = useState(false)

  const startEditing = () => {
    setFirstName(patron.first_name)
    setLastName(patron.last_name)
    setPhone(patron.phone || '')
    setAddress(patron.address || '')
    setDateOfBirth(patron.date_of_birth || '')
    setPreferredContact(patron.preferred_contact_method || '')
    setLanguagePreference(patron.language_preference || '')
    setAccessibilityNeeds(patron.accessibility_needs || '')
    setEmergencyContactName(patron.emergency_contact_name || '')
    setEmergencyContactPhone(patron.emergency_contact_phone || '')
    setShowAdditionalDetails(false)
    setIsEditing(true)
  }

  const cancelEditing = () => {
    setIsEditing(false)
  }

  const handleSave = async () => {
    if (!token) return
    if (!firstName.trim() || !lastName.trim()) {
      toast.error(t('patronProfileTab.firstNameAndLastNameRequired'))
      return
    }
    setIsSaving(true)
    try {
      const body: Record<string, string | null> = {}
      if (firstName.trim() !== patron.first_name) body.first_name = firstName.trim()
      if (lastName.trim() !== patron.last_name) body.last_name = lastName.trim()
      if (phone !== (patron.phone || '')) body.phone = phone || null
      if (address !== (patron.address || '')) body.address = address || null
      if (dateOfBirth !== (patron.date_of_birth || '')) body.date_of_birth = dateOfBirth || null
      if (preferredContact !== (patron.preferred_contact_method || '')) body.preferred_contact_method = preferredContact || null
      if (languagePreference !== (patron.language_preference || '')) body.language_preference = languagePreference || null
      if (accessibilityNeeds !== (patron.accessibility_needs || '')) body.accessibility_needs = accessibilityNeeds || null
      if (emergencyContactName !== (patron.emergency_contact_name || '')) body.emergency_contact_name = emergencyContactName || null
      if (emergencyContactPhone !== (patron.emergency_contact_phone || '')) body.emergency_contact_phone = emergencyContactPhone || null

      if (Object.keys(body).length === 0) {
        toast(t('patronProfileTab.noChangesToSave'))
        setIsEditing(false)
        return
      }

      await fetchApi(`/staff/patrons/${patron.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      toast.success(t('patronProfileTab.profileUpdated'))
      setIsEditing(false)

      if (onPatronUpdated) {
        onPatronUpdated({
          ...patron,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: phone || null,
          address: address || null,
          date_of_birth: dateOfBirth || null,
          preferred_contact_method: (preferredContact as 'email' | 'phone' | 'mail') || null,
          language_preference: languagePreference || null,
          accessibility_needs: accessibilityNeeds || null,
          emergency_contact_name: emergencyContactName || null,
          emergency_contact_phone: emergencyContactPhone || null,
        })
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('patronProfileTab.failedToUpdateProfile'))
    } finally {
      setIsSaving(false)
    }
  }

  const loadReadingMinutes = async () => {
    if (!token) return
    setIsLoadingMinutes(true)
    try {
      const data = await fetchApi(`/staff/patrons/${patron.id}/reading-minutes`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setReadingMinutes(data)
    } catch {
      // silent
    } finally {
      setIsLoadingMinutes(false)
    }
  }

  const handleAddMinutesOwed = async () => {
    if (!token || !addMinutesValue || !addMinutesReason) return
    setIsSubmittingMinutes(true)
    try {
      const result = await fetchApi(`/staff/patrons/${patron.id}/reading-minutes/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          minutes: parseInt(addMinutesValue),
          reason: addMinutesReason,
        }),
      })
      toast.success(result.message)
      setReadingMinutes({
        minutes_owed: result.minutes_owed,
        minutes_logged: result.minutes_logged,
        minutes_remaining: result.minutes_remaining,
        is_clear: result.is_clear,
      })
      setShowAddMinutes(false)
      setAddMinutesValue('')
      setAddMinutesReason('')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('patronProfileTab.failedToAddMinutes'))
    } finally {
      setIsSubmittingMinutes(false)
    }
  }

  const handleLogMinutes = async () => {
    if (!token || !logMinutesValue) return
    setIsSubmittingMinutes(true)
    try {
      const result = await fetchApi(`/staff/patrons/${patron.id}/reading-minutes/log`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          minutes: parseInt(logMinutesValue),
          note: logMinutesNote || undefined,
        }),
      })
      toast.success(result.message)
      setReadingMinutes({
        minutes_owed: result.minutes_owed,
        minutes_logged: result.minutes_logged,
        minutes_remaining: result.minutes_remaining,
        is_clear: result.is_clear,
      })
      setShowLogMinutes(false)
      setLogMinutesValue('')
      setLogMinutesNote('')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('patronProfileTab.failedToLogMinutes'))
    } finally {
      setIsSubmittingMinutes(false)
    }
  }

  const inputClass = "w-full px-3 py-2 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/50"
  const labelClass = "block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-1"

  return (
    <div className="space-y-6">
      {/* Profile Information */}
      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('patronProfileTab.profileInformation')}
          </h3>
          {!isEditing ? (
            <div className="flex items-center gap-2">
              <ResetPasswordButton
                patronId={patron.id}
                patronName={`${patron.first_name} ${patron.last_name}`}
                patronEmail={patron.email ?? patron.email_masked ?? ""}
              />
              <button
                onClick={startEditing}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
              >
                <Pencil className="w-4 h-4" />
                {t('patronProfileTab.edit')}
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={cancelEditing}
                disabled={isSaving}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-dark/5 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
                {t('patronProfileTab.cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-lsc-green rounded-lg hover:bg-lsc-green/90 disabled:opacity-50 transition-colors"
              >
                {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
                {t('patronProfileTab.save')}
              </button>
            </div>
          )}
        </div>

        {isEditing ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="patron-profile-first-name" className={labelClass}>{t('patronProfileTab.firstName')}</label>
                <input
                  id="patron-profile-first-name"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  maxLength={100}
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="patron-profile-last-name" className={labelClass}>{t('patronProfileTab.lastName')}</label>
                <input
                  id="patron-profile-last-name"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  maxLength={100}
                  className={inputClass}
                />
              </div>
            </div>
            <div>
              <label htmlFor="patron-profile-email" className={labelClass}>{t('patronProfileTab.email')}</label>
              <input
                id="patron-profile-email"
                type="email"
                value={patron.email ?? patron.email_masked ?? ""}
                disabled
                className="w-full px-3 py-2 text-sm border border-sage/30 rounded-lg bg-earth-100 dark:bg-earth-900 text-lsc-dark/70 dark:text-lsc-cream/50 cursor-not-allowed"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">{t('patronProfileTab.emailChangesMustBeMade')}</p>
            </div>
            <div>
              <label htmlFor="patron-profile-phone" className={labelClass}>{t('patronProfileTab.phone')}</label>
              <input
                id="patron-profile-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                maxLength={50}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="patron-profile-address" className={labelClass}>{t('patronProfileTab.address')}</label>
              <textarea
                id="patron-profile-address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                maxLength={500}
                rows={2}
                className={`${inputClass} resize-none`}
              />
            </div>

            {/* Additional Details (collapsible) */}
            <div className="border-t border-sage/20 pt-3 mt-3">
              <button
                type="button"
                onClick={() => setShowAdditionalDetails(!showAdditionalDetails)}
                className="flex items-center gap-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors w-full"
              >
                {showAdditionalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                Additional Details
              </button>

              {showAdditionalDetails && (
                <div className="space-y-3 mt-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="patron-profile-dob" className={labelClass}>Date of Birth</label>
                      <input
                        id="patron-profile-dob"
                        type="date"
                        value={dateOfBirth}
                        onChange={(e) => setDateOfBirth(e.target.value)}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label htmlFor="patron-profile-preferred-contact" className={labelClass}>Preferred Contact Method</label>
                      <select
                        id="patron-profile-preferred-contact"
                        value={preferredContact}
                        onChange={(e) => setPreferredContact(e.target.value)}
                        className={inputClass}
                      >
                        <option value="">No preference on file</option>
                        <option value="email">Email</option>
                        <option value="phone">Phone</option>
                        <option value="mail">Mail</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="patron-profile-language" className={labelClass}>Language Preference</label>
                    <input
                      id="patron-profile-language"
                      type="text"
                      value={languagePreference}
                      onChange={(e) => setLanguagePreference(e.target.value)}
                      maxLength={50}
                      placeholder="e.g. English, Spanish"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label htmlFor="patron-profile-accessibility-needs" className={labelClass}>Accessibility Needs</label>
                    <textarea
                      id="patron-profile-accessibility-needs"
                      value={accessibilityNeeds}
                      onChange={(e) => setAccessibilityNeeds(e.target.value)}
                      rows={2}
                      placeholder="Large print, audiobooks, wheelchair access, etc."
                      className={`${inputClass} resize-none`}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="patron-profile-emergency-contact-name" className={labelClass}>Emergency Contact Name</label>
                      <input
                        id="patron-profile-emergency-contact-name"
                        type="text"
                        value={emergencyContactName}
                        onChange={(e) => setEmergencyContactName(e.target.value)}
                        maxLength={200}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label htmlFor="patron-profile-emergency-contact-phone" className={labelClass}>Emergency Contact Phone</label>
                      <input
                        id="patron-profile-emergency-contact-phone"
                        type="tel"
                        value={emergencyContactPhone}
                        onChange={(e) => setEmergencyContactPhone(e.target.value)}
                        maxLength={20}
                        className={inputClass}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>
              <span className="font-medium">{t('patronProfileTab.nameLabel')}</span> {patron.first_name} {patron.last_name}
            </p>
            <p>
              <span className="font-medium">{t('patronProfileTab.emailLabel')}</span> {patron.email ?? patron.email_masked ?? ""}
            </p>
            {patron.phone && (
              <p>
                <span className="font-medium">{t('patronProfileTab.phoneLabel')}</span> {patron.phone}
              </p>
            )}
            {patron.address && (
              <p>
                <span className="font-medium">{t('patronProfileTab.addressLabel')}</span> {patron.address}
              </p>
            )}
            {patron.library_card && (
              <p>
                <span className="font-medium">{t('patronProfileTab.libraryCardLabel')}</span> {patron.library_card}
              </p>
            )}
            {/* Additional details in read-only mode */}
            {(patron.date_of_birth || patron.preferred_contact_method || patron.language_preference || patron.accessibility_needs || patron.emergency_contact_name) && (
              <>
                <div className="border-t border-sage/20 pt-3 mt-3">
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Additional Details</p>
                </div>
                {patron.date_of_birth && (
                  <p>
                    <span className="font-medium">Date of Birth: </span> {patron.date_of_birth}
                  </p>
                )}
                {patron.preferred_contact_method && (
                  <p>
                    <span className="font-medium">Preferred Contact: </span> {patron.preferred_contact_method}
                  </p>
                )}
                {patron.language_preference && (
                  <p>
                    <span className="font-medium">Language: </span> {patron.language_preference}
                  </p>
                )}
                {patron.accessibility_needs && (
                  <p>
                    <span className="font-medium">Accessibility Needs: </span> {patron.accessibility_needs}
                  </p>
                )}
                {patron.emergency_contact_name && (
                  <p>
                    <span className="font-medium">Emergency Contact: </span>
                    {patron.emergency_contact_name}
                    {patron.emergency_contact_phone && ` (${patron.emergency_contact_phone})`}
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Onboarding Status */}
      <PatronOnboardingStatus
        patronId={patron.id}
        onboardingCompletedAt={patron.onboarding_completed_at}
        onboardingSkipped={patron.onboarding_skipped}
      />

      {/* Reading Minutes (Read-for-Fines) */}
      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-lsc-rose" />
            {t('patronProfileTab.readingMinutes')}
          </h3>
          {!readingMinutes && (
            <button
              onClick={loadReadingMinutes}
              disabled={isLoadingMinutes}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
            >
              {isLoadingMinutes ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : t('patronProfileTab.load')}
            </button>
          )}
        </div>

        {readingMinutes ? (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{t('patronProfileTab.owed')}</div>
                <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{readingMinutes.minutes_owed}</div>
              </div>
              <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{t('patronProfileTab.logged')}</div>
                <div className="text-lg font-bold text-status-success-600">{readingMinutes.minutes_logged}</div>
              </div>
              <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{t('patronProfileTab.remaining')}</div>
                <div className={`text-lg font-bold ${readingMinutes.is_clear ? 'text-status-success-600' : 'text-status-warning-600'}`}>
                  {readingMinutes.minutes_remaining}
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => { setShowAddMinutes(!showAddMinutes); setShowLogMinutes(false) }}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-lsc-rose border border-lsc-rose/30 rounded-lg hover:bg-lsc-rose/5"
              >
                <Plus className="w-3 h-3" /> {t('patronProfileTab.addMinutesOwed')}
              </button>
              <button
                onClick={() => { setShowLogMinutes(!showLogMinutes); setShowAddMinutes(false) }}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-lsc-green border border-lsc-green/30 rounded-lg hover:bg-lsc-green/5"
              >
                <Clock className="w-3 h-3" /> {t('patronProfileTab.logReadingTime')}
              </button>
            </div>

            {showAddMinutes && (
              <div className="p-3 bg-lsc-rose/5 border border-lsc-rose/20 rounded-lg space-y-2">
                <input
                  type="number"
                  placeholder={t('patronProfileTab.minutesPlaceholder1to500')}
                  min={1} max={500}
                  value={addMinutesValue}
                  onChange={(e) => setAddMinutesValue(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800"
                />
                <input
                  type="text"
                  placeholder={t('patronProfileTab.reasonEGOverdueFine')}
                  value={addMinutesReason}
                  onChange={(e) => setAddMinutesReason(e.target.value)}
                  maxLength={500}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800"
                />
                <button
                  onClick={() => setConfirmAddMinutesOpen(true)}
                  disabled={isSubmittingMinutes || !addMinutesValue || !addMinutesReason}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {isSubmittingMinutes ? <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" /> : null}
                  {t('patronProfileTab.add')}
                </button>
              </div>
            )}

            {showLogMinutes && (
              <div className="p-3 bg-lsc-green/5 border border-lsc-green/20 rounded-lg space-y-2">
                <input
                  type="number"
                  placeholder={t('patronProfileTab.minutesReadPlaceholder1to120')}
                  min={1} max={120}
                  value={logMinutesValue}
                  onChange={(e) => setLogMinutesValue(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800"
                />
                <input
                  type="text"
                  placeholder={t('patronProfileTab.noteOptional')}
                  value={logMinutesNote}
                  onChange={(e) => setLogMinutesNote(e.target.value)}
                  maxLength={200}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800"
                />
                <button
                  onClick={handleLogMinutes}
                  disabled={isSubmittingMinutes || !logMinutesValue}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-lsc-green rounded-lg hover:bg-lsc-green/90 disabled:opacity-50"
                >
                  {isSubmittingMinutes ? <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" /> : null}
                  {t('patronProfileTab.logReading')}
                </button>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
            {t('patronProfileTab.clickLoadToViewReadingMinutes')}
          </p>
        )}
      </div>

      {/* Patron Tags */}
      <PatronTagsSection patronId={patron.id} />

      {/* Prepaid Account */}
      <PatronAccountSection patronId={patron.id} />

      <TeacherCardSection patron={patron} onPatronUpdated={onPatronUpdated} />

      {/* Family / Linked Accounts */}
      {isLoadingFamily ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : familyData && familyData.linked_accounts && familyData.linked_accounts.length > 0 ? (
        <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">{t('patronProfileTab.linkedAccounts')}</h4>
          <div className="space-y-2">
            {familyData.linked_accounts!.map((account) => (
              <div key={account.id} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {account.first_name} {account.last_name} ({account.relationship})
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={confirmAddMinutesOpen}
        title={t('patronProfileTab.confirmAddMinutesTitle', 'Add minutes owed?')}
        body={t(
          'patronProfileTab.confirmAddMinutesBody',
          'Add {{minutes}} minutes owed for {{patron}}. New remaining balance: {{balance}} minutes.'
        )
          .replace('{{minutes}}', addMinutesValue || '0')
          .replace('{{patron}}', `${patron.first_name} ${patron.last_name}`)
          .replace(
            '{{balance}}',
            String((readingMinutes?.minutes_remaining ?? 0) + (parseInt(addMinutesValue) || 0))
          )}
        confirmLabel={t('patronProfileTab.confirmAddMinutesLabel', 'Add minutes')}
        tone="danger"
        onConfirm={() => {
          setConfirmAddMinutesOpen(false)
          handleAddMinutesOwed()
        }}
        onCancel={() => setConfirmAddMinutesOpen(false)}
      />
    </div>
  )
}
