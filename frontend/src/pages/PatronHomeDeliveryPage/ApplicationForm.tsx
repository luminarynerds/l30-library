/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import {
  Loader2,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  createHomeDeliveryApplication,
  type HomeDeliveryApplication,
  type DeliveryFrequency,
  type HomeDeliveryApplicationStatus,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { FREQUENCY_OPTIONS, DAY_OPTIONS, statusBadge, formatStatus, formatDate } from "./types"

export function ApplyTab({
  applications,
  onApplicationCreated,
  isEnrolled,
  onGoToEnrollment,
}: {
  applications: HomeDeliveryApplication[]
  onApplicationCreated: (app: HomeDeliveryApplication) => void
  isEnrolled: boolean
  onGoToEnrollment: () => void
}) {
  const { t } = useTranslation()
  const latestApp = applications.length > 0 ? applications[0] : null
  const canApply = !latestApp || latestApp.status === "denied" || latestApp.status === "withdrawn"

  if (isEnrolled) {
    return (
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6 text-center">
        <CheckCircle2 className="w-12 h-12 text-status-success-600 dark:text-status-success-400 mx-auto mb-3" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">You are enrolled!</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Your home delivery service is active. Manage your enrollment and track deliveries from the tabs above.
        </p>
        <button
          onClick={onGoToEnrollment}
          className="bg-sage text-white px-6 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors min-h-[44px]"
          aria-label={t("patronHomeDelivery.goToEnrollmentDetails")}
        >
          View Enrollment
        </button>
      </div>
    )
  }

  if (latestApp && !canApply) {
    return <ApplicationStatus application={latestApp} onGoToEnrollment={onGoToEnrollment} />
  }

  return (
    <div className="space-y-6">
      {latestApp?.status === "denied" && (
        <div className="rounded-xl border-2 border-status-danger-200 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 p-4">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-status-danger-800 dark:text-status-danger-300">Previous application denied</p>
              {latestApp.denial_reason && (
                <p className="text-sm text-status-danger-700 dark:text-status-danger-400 mt-1">Reason: {latestApp.denial_reason}</p>
              )}
              <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{t("patronHomeDelivery.youMayReapplyBelow")}</p>
            </div>
          </div>
        </div>
      )}
      <ApplicationForm onSubmitted={onApplicationCreated} />
    </div>
  )
}

function ApplicationStatus({
  application,
  onGoToEnrollment,
}: {
  application: HomeDeliveryApplication
  onGoToEnrollment: () => void
}) {
  const { t } = useTranslation()
  const s = application.status as HomeDeliveryApplicationStatus
  return (
    <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Application Status</h2>
        <span className={statusBadge(s)}>{formatStatus(s)}</span>
      </div>
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Submitted</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{formatDate(application.submitted_at)}</dd>
        </div>
        <div>
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Delivery Address</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{application.delivery_address}</dd>
        </div>
        <div>
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Preferred Frequency</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{formatStatus(application.preferred_frequency)}</dd>
        </div>
        <div>
          <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Reason</dt>
          <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{application.reason}</dd>
        </div>
      </dl>

      {s === "pending" || s === "under_review" ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-status-warning-700 dark:text-status-warning-300">
          <Clock className="w-4 h-4" />
          <span>{t("patronHomeDelivery.yourApplicationIsBeingReviewed")}</span>
        </div>
      ) : null}

      {s === "approved" && (
        <div className="mt-4">
          <p className="text-status-success-700 dark:text-status-success-400 text-sm mb-3">
            Your application has been approved. You should now be enrolled in the home delivery program.
          </p>
          <button
            onClick={onGoToEnrollment}
            className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors min-h-[44px]"
            aria-label={t('aria.applicationForm.viewYourEnrollment')}
          >
            View Enrollment
          </button>
        </div>
      )}

      {s === "waitlisted" && (
        <div className="mt-4 flex items-center gap-2 text-sm text-lsc-rose dark:text-lsc-rose-light">
          <AlertCircle className="w-4 h-4" />
          <span>{t("patronHomeDelivery.youAreOnTheWaitlist")}</span>
        </div>
      )}
    </div>
  )
}

