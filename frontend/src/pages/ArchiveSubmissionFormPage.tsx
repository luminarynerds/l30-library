/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import { Upload, CheckCircle2, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

export default function ArchiveSubmissionFormPage(): React.ReactElement {
  const { t } = useTranslation()
  const [step, setStep] = useState<'form' | 'success'>('form')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    submitterName: '',
    submitterEmail: '',
    submitterPhone: '',
    submitterRelationship: '',
    materialType: '',
    title: '',
    description: '',
    dateOrPeriod: '',
    location: '',
    peopleInvolved: '',
    historicalSignificance: '',
    isPublic: true,
    accessLevel: 'public',
    submitterOwnsMaterial: true,
    hasPermission: undefined as boolean | undefined,
    permissionDetails: '',
    creativeCommonsLicense: 'CC-BY-4.0',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target

    if (type === 'checkbox') {
      const target = e.target as HTMLInputElement
      setFormData(prev => ({
        ...prev,
        [name]: target.checked,
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value,
      }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      await fetchApi('/genealogy/archives/submit', {
        method: 'POST',
        body: JSON.stringify({
          submitter_name: formData.submitterName,
          submitter_email: formData.submitterEmail,
          submitter_phone: formData.submitterPhone || null,
          submitter_relationship: formData.submitterRelationship || null,
          material_type: formData.materialType,
          title: formData.title,
          description: formData.description,
          date_or_period: formData.dateOrPeriod || null,
          location: formData.location || null,
          people_involved: formData.peopleInvolved || null,
          historical_significance: formData.historicalSignificance || null,
          is_public: formData.isPublic,
          access_level: formData.accessLevel,
          submitter_owns_material: formData.submitterOwnsMaterial,
          has_permission: formData.hasPermission,
          permission_details: formData.permissionDetails || null,
          creative_commons_license: formData.creativeCommonsLicense,
        }),
      })

      setIsSubmitting(false)
      setStep('success')
      toast.success('Your contribution has been published to the community archives. Thank you!')
    } catch (error: unknown) {
      setIsSubmitting(false)
      toast.error(t('archiveSubmissionForm.failedToSubmitYourArchive'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }

  if (step === 'success') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-200 dark:border-status-success-800 rounded-xl p-8 text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle2 className="w-12 h-12 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-status-success-900 dark:text-status-success-100 mb-2">
            Thank You!
          </h2>
          <p className="text-status-success-800 dark:text-status-success-200 mb-4">
            Your contribution is live in the community archives.
          </p>
          <p className="text-status-success-700 dark:text-status-success-300 mb-6">
            It is visible on the public archive page right now. Library staff may follow up with questions or refinements as we curate the collection.
          </p>
          <button
            onClick={() => {
              setStep('form')
              setFormData({
                submitterName: '',
                submitterEmail: '',
                submitterPhone: '',
                submitterRelationship: '',
                materialType: '',
                title: '',
                description: '',
                dateOrPeriod: '',
                location: '',
                peopleInvolved: '',
                historicalSignificance: '',
                isPublic: true,
                accessLevel: 'public',
                submitterOwnsMaterial: true,
                hasPermission: undefined,
                permissionDetails: '',
                creativeCommonsLicense: 'CC-BY-4.0',
              })
            }}
            className="px-6 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-status-success-600 focus:ring-offset-2 dark:focus:ring-offset-earth-800"
          >
            Submit Another Item
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-full bg-lsc-rose/10 flex items-center justify-center">
            <Upload className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
        </div>
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Submit to Community Archives
        </h1>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          Share your historical materials with our community.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6 bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        {/* Your Information */}
        <div>
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Your Information
          </h2>
          <div className="space-y-4">
            <div>
              <label htmlFor="submitterName" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Your Name <span className="text-status-danger-600">*</span>
              </label>
              <input
                type="text"
                id="submitterName"
                name="submitterName"
                value={formData.submitterName}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div>
              <label htmlFor="submitterEmail" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Email <span className="text-status-danger-600">*</span>
              </label>
              <input
                type="email"
                id="submitterEmail"
                name="submitterEmail"
                value={formData.submitterEmail}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="submitterPhone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Phone (Optional)
                </label>
                <input
                  type="tel"
                  id="submitterPhone"
                  name="submitterPhone"
                  value={formData.submitterPhone}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div>
                <label htmlFor="submitterRelationship" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Your Relationship (e.g., "family member", "local historian")
                </label>
                <input
                  type="text"
                  id="submitterRelationship"
                  name="submitterRelationship"
                  value={formData.submitterRelationship}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Material Information */}
        <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            What Are You Submitting?
          </h2>
          <div className="space-y-4">
            <div>
              <label htmlFor="materialType" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Material Type <span className="text-status-danger-600">*</span>
              </label>
              <select
                id="materialType"
                name="materialType"
                value={formData.materialType}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">-- Select a type --</option>
                <option value="photograph">Photograph</option>
                <option value="document">Document</option>
                <option value="newspaper">Newspaper Clipping</option>
                <option value="map">Map or Blueprint</option>
                <option value="video">Video or Film</option>
                <option value="audio">Audio Recording</option>
                <option value="yearbook">Yearbook</option>
                <option value="letter">Letter or Correspondence</option>
                <option value="diary">Diary or Journal</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label htmlFor="title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Title <span className="text-status-danger-600">*</span>
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                placeholder={t('placeholder.archiveSubmissionForm.egMainStreetIn')}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Description <span className="text-status-danger-600">*</span>
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
                rows={4}
                placeholder={t('archiveSubmissionForm.tellUsAboutThisMaterial')}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
              />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="dateOrPeriod" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Date or Time Period
                </label>
                <input
                  type="text"
                  id="dateOrPeriod"
                  name="dateOrPeriod"
                  value={formData.dateOrPeriod}
                  onChange={handleChange}
                  placeholder={t('placeholder.archiveSubmissionForm.eg1950sOrJanuary')}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div>
                <label htmlFor="location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Location (if applicable)
                </label>
                <input
                  type="text"
                  id="location"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder={t('placeholder.archiveSubmissionForm.egMainStreetTown')}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
            </div>

            <div>
              <label htmlFor="peopleInvolved" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                People Involved (optional)
              </label>
              <input
                type="text"
                id="peopleInvolved"
                name="peopleInvolved"
                value={formData.peopleInvolved}
                onChange={handleChange}
                placeholder={t('archiveSubmissionForm.namesOfPeopleInPhotos')}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
          </div>
        </div>

        {/* Rights and Permissions */}
        <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Rights & Permissions
          </h2>

          <div className="space-y-4">
            <div className="p-4 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="submitterOwnsMaterial"
                  checked={formData.submitterOwnsMaterial}
                  onChange={handleChange}
                  className="mt-1"
                />
                <span className="text-sm text-earth-900 dark:text-earth-200">
                  I own this material or have permission to share it
                </span>
              </label>
            </div>

            {!formData.submitterOwnsMaterial && (
              <div className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="hasPermission"
                    checked={formData.hasPermission === true}
                    onChange={(e) => {
                      setFormData(prev => ({
                        ...prev,
                        hasPermission: e.target.checked ? true : undefined,
                      }))
                    }}
                    className="mt-1"
                  />
                  <span className="text-sm text-status-warning-900 dark:text-status-warning-100">
                    I have written permission from the owner to share this
                  </span>
                </label>

                {formData.hasPermission && (
                  <textarea
                    name="permissionDetails"
                    value={formData.permissionDetails}
                    onChange={handleChange}
                    placeholder={t('archiveSubmissionForm.describeYourPermissionEmailVerbal')}
                    rows={2}
                    className="w-full mt-3 px-4 py-2 border border-status-warning-200 dark:border-status-warning-700 rounded-lg bg-lsc-white dark:bg-status-warning-900/10 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-status-warning-500 resize-none"
                  />
                )}
              </div>
            )}

            <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-3">
                By submitting, you agree to share this material under a <strong>Creative Commons license</strong>, which means others can view and learn from it. You retain ownership.
              </p>
              <label htmlFor="creativeCommonsLicense" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                License Type
              </label>
              <select
                id="creativeCommonsLicense"
                name="creativeCommonsLicense"
                value={formData.creativeCommonsLicense}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="CC-BY-4.0">{t('archiveSubmissionForm.ccByAnyoneCanUse')}</option>
                <option value="CC-BY-SA-4.0">{t('archiveSubmissionForm.ccBySaAnyoneCan')}</option>
                <option value="CC-BY-NC-4.0">{t('archiveSubmissionForm.ccByNcNonCommercial')}</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex gap-3 border-t border-lsc-border dark:border-earth-700 pt-6">
          <button
            type="submit"
            disabled={isSubmitting}
            className={clsx(
              'flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-earth-800',
              isSubmitting
                ? 'bg-lsc-rose/50 cursor-not-allowed'
                : 'bg-lsc-rose hover:bg-lsc-rose/90 focus:ring-lsc-rose'
            )}
            aria-busy={isSubmitting}
          >
            {isSubmitting && <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
            {isSubmitting ? 'Submitting...' : 'Submit Your Material'}
          </button>
        </div>
      </form>

      {/* Info */}
      <div className="bg-lsc-cream/50 dark:bg-earth-700/30 rounded-xl p-4 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <p>
          Your contribution is published immediately. Library staff may contact you with questions and can adjust or unpublish items as we curate the collection.
        </p>
      </div>
    </div>
  )
}
