/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Suspense, useState } from 'react'
import { Calendar, Clock, List, Loader2, Map as MapIcon, MapPin, Phone } from 'lucide-react'
import type { LegalClinicSummary } from '@/api/legal-api'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation, getCurrentLocale } from '@/i18n'
import EligibilityChecker from '../EligibilityChecker'
import { lazyWithRetry } from '../../../utils/lazyWithRetry'

const ClinicMapView = lazyWithRetry(() => import('../ClinicMapView'), 'legal-clinics-clinic-map-view')

interface ClinicsTabProps {
  clinics: LegalClinicSummary[]
  isLoading: boolean
}

const formatDate = (dateStr: string): string =>
  new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })

const formatTime = (timeStr: string): string => {
  const [hours = '0', minutes] = timeStr.split(':')
  const hour = parseInt(hours)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const hour12 = hour % 12 || 12
  return `${hour12}:${minutes} ${ampm}`
}


function ClinicNotifyForm(): React.ReactElement {
  const [email, setEmail] = useState('')
  const [consented, setConsented] = useState(false)
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !consented) return
    setStatus('submitting')
    try {
      await fetchApi('/legal/clinic-notify', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  const { t } = useTranslation()

  if (status === 'done') {
    return (
      <div className="max-w-sm mx-auto bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4 text-sm text-status-success-800 dark:text-status-success-200" role="status">
        {t('components.legal.clinicsTab.youReOnThe', "You're on the list. We'll send one email when a clinic is scheduled.")}
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-sm mx-auto text-left space-y-3"
      aria-label={t('aria.legalResources.notifyMeWhenClinics', 'Notify me when clinics are added')}
    >
      <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 text-center">
        {t('components.legal.clinicsTab.getNotifiedWhenA', 'Get notified when a free clinic is scheduled')}
      </p>
      <div>
        <label htmlFor="clinic-notify-email" className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          {t('components.legal.clinicsTab.emailAddress', 'Email address')}
        </label>
        <input
          id="clinic-notify-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
      </div>
      <label className="flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox"
          required
          checked={consented}
          onChange={(e) => setConsented(e.target.checked)}
          className="mt-0.5 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose flex-shrink-0"
          aria-describedby="clinic-notify-consent-desc"
        />
        <span id="clinic-notify-consent-desc" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t(
            'components.legal.clinicsTab.iAgreeToReceive',
            'I agree to receive a one-time email notification from our library when a free legal clinic is scheduled. Your email is used only for this purpose and deleted after notification is sent.',
          )}
        </span>
      </label>
      {status === 'error' && (
        <p role="alert" className="text-xs text-status-danger-600 dark:text-status-danger-400">
          {t('components.legal.clinicsTab.somethingWentWrongPlease', 'Something went wrong. Please try again or call the library directly.')}
        </p>
      )}
      <button
        type="submit"
        disabled={!email || !consented || status === 'submitting'}
        className="w-full py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
      >
        {status === 'submitting'
          ? t('components.legal.clinicsTab.submitting', 'Submitting...')
          : t('components.legal.clinicsTab.notifyMe', 'Notify me')}
      </button>
    </form>
  )
}

export default function ClinicsTab({ clinics, isLoading }: ClinicsTabProps): React.ReactElement {
  const { t } = useTranslation()
  const [view, setView] = useState<'list' | 'map'>('list')
  const hasGeoData = clinics.some((c) => c.latitude)

  return (
    <div className="space-y-6">
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setView('list')}
          className={`flex items-center gap-1 px-3 min-h-[44px] rounded-lg text-sm font-medium transition-colors ${
            view === 'list'
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80'
          }`}
          aria-pressed={view === 'list'}
        >
          <List aria-hidden="true" className="w-4 h-4" /> {t('components.legal.clinicsTab.list', 'List')}
        </button>
        {hasGeoData && (
        <button
          onClick={() => setView('map')}
          className={`flex items-center gap-1 px-3 min-h-[44px] rounded-lg text-sm font-medium transition-colors ${
            view === 'map'
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80'
          }`}
          aria-pressed={view === 'map'}
        >
          <MapIcon aria-hidden="true" className="w-4 h-4" /> {t('components.legal.clinicsTab.map', 'Map')}
        </button>
        )}
      </div>
      {view === 'map' && (
        <Suspense fallback={<div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>}>
          <ClinicMapView clinics={clinics} />
        </Suspense>
      )}
      {view === 'list' && (
        <>
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : clinics.length > 0 ? (
        clinics.map((clinic) => (
          <div
            key={clinic.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
          >
            <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
              <div className="flex-1">
                <div className="flex items-start gap-3 mb-2">
                  <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-earth-50">{clinic.title}</h3>
                  {clinic.is_virtual && (
                    <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded text-xs">
                      {t('components.legal.clinicsTab.virtual', 'Virtual')}
                    </span>
                  )}
                </div>
                <div className="grid sm:grid-cols-2 gap-3 text-sm">
                  <p className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Calendar aria-hidden="true" className="w-4 h-4" />
                    {formatDate(clinic.date)}
                  </p>
                  <p className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Clock aria-hidden="true" className="w-4 h-4" />
                    {formatTime(clinic.start_time)} - {formatTime(clinic.end_time)}
                  </p>
                  {clinic.location_name && (
                    <p className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <MapPin aria-hidden="true" className="w-4 h-4" />
                      {clinic.location_name}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    clinic.spots_available > 0
                      ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
                      : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'
                  }`}
                >
                  {clinic.spots_available > 0
                    ? t('components.legal.clinicsTab.spotsAvailable', { count: clinic.spots_available })
                    : t('components.legal.clinicsTab.full', 'Full')}
                </span>
                {clinic.topic_name && (
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-rose dark:text-lsc-rose-light rounded-full text-xs font-medium">
                    {clinic.topic_name}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center py-10">
          <Calendar aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('components.legal.clinicsTab.noUpcomingClinics', 'No upcoming clinics')}</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            {t('components.legal.clinicsTab.checkBackSoonFor', 'Check back soon for scheduled legal clinics.')}
          </p>
          <ClinicNotifyForm />
        </div>
      )}
        </>
      )}


      <EligibilityChecker />
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
        <h3 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-200 mb-2">
          {t('legalResources.needImmediateLegalHelp')}
        </h3>
        <p className="text-status-danger-700 dark:text-status-danger-300 text-sm mb-4">
          {t('components.legal.clinicsTab.ifYoureFacingAn', "If you're facing an emergency legal situation, contact these resources:")}
        </p>
        <div className="flex flex-wrap gap-4">
          <a
            href="https://www.lsc.gov/about-lsc/what-legal-aid/get-legal-help"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t('aria.legalResources.findLegalAidVia', 'Find Legal Aid Near You via LSC.gov (opens in a new tab)')}
            className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Phone aria-hidden="true" className="w-4 h-4" />
            {t('components.legal.clinicsTab.findLegalAidNear', 'Find Legal Aid Near You (LSC)')}
          </a>
          <a
            href="tel:211"
            aria-label={t('aria.legalResources.call211ForLocal', 'Call 211 for local crisis and referral help')}
            className="inline-flex items-center gap-2 min-h-[44px] px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Phone aria-hidden="true" className="w-4 h-4" />
            {t('components.legal.clinicsTab.dial211ForLocal', 'Dial 211 for local crisis and referral help')}
          </a>
        </div>
      </div>
    </div>
  )
}