function ApplicationForm({ onSubmitted }: { onSubmitted: (app: HomeDeliveryApplication) => void }) {
  const { t } = useTranslation()
  const [reason, setReason] = useState("")
  const [address, setAddress] = useState("")
  const [phone, setPhone] = useState("")
  const [frequency, setFrequency] = useState<DeliveryFrequency>("biweekly")
  const [preferredDay, setPreferredDay] = useState("")
  const [timeStart, setTimeStart] = useState("")
  const [timeEnd, setTimeEnd] = useState("")
  const [medicalDoc, setMedicalDoc] = useState(false)
  const [altName, setAltName] = useState("")
  const [altPhone, setAltPhone] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const inputCls = "w-full px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-sage/50 focus:border-sage min-h-[44px]"
  const labelCls = "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
    if (!reason.trim() || !address.trim() || !phone.trim()) {
      toast.error(t("patronHomeDelivery.pleaseFillInAllRequired"))
      return
    }
    setSubmitting(true)
    try {
      const app = await createHomeDeliveryApplication(clean({
        reason: reason.trim(),
        delivery_address: address.trim(),
        contact_phone: phone.trim(),
        preferred_frequency: frequency,
        preferred_day: preferredDay || undefined,
        preferred_time_start: timeStart || undefined,
        preferred_time_end: timeEnd || undefined,
        medical_documentation: medicalDoc,
        alternate_contact_name: altName.trim() || undefined,
        alternate_contact_phone: altPhone.trim() || undefined,
      }))
      onSubmitted(app)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.applicationForm.failedToSubmitApplication'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">{t("patronHomeDelivery.applyForHomeDelivery")}</h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        Home delivery is available to patrons who are homebound or have difficulty visiting the library.
      </p>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="app-reason" className={labelCls}>Reason for request *</label>
          <textarea
            id="app-reason"
            value={reason}
            onChange={e => setReason(e.target.value)}
            className={`${inputCls} min-h-[80px]`}
            placeholder={t("patronHomeDelivery.pleaseDescribeWhyYouNeed")}
            required
            aria-required="true"
            aria-describedby="app-reason-hint"
            aria-invalid={submitted && reason.trim() === "" ? true : undefined}
          />
          <p id="app-reason-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
            Describe why you need home delivery (e.g., mobility limitations, transportation issues).
          </p>
        </div>
        <div>
          <label htmlFor="app-address" className={labelCls}>Delivery address *</label>
          <input
            id="app-address"
            type="text"
            value={address}
            onChange={e => setAddress(e.target.value)}
            className={inputCls}
            placeholder={t('placeholder.applicationForm.123MainStApt')}
            required
            aria-required="true"
            aria-describedby="app-address-hint"
            aria-invalid={submitted && address.trim() === "" ? true : undefined}
          />
          <p id="app-address-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
            Full delivery address including apartment/unit number.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="app-phone" className={labelCls}>Contact phone *</label>
            <input
              id="app-phone"
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              className={inputCls}
              placeholder={t('placeholder.applicationForm.5555551234')}
              required
              aria-required="true"
              aria-describedby="app-phone-hint"
              aria-invalid={submitted && phone.trim() === "" ? true : undefined}
            />
            <p id="app-phone-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
              Phone number where we can reach you about deliveries.
            </p>
          </div>
          <div>
            <label htmlFor="app-frequency" className={labelCls}>Preferred frequency</label>
            <select id="app-frequency" value={frequency} onChange={e => setFrequency(e.target.value as DeliveryFrequency)} className={inputCls}>
              {FREQUENCY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="app-day" className={labelCls}>Preferred day</label>
            <select id="app-day" value={preferredDay} onChange={e => setPreferredDay(e.target.value)} className={inputCls}>
              <option value="">No preference</option>
              {DAY_OPTIONS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="app-time-start" className={labelCls}>Earliest time</label>
            <input id="app-time-start" type="time" value={timeStart} onChange={e => setTimeStart(e.target.value)} className={inputCls} />
          </div>
          <div>
            <label htmlFor="app-time-end" className={labelCls}>Latest time</label>
            <input id="app-time-end" type="time" value={timeEnd} onChange={e => setTimeEnd(e.target.value)} className={inputCls} />
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-start gap-3">
            <input
              id="app-medical"
              type="checkbox"
              checked={medicalDoc}
              onChange={e => setMedicalDoc(e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-sage/30 text-sage focus:ring-sage"
              aria-describedby="app-medical-privacy"
            />
            <label htmlFor="app-medical" className="text-sm text-lsc-dark dark:text-lsc-cream">
              I have medical documentation supporting my need for home delivery
            </label>
          </div>
          <p id="app-medical-privacy" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 ml-7">
            Your health information is kept confidential and only used to assess delivery eligibility. See our privacy policy for details.
          </p>
        </div>
        <fieldset className="border border-sage/20 dark:border-earth-600 rounded-lg p-4">
          <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream px-2">Alternate Contact (optional)</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="app-alt-name" className={labelCls}>Name</label>
              <input id="app-alt-name" type="text" value={altName} onChange={e => setAltName(e.target.value)} className={inputCls} placeholder={t('placeholder.applicationForm.contactName')} />
            </div>
            <div>
              <label htmlFor="app-alt-phone" className={labelCls}>Phone</label>
              <input id="app-alt-phone" type="tel" value={altPhone} onChange={e => setAltPhone(e.target.value)} className={inputCls} placeholder={t('placeholder.applicationForm.5555555678')} />
            </div>
          </div>
        </fieldset>
        <button
          type="submit"
          disabled={submitting}
          className="w-full md:w-auto bg-sage text-white px-6 py-3 rounded-lg font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] flex items-center justify-center gap-2"
          aria-label={t("patronHomeDelivery.submitHomeDeliveryApplication")}
        >
          {submitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Send className="w-4 h-4" />}
          {submitting ? "Submitting..." : "Submit Application"}
        </button>
      </form>
    </div>
  )
}
