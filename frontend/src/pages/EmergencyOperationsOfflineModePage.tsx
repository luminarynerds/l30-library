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
  WifiOff,
  Wifi,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  X,
  Loader2,
  RefreshCw,
  FileText,
  AlertCircle,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export default function EmergencyOperationsOfflineModePage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [offlineStatus, setOfflineStatus] = useState<any>(null)
  const [showActivateModal, setShowActivateModal] = useState(false)
  const [showDeactivateModal, setShowDeactivateModal] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [activateForm, setActivateForm] = useState({
    reason: "",
    affected_services: [] as string[],
    affected_branches: [] as number[],
    recovery_priority: "normal",
    estimated_restoration: "",
  })

  const [syncData, setSyncData] = useState({
    total_items: 0,
    pending: 0,
    synced: 0,
    failed: 0,
    pending_percentage: 0,
  })

  const services = [
    { id: "circulation", label: "Circulation System", icon: "📚" },
    { id: "catalog", label: "Catalog Search", icon: "🔍" },
    { id: "patron_accounts", label: "Patron Accounts", icon: "👤" },
    { id: "holds", label: "Hold System", icon: "🚀" },
    { id: "renewals", label: "Renewals", icon: "🔄" },
    { id: "events", label: "Events", icon: "📅" },
  ]

  const loadOfflineModeData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [status, syncStats] = await Promise.all([
        emergencyOperationsAPI.offlineMode.getOfflineModeStatus(),
        emergencyOperationsAPI.dataSync.getSyncStatistics(),
      ])

      setOfflineStatus(status)
      setSyncData(syncStats)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsOfflineMode.failedToLoadOfflineMode'))
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

    loadOfflineModeData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleActivateOfflineMode = async () => {
    if (!activateForm.reason.trim()) {
      toast.error(t('emergencyOperationsOfflineMode.pleaseProvideAReasonFor'))
      return
    }

    if (activateForm.affected_services.length === 0) {
      toast.error(t('emergencyOperationsOfflineMode.pleaseSelectAtLeastOne'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.offlineMode.activateOfflineMode({
        reason: activateForm.reason,
        affected_services: activateForm.affected_services,
        affected_branches: activateForm.affected_branches.length > 0 ? activateForm.affected_branches : null,
        recovery_priority: activateForm.recovery_priority,
        ...(activateForm.estimated_restoration ? { estimated_restoration: activateForm.estimated_restoration } : {}),
      })

      toast.success(t('emergencyOperationsOfflineMode.offlineModeActivatedSuccessfully'))
      setShowActivateModal(false)
      setActivateForm({
        reason: "",
        affected_services: [],
        affected_branches: [],
        recovery_priority: "normal",
        estimated_restoration: "",
      })
      loadOfflineModeData()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsOfflineMode.failedToActivateOfflineMode'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeactivateOfflineMode = async () => {
    if (!offlineStatus?.mode_details?.id) return

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.offlineMode.deactivateOfflineMode(offlineStatus.mode_details.id)
      toast.success(t('emergencyOperationsOfflineMode.offlineModeDeactivatedSystemIs'))
      setShowDeactivateModal(false)
      loadOfflineModeData()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsOfflineMode.failedToDeactivateOfflineMode'))
    } finally {
      setIsSaving(false)
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  return (
    <AdminShell title="Offline Mode Management" subtitle={t('emergencyOperationsOfflineMode.enableOperationsDuringSystemOutages')}>
      <div>
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/emergency-operations")} className="hover:text-lsc-rose">
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div></div>
          </div>
        </div>

        {/* Current Status */}
        <div
          className={`mb-8 p-6 rounded-lg border-2 ${
            offlineStatus?.is_offline
              ? "bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-300 dark:border-status-danger-700"
              : "bg-status-success-50 dark:bg-status-success-900/20 border-status-success-300 dark:border-status-success-700"
          }`}
        >
          <div className="flex items-start gap-4">
            {offlineStatus?.is_offline ? (
              <WifiOff className="w-8 h-8 text-status-danger-600 mt-1 flex-shrink-0" />
            ) : (
              <Wifi className="w-8 h-8 text-status-success-600 mt-1 flex-shrink-0" />
            )}
            <div className="flex-1">
              <h2
                className={`text-2xl font-bold ${
                  offlineStatus?.is_offline ? "text-status-danger-900" : "text-status-success-900 dark:text-status-success-200"
                }`}
              >
                {offlineStatus?.is_offline ? "OFFLINE" : "ONLINE"}
              </h2>
              {offlineStatus?.is_offline ? (
                <div className="mt-3 space-y-2 text-status-danger-800 dark:text-status-danger-300">
                  <p>
                    <strong>Reason:</strong> {offlineStatus.reason}
                  </p>
                  {offlineStatus.estimated_restoration && (
                    <p>
                      <strong>Estimated Restoration:</strong>{" "}
                      {new Date(offlineStatus.estimated_restoration).toLocaleString()}
                    </p>
                  )}
                  <p>
                    <strong>Recovery Priority:</strong> {offlineStatus.recovery_priority}
                  </p>
                  <p>
                    <strong>Pending Sync Items:</strong> {offlineStatus.pending_sync_items}
                  </p>
                </div>
              ) : (
                <p className="text-status-success-800 dark:text-status-success-300 mt-2">{t('emergencyOperationsOfflineMode.allSystemsOperationalNoOffline')}</p>
              )}
            </div>
            <div className="flex gap-2 flex-shrink-0">
              {!offlineStatus?.is_offline ? (
                <button
                  onClick={() => setShowActivateModal(true)}
                  className="px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors font-semibold flex items-center gap-2"
                >
                  <AlertTriangle className="w-4 h-4" />
                  Activate Offline Mode
                </button>
              ) : (
                <button
                  onClick={() => setShowDeactivateModal(true)}
                  className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors font-semibold flex items-center gap-2"
                >
                  <Wifi className="w-4 h-4" />
                  Deactivate Offline Mode
                </button>
              )}
            </div>
          </div>
        </div>

        {offlineStatus?.is_offline && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Sync Statistics */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
              <h3 className="font-serif text-xl font-bold mb-4 flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                Data Synchronization Progress
              </h3>

              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-semibold">{syncData.pending_percentage.toFixed(1)}% Complete</span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {syncData.synced} of {syncData.total_items}
                    </span>
                  </div>
                  <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-lsc-rose h-full transition-all duration-300"
                      style={{ width: `${100 - syncData.pending_percentage}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="bg-earth-50 dark:bg-earth-800/20 p-3 rounded border border-lsc-border dark:border-earth-700">
                    <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{syncData.synced}</div>
                    <div className="text-sm text-earth-800 dark:text-lsc-rose-light">Synced</div>
                  </div>
                  <div className="bg-status-warning-50 dark:bg-status-warning-900/20 p-3 rounded border border-status-warning-200 dark:border-status-warning-800">
                    <div className="text-2xl font-bold text-status-warning-600">{syncData.pending}</div>
                    <div className="text-sm text-status-warning-800 dark:text-status-warning-300">Pending</div>
                  </div>
                  <div className="bg-status-danger-50 dark:bg-status-danger-900/20 p-3 rounded border border-status-danger-200 dark:border-status-danger-800">
                    <div className="text-2xl font-bold text-status-danger-600">{syncData.failed}</div>
                    <div className="text-sm text-status-danger-800 dark:text-status-danger-300">Failed</div>
                  </div>
                  <div className="bg-earth-50 dark:bg-earth-900 p-3 rounded border border-lsc-border dark:border-earth-700">
                    <div className="text-2xl font-bold text-lsc-dark/70 dark:text-lsc-cream/70">{syncData.total_items}</div>
                    <div className="text-sm text-earth-800 dark:text-earth-100">Total Items</div>
                  </div>
                </div>

                <button
                  onClick={() => navigate("/emergency-operations/data-sync")}
                  className="w-full mt-4 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold"
                >
                  View Detailed Sync
                </button>
              </div>
            </div>

            {/* Affected Services */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
              <h3 className="font-serif text-xl font-bold mb-4">Affected Services</h3>

              <div className="space-y-2">
                {offlineStatus?.affected_services?.map((service: string) => (
                  <div key={service} className="flex items-center gap-3 p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                    <AlertCircle className="w-5 h-5 text-status-warning-600" />
                    <span className="font-semibold text-earth-800 dark:text-earth-100">{service}</span>
                  </div>
                ))}
              </div>

              {offlineStatus?.affected_branches && offlineStatus.affected_branches.length > 0 && (
                <div className="mt-6">
                  <h4 className="font-serif font-semibold mb-3">Affected Branches</h4>
                  <div className="space-y-2">
                    {offlineStatus.affected_branches.map((branch: number) => (
                      <div
                        key={branch}
                        className="flex items-center gap-3 p-2 bg-earth-50 dark:bg-earth-800/20 rounded border border-lsc-border dark:border-earth-700"
                      >
                        <CheckCircle2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                        <span className="text-earth-800 dark:text-earth-100">Branch {branch}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Paper Backup Information */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6 mb-8">
          <h3 className="font-serif text-xl font-bold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-status-warning-600" />
            Paper Backup Procedures
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('emergencyOperationsOfflineMode.availableDuringOfflineMode')}</h4>
              <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-status-success-600 mt-0.5 flex-shrink-0" />
                  <span>{t('emergencyOperationsOfflineMode.paperBasedCheckoutAndReturn')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-status-success-600 mt-0.5 flex-shrink-0" />
                  <span>{t('emergencyOperationsOfflineMode.manualHoldAndRenewalProcessing')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-status-success-600 mt-0.5 flex-shrink-0" />
                  <span>{t('emergencyOperationsOfflineMode.patronInformationLookupViaBackup')}</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-status-success-600 mt-0.5 flex-shrink-0" />
                  <span>{t('emergencyOperationsOfflineMode.transactionLoggingForLaterSync')}</span>
                </li>
              </ul>
            </div>

            <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded p-4">
              <h4 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80 mb-3">Quick Links</h4>
              <div className="space-y-2">
                <button
                  onClick={() => navigate("/emergency-operations/paper-backup")}
                  className="w-full text-left px-3 py-2 bg-lsc-white dark:bg-earth-800 hover:bg-earth-100 rounded border border-lsc-border dark:border-earth-600 transition-colors text-earth-900 dark:text-lsc-rose-light/80 font-semibold"
                >
                  View Paper Forms
                </button>
                <button
                  onClick={() => navigate("/emergency-operations/recovery")}
                  className="w-full text-left px-3 py-2 bg-lsc-white dark:bg-earth-800 hover:bg-earth-100 rounded border border-lsc-border dark:border-earth-600 transition-colors text-earth-900 dark:text-lsc-rose-light/80 font-semibold"
                >
                  View Pending Submissions
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Offline Instructions */}
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-300 dark:border-status-warning-700 rounded-lg p-6">
          <h3 className="font-serif font-bold text-status-warning-900 dark:text-status-warning-200 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Staff Instructions During Offline Mode
          </h3>
          <ol className="space-y-2 text-sm text-status-warning-900 dark:text-status-warning-200 list-decimal list-inside">
            <li>{t('emergencyOperationsOfflineMode.printPaperBackupFormsFor')}</li>
            <li>{t('emergencyOperationsOfflineMode.recordAllPatronActivityOn')}</li>
            <li>{t('emergencyOperationsOfflineMode.verifyPatronInformationManuallyFrom')}</li>
            <li>{t('emergencyOperationsOfflineMode.storeCompletedFormsInSecure')}</li>
            <li>{t('emergencyOperationsOfflineMode.prepareForAutomaticSyncWhen')}</li>
            <li>{t('emergencyOperationsOfflineMode.contactManagementWithQuestionsOr')}</li>
          </ol>
        </div>

      {/* Activate Offline Mode Modal */}
      {showActivateModal && (
        <ModalBackdrop onClose={() => setShowActivateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <WifiOff className="w-6 h-6 text-status-danger-600" />
                Activate Offline Mode
              </h2>
              <button onClick={() => setShowActivateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">{t('emergencyOperationsOfflineMode.reasonForOfflineMode')}</label>
                <textarea
                  value={activateForm.reason}
                  onChange={(e) => setActivateForm({ ...activateForm, reason: e.target.value })}
                  placeholder={t('placeholder.emergencyOperationsOfflineMode.egPowerOutageInternet')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                  rows={3}
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Affected Services *</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {services.map((service) => (
                    <label key={service.id} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                      <input
                        type="checkbox"
                        checked={activateForm.affected_services.includes(service.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setActivateForm({
                              ...activateForm,
                              affected_services: [...activateForm.affected_services, service.id],
                            })
                          } else {
                            setActivateForm({
                              ...activateForm,
                              affected_services: activateForm.affected_services.filter((s) => s !== service.id),
                            })
                          }
                        }}
                      />
                      <span>{service.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Recovery Priority</label>
                <select
                  value={activateForm.recovery_priority}
                  onChange={(e) => setActivateForm({ ...activateForm, recovery_priority: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="normal">Normal</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Estimated Restoration Time</label>
                <input
                  type="datetime-local"
                  value={activateForm.estimated_restoration}
                  onChange={(e) => setActivateForm({ ...activateForm, estimated_restoration: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowActivateModal(false)}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleActivateOfflineMode}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <WifiOff className="w-4 h-4" />}
                  Activate Offline Mode
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Deactivate Offline Mode Modal */}
      {showDeactivateModal && (
        <ModalBackdrop onClose={() => setShowDeactivateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <Wifi className="w-6 h-6 text-status-success-600" />
                Deactivate Offline Mode
              </h2>
              <button onClick={() => setShowDeactivateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Are you sure? Deactivating offline mode will:
            </p>

            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 list-disc list-inside">
              <li>{t('emergencyOperationsOfflineMode.endPaperBackupProcedures')}</li>
              <li>{t('emergencyOperationsOfflineMode.beginAutomaticDataSynchronization')}</li>
              <li>Process {syncData.pending} pending items</li>
              <li>{t('emergencyOperationsOfflineMode.resumeNormalSystemOperations')}</li>
            </ul>

            <div className="flex gap-3">
              <button
                onClick={() => setShowDeactivateModal(false)}
                disabled={isSaving}
                className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivateOfflineMode}
                disabled={isSaving}
                className="flex-1 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Wifi className="w-4 h-4" />}
                Deactivate
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
      </div>
    </AdminShell>
  )
}
