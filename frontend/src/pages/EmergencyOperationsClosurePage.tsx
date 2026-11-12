/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Building2,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  AlertTriangle,
  Mail,
  MessageCircle,
  Phone,
  Calendar,
  MapPin,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ClosureData {
  id: number
  closure_reason: string
  reason_details: string
  closure_start: string
  estimated_reopening?: string | null
  actual_reopening?: string | null
  is_active: boolean
  severity_level: string
  patrons_notified: boolean
  staff_notified: boolean
  services_affected?: string[] | null
  areas_affected?: string[] | null
  interim_services?: string | null
  created_at: string
}

export default function EmergencyOperationsClosurePage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [closures, setClosures] = useState<ClosureData[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedClosure, setSelectedClosure] = useState<ClosureData | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const closureReasons = [
    { id: "weather", label: "Weather Emergency" },
    { id: "power_outage", label: "Power Outage" },
    { id: "system_failure", label: "System Failure" },
    { id: "security_incident", label: "Security Incident" },
    { id: "natural_disaster", label: "Natural Disaster" },
    { id: "pandemic", label: "Pandemic/Health" },
    { id: "infrastructure_damage", label: "Infrastructure Damage" },
    { id: "scheduled_maintenance", label: "Scheduled Maintenance" },
    { id: "other", label: "Other" },
  ]

  const [form, setForm] = useState({
    closure_reason: "",
    reason_details: "",
    closure_start: "",
    estimated_reopening: "",
    severity_level: "moderate",
    areas_affected: [] as string[],
    services_affected: [] as string[],
  })

  const areas = ["Main Floor", "Children's Area", "Teen Area", "Adult Area", "Reference Section", "Makerspace"]

  const loadClosures = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await emergencyOperationsAPI.buildingClosure.getActiveClosures()
      setClosures(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsClosure.failedToLoadClosures'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin", "manager"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    loadClosures()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateClosure = async () => {
    if (!form.closure_reason || !form.reason_details || !form.closure_start) {
      toast.error(t('emergencyOperationsClosure.pleaseFillInAllRequired'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.buildingClosure.createClosure(clean({
        closure_reason: form.closure_reason,
        reason_details: form.reason_details,
        closure_start: form.closure_start,
        ...(form.estimated_reopening ? { estimated_reopening: form.estimated_reopening } : {}),
        areas_affected: form.areas_affected.length > 0 ? form.areas_affected : undefined,
        severity_level: form.severity_level,
      }))

      toast.success(t('emergencyOperationsClosure.buildingClosureCreatedSuccessfully'))
      setShowCreateModal(false)
      resetForm()
      loadClosures()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsClosure.failedToCreateClosure'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleNotifyPatrons = async (closureId: number) => {
    if (!selectedClosure) return

    try {
      setIsSaving(true)
      const message = `The library is closed: ${selectedClosure.reason_details}`
      await emergencyOperationsAPI.buildingClosure.notifyAboutClosure(closureId, message)

      toast.success(t('toast.emergencyOperationsClosure.patronsNotifiedSuccessfully'))
      loadClosures()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsClosure.failedToNotifyPatrons'))
    } finally {
      setIsSaving(false)
    }
  }

  const resetForm = () => {
    setForm({
      closure_reason: "",
      reason_details: "",
      closure_start: "",
      estimated_reopening: "",
      severity_level: "moderate",
      areas_affected: [],
      services_affected: [],
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  return (
    <AdminShell title="Building Closure Management" subtitle={t('emergencyOperationsClosure.communicateClosuresAndManagePatron')}>
      <div>
      <div>
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/emergency-operations")} className="hover:text-lsc-rose">
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div></div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Closure
          </button>
        </div>

        {/* Active Closures */}
        {closures.filter((c) => c.is_active).length > 0 ? (
          <div className="space-y-6 mb-8">
            <h2 className="text-2xl font-serif font-bold">Active Closures</h2>
            {closures
              .filter((c) => c.is_active)
              .map((closure) => (
                <div
                  key={closure.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-danger-300 dark:border-status-danger-700 p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Closure Details */}
                    <div>
                      <div className="flex items-start gap-3 mb-4">
                        <AlertTriangle className="w-6 h-6 text-status-danger-600 mt-1 flex-shrink-0" />
                        <div>
                          <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{closure.closure_reason}</h3>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {new Date(closure.closure_start).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{closure.reason_details}</p>

                      <div className="space-y-3 text-sm">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            <strong>Opened:</strong> {new Date(closure.closure_start).toLocaleDateString()}
                          </span>
                        </div>

                        {closure.estimated_reopening && (
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                              <strong>Est. Reopening:</strong>{" "}
                              {new Date(closure.estimated_reopening).toLocaleString()}
                            </span>
                          </div>
                        )}

                        {closure.actual_reopening && (
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-status-success-600" />
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                              <strong>Reopened:</strong>{" "}
                              {new Date(closure.actual_reopening).toLocaleString()}
                            </span>
                          </div>
                        )}

                        {closure.areas_affected && closure.areas_affected.length > 0 && (
                          <div className="flex items-start gap-2">
                            <MapPin className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex-shrink-0" />
                            <div>
                              <strong className="block">Affected Areas:</strong>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {closure.areas_affected.map((area: string) => (
                                  <span
                                    key={area}
                                    className="px-2 py-1 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 rounded text-xs font-semibold"
                                  >
                                    {area}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Notification Status */}
                    <div>
                      <h4 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Notification Status</h4>

                      <div className="space-y-3 mb-6">
                        <div
                          className={`p-3 rounded border-2 flex items-center gap-3 ${
                            closure.patrons_notified
                              ? "bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800"
                              : "bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800"
                          }`}
                        >
                          {closure.patrons_notified ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600" />
                          )}
                          <div className="flex-1">
                            <div className="font-semibold text-sm">
                              {closure.patrons_notified ? "Patrons Notified" : "Patrons Not Notified"}
                            </div>
                          </div>
                        </div>

                        <div
                          className={`p-3 rounded border-2 flex items-center gap-3 ${
                            closure.staff_notified
                              ? "bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800"
                              : "bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800"
                          }`}
                        >
                          {closure.staff_notified ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600" />
                          )}
                          <div className="flex-1">
                            <div className="font-semibold text-sm">
                              {closure.staff_notified ? "Staff Notified" : "Staff Not Notified"}
                            </div>
                          </div>
                        </div>
                      </div>

                      {!closure.patrons_notified && (
                        <button
                          onClick={() => {
                            setSelectedClosure(closure)
                            handleNotifyPatrons(closure.id)
                          }}
                          disabled={isSaving}
                          className="w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold disabled:opacity-50 flex items-center justify-center gap-2 mb-3"
                        >
                          {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Mail className="w-4 h-4" />}
                          Notify All Patrons
                        </button>
                      )}

                      <div className="space-y-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <p className="flex items-center gap-2">
                          <Mail className="w-3 h-3" />
                          Email notifications will be sent
                        </p>
                        <p className="flex items-center gap-2">
                          <MessageCircle className="w-3 h-3" />
                          SMS updates available
                        </p>
                        <p className="flex items-center gap-2">
                          <Phone className="w-3 h-3" />
                          Phone tree can be triggered
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="bg-earth-50 dark:bg-earth-800/20 border-2 border-lsc-border dark:border-earth-700 rounded-lg p-8 text-center mb-8">
            <Building2 className="w-12 h-12 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('emergencyOperationsClosure.noActiveBuildingClosures')}</p>
          </div>
        )}

        {/* Past Closures */}
        {closures.filter((c) => !c.is_active).length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-xl font-bold mb-4">Past Closures</h2>
            <div className="space-y-3">
              {closures
                .filter((c) => !c.is_active)
                .slice(0, 5)
                .map((closure) => (
                  <div key={closure.id} className="p-4 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{closure.closure_reason}</h4>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {new Date(closure.closure_start).toLocaleDateString()} to{" "}
                          {closure.actual_reopening
                            ? new Date(closure.actual_reopening).toLocaleDateString()
                            : "TBD"}
                        </p>
                      </div>
                      <CheckCircle2 className="w-5 h-5 text-status-success-600" />
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

      {/* Create Closure Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={() => setShowCreateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <Building2 className="w-6 h-6 text-status-danger-600" />
                Create Building Closure
              </h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">Closure Reason *</label>
                <select
                  value={form.closure_reason}
                  onChange={(e) => setForm({ ...form, closure_reason: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
                >
                  <option value="">Select a reason...</option>
                  {closureReasons.map((reason) => (
                    <option key={reason.id} value={reason.id}>
                      {reason.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Details *</label>
                <textarea
                  value={form.reason_details}
                  onChange={(e) => setForm({ ...form, reason_details: e.target.value })}
                  placeholder={t('emergencyOperationsClosure.provideDetailsAboutTheClosure')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Start Time *</label>
                  <input
                    type="datetime-local"
                    value={form.closure_start}
                    onChange={(e) => setForm({ ...form, closure_start: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Est. Reopening Time</label>
                  <input
                    type="datetime-local"
                    value={form.estimated_reopening}
                    onChange={(e) => setForm({ ...form, estimated_reopening: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Severity Level</label>
                <select
                  value={form.severity_level}
                  onChange={(e) => setForm({ ...form, severity_level: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-danger-500 outline-none"
                >
                  <option value="minimal">Minimal</option>
                  <option value="moderate">Moderate</option>
                  <option value="severe">Severe</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Affected Areas</label>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {areas.map((area) => (
                    <label key={area} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                      <input
                        type="checkbox"
                        checked={form.areas_affected.includes(area)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({
                              ...form,
                              areas_affected: [...form.areas_affected, area],
                            })
                          } else {
                            setForm({
                              ...form,
                              areas_affected: form.areas_affected.filter((a) => a !== area),
                            })
                          }
                        }}
                      />
                      <span>{area}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateClosure}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Building2 className="w-4 h-4" />}
                  Create Closure
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
      </div>
      </div>
    </AdminShell>
  )
}
