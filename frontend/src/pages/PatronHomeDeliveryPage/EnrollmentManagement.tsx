/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import {
  Loader2,
  Pause,
  Play,
  Pencil,
  CheckCircle2,
  MapPin,
  Phone,
  User,
  CalendarDays,
  Truck,
  Package,
  X,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  pauseMyEnrollment,
  resumeMyEnrollment,
  updateMyEnrollment,
  type HomeDeliveryEnrollment,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { DAY_OPTIONS, statusBadge, formatStatus, formatDate } from "./types"

export function EnrollmentTab({
  enrollment,
  onEnrollmentUpdated,
}: {
  enrollment: HomeDeliveryEnrollment
  onEnrollmentUpdated: (e: HomeDeliveryEnrollment) => void
}) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [instructions, setInstructions] = useState(enrollment.delivery_instructions || "")
  const [contactPhone, setContactPhone] = useState(enrollment.contact_phone)
  const [prefDay, setPrefDay] = useState(enrollment.preferred_day || "")
  const [prefTimeStart, setPrefTimeStart] = useState(enrollment.preferred_time_start || "")
  const [prefTimeEnd, setPrefTimeEnd] = useState(enrollment.preferred_time_end || "")
  const [pauseReason, setPauseReason] = useState("")
  const [showPauseForm, setShowPauseForm] = useState(false)

  const inputCls = "w-full px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-sage/50 focus:border-sage min-h-[44px]"

  async function handleSave() {
    setSaving(true)
    try {
      const updated = await updateMyEnrollment(clean({
        delivery_instructions: instructions.trim() || undefined,
        contact_phone: contactPhone.trim() || undefined,
        preferred_day: prefDay || undefined,
        preferred_time_start: prefTimeStart || undefined,
        preferred_time_end: prefTimeEnd || undefined,
      }))
      onEnrollmentUpdated(updated)
      setEditing(false)
      toast.success(t('toast.enrollmentManagement.enrollmentUpdated'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.enrollmentManagement.failedToUpdateEnrollment'))
    } finally {
      setSaving(false)
    }
  }

  async function handlePause() {
    setSaving(true)
    try {
      const updated = await pauseMyEnrollment(clean({
        reason: pauseReason.trim() || undefined,
      }))
      onEnrollmentUpdated(updated)
      setShowPauseForm(false)
      setPauseReason("")
      toast.success(t('toast.enrollmentManagement.deliveriesPaused'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.enrollmentManagement.failedToPauseEnrollment'))
    } finally {
      setSaving(false)
    }
  }

  async function handleResume() {
    setSaving(true)
    try {
      const updated = await resumeMyEnrollment()
      onEnrollmentUpdated(updated)
      toast.success(t('toast.enrollmentManagement.deliveriesResumed'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.enrollmentManagement.failedToResumeEnrollment'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Status card */}
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Enrollment Details</h2>
          <span className={statusBadge(enrollment.status)}>{formatStatus(enrollment.status)}</span>
        </div>

        {enrollment.status === "paused" && enrollment.pause_reason && (
          <div className="mb-4 rounded-lg bg-earth-50 dark:bg-earth-800/20 p-3 text-sm text-earth-800 dark:text-lsc-rose-light">
            Paused: {enrollment.pause_reason}
            {enrollment.pause_until && ` (until ${formatDate(enrollment.pause_until)})`}
          </div>
        )}

        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 text-sm">
          <div className="flex items-start gap-2">
            <MapPin className="w-4 h-4 text-sage mt-0.5 shrink-0" />
            <div>
              <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Delivery Address</dt>
              <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{enrollment.delivery_address}</dd>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Phone className="w-4 h-4 text-sage mt-0.5 shrink-0" />
            <div>
              <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Contact Phone</dt>
              <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{editing
                ? <input type="tel" value={contactPhone} onChange={e => setContactPhone(e.target.value)} className={inputCls} />
                : enrollment.contact_phone
              }</dd>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <CalendarDays className="w-4 h-4 text-sage mt-0.5 shrink-0" />
            <div>
              <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Frequency</dt>
              <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{formatStatus(enrollment.delivery_frequency)}</dd>
            </div>
          </div>
          {enrollment.assigned_volunteer_name && (
            <div className="flex items-start gap-2">
              <User className="w-4 h-4 text-sage mt-0.5 shrink-0" />
              <div>
                <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Volunteer</dt>
                <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{enrollment.assigned_volunteer_name}</dd>
              </div>
            </div>
          )}
          {enrollment.next_scheduled_delivery && (
            <div className="flex items-start gap-2">
              <Truck className="w-4 h-4 text-sage mt-0.5 shrink-0" />
              <div>
                <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Next Delivery</dt>
                <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{formatDate(enrollment.next_scheduled_delivery)}</dd>
              </div>
            </div>
          )}
          <div className="flex items-start gap-2">
            <Package className="w-4 h-4 text-sage mt-0.5 shrink-0" />
            <div>
              <dt className="text-lsc-dark/70 dark:text-lsc-cream/60">Total Deliveries</dt>
              <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{enrollment.total_deliveries}</dd>
            </div>
          </div>
        </dl>

        {/* Editable fields */}
        {editing && (
          <div className="mt-6 space-y-4 border-t border-sage/20 dark:border-earth-600 pt-4">
            <div>
              <label htmlFor="enr-instructions" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Delivery Instructions</label>
              <textarea
                id="enr-instructions"
                value={instructions}
                onChange={e => setInstructions(e.target.value)}
                className={`${inputCls} min-h-[60px]`}
                placeholder={t('placeholder.enrollmentManagement.egLeaveAtSide')}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="enr-day" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Preferred Day</label>
                <select id="enr-day" value={prefDay} onChange={e => setPrefDay(e.target.value)} className={inputCls}>
                  <option value="">No preference</option>
                  {DAY_OPTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="enr-time-start" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Earliest Time</label>
                <input id="enr-time-start" type="time" value={prefTimeStart} onChange={e => setPrefTimeStart(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label htmlFor="enr-time-end" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Latest Time</label>
                <input id="enr-time-end" type="time" value={prefTimeEnd} onChange={e => setPrefTimeEnd(e.target.value)} className={inputCls} />
              </div>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-6 flex flex-wrap gap-3">
          {editing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 min-h-[44px] flex items-center gap-2"
                aria-label={t('aria.enrollmentManagement.saveEnrollmentChanges')}
              >
                {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="border border-sage/30 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream px-4 py-2 rounded-lg font-medium hover:bg-sage/10 transition-colors min-h-[44px]"
                aria-label={t('aria.shelf.cancelEditing')}
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="border border-sage/30 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream px-4 py-2 rounded-lg font-medium hover:bg-sage/10 transition-colors min-h-[44px] flex items-center gap-2"
              aria-label={t('aria.enrollmentManagement.editEnrollmentDetails')}
            >
              <Pencil className="w-4 h-4" /> Edit Details
            </button>
          )}

          {enrollment.status === "active" && (
            showPauseForm ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={pauseReason}
                  onChange={e => setPauseReason(e.target.value)}
                  placeholder={t('placeholder.enrollmentManagement.reasonOptional')}
                  className="px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm min-h-[44px]"
                  aria-label={t("patronHomeDelivery.reasonForPausingDeliveries")}
                />
                <button
                  onClick={handlePause}
                  disabled={saving}
                  className="bg-lsc-rose text-white px-4 py-2 rounded-lg font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 min-h-[44px] flex items-center gap-2"
                  aria-label={t('aria.enrollmentManagement.confirmPauseDeliveries')}
                >
                  {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Pause className="w-4 h-4" />}
                  Pause
                </button>
                <button onClick={() => setShowPauseForm(false)} className="text-lsc-dark/70 dark:text-lsc-cream/60 min-h-[44px] min-w-[44px] flex items-center justify-center" aria-label={t('aria.enrollmentManagement.cancelPause')}>
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowPauseForm(true)}
                className="bg-lsc-rose text-white px-4 py-2 rounded-lg font-medium hover:bg-lsc-rose/90 transition-colors min-h-[44px] flex items-center gap-2"
                aria-label={t('aria.enrollmentManagement.pauseDeliveries')}
              >
                <Pause className="w-4 h-4" /> Pause Deliveries
              </button>
            )
          )}

          {enrollment.status === "paused" && (
            <button
              onClick={handleResume}
              disabled={saving}
              className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 min-h-[44px] flex items-center gap-2"
              aria-label={t('aria.enrollmentManagement.resumeDeliveries')}
            >
              {saving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Play className="w-4 h-4" />}
              Resume Deliveries
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
