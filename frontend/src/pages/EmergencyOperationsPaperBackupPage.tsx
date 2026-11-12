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
  FileText,
  ChevronLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Clock,
  User,
  Barcode,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'

interface PaperSubmission {
  id: number
  form_id: number
  form_type: string
  transaction_date: string
  staff_initials: string
  patron_id?: number | null
  item_barcode?: string | null
  synced: boolean
  synced_at?: string | null
  sync_resolution?: string | null
  created_at: string
}

export default function EmergencyOperationsPaperBackupPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [submissions, setSubmissions] = useState<PaperSubmission[]>([])
  const [filterType, setFilterType] = useState<string | null>(null)
  const [filterSynced, setFilterSynced] = useState<boolean | null>(null)
  const [selectedSubmissions, setSelectedSubmissions] = useState<Set<number>>(new Set())
  const [expandedSubmission, setExpandedSubmission] = useState<number | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)

  const loadSubmissions = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await emergencyOperationsAPI.paperBackup.getPendingSubmissions(filterType ?? undefined, 999)
      setSubmissions(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsPaperBackup.failedToLoadPaperSubmissions'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType])


  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin", "manager"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    loadSubmissions()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleSyncSubmission = async (submissionId: number) => {
    try {
      setIsSyncing(true)
      await emergencyOperationsAPI.dataSync.queueSyncItem({
        sync_source: "paper_forms",
        entity_type: "paper_submission",
        entity_data: { submission_id: submissionId },
      })

      toast.success(t('emergencyOperationsPaperBackup.submissionQueuedForSync'))
      loadSubmissions()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsPaperBackup.failedToSyncSubmission'))
    } finally {
      setIsSyncing(false)
    }
  }

  const handleBatchSync = async () => {
    if (selectedSubmissions.size === 0) {
      toast.error(t('emergencyOperationsPaperBackup.pleaseSelectSubmissionsToSync'))
      return
    }

    try {
      setIsSyncing(true)
      for (const id of selectedSubmissions) {
        await emergencyOperationsAPI.dataSync.queueSyncItem({
          sync_source: "paper_forms",
          entity_type: "paper_submission",
          entity_data: { submission_id: id },
        })
      }

      toast.success(t('toast.emergencyOperationsPaperBackup.sizeSubmissionsQueuedForSync', { size: selectedSubmissions.size }))
      setSelectedSubmissions(new Set())
      loadSubmissions()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsPaperBackup.failedToSyncSubmissions'))
    } finally {
      setIsSyncing(false)
    }
  }

  const toggleSubmissionSelection = (id: number) => {
    const newSelection = new Set(selectedSubmissions)
    if (newSelection.has(id)) {
      newSelection.delete(id)
    } else {
      newSelection.add(id)
    }
    setSelectedSubmissions(newSelection)
  }

  const toggleSelectAll = () => {
    if (selectedSubmissions.size === filteredSubmissions.length) {
      setSelectedSubmissions(new Set())
    } else {
      setSelectedSubmissions(new Set(filteredSubmissions.map((s) => s.id)))
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  const formTypes = [...new Set(submissions.map((s) => s.form_type))]

  const filteredSubmissions = submissions.filter((submission) => {
    if (filterType && submission.form_type !== filterType) return false
    if (filterSynced !== null && submission.synced !== filterSynced) return false
    return true
  })

  const stats = {
    total: submissions.length,
    pending: submissions.filter((s) => !s.synced).length,
    synced: submissions.filter((s) => s.synced).length,
  }

  return (
    <AdminShell title="Paper Backup Submissions" subtitle={t('emergencyOperationsPaperBackup.manageAndSyncOfflineTransactions')}>
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

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Total Submissions</h3>
              <FileText className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">{stats.total}</div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-warning-200 dark:border-status-warning-800 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200">Pending Sync</h3>
              <AlertCircle className="w-5 h-5 text-status-warning-600" />
            </div>
            <div className="text-3xl font-bold text-status-warning-600">{stats.pending}</div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-success-200 dark:border-status-success-800 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200">Synced</h3>
              <CheckCircle2 className="w-5 h-5 text-status-success-600" />
            </div>
            <div className="text-3xl font-bold text-status-success-600">{stats.synced}</div>
          </div>
        </div>

        {/* Filters and Actions */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-4 mb-6 flex gap-4 flex-wrap items-end">
          <div>
            <label className="block font-semibold mb-2 text-sm">Filter by Type</label>
            <select
              value={filterType || ""}
              onChange={(e) => setFilterType(e.target.value || null)}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
            >
              <option value="">All Types</option>
              {formTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold mb-2 text-sm">Filter by Status</label>
            <select
              value={filterSynced === null ? "" : filterSynced ? "synced" : "pending"}
              onChange={(e) => {
                if (e.target.value === "pending") setFilterSynced(false)
                else if (e.target.value === "synced") setFilterSynced(true)
                else setFilterSynced(null)
              }}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="synced">Synced</option>
            </select>
          </div>

          <button
            onClick={() => {
              setFilterType(null)
              setFilterSynced(null)
            }}
            className="px-3 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 rounded-lg transition-colors text-sm font-semibold"
          >
            Clear Filters
          </button>

          {selectedSubmissions.size > 0 && (
            <button
              onClick={handleBatchSync}
              disabled={isSyncing}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold disabled:opacity-50 flex items-center gap-2 ml-auto"
            >
              {isSyncing ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              Sync {selectedSubmissions.size} Items
            </button>
          )}
        </div>

        {/* Submissions List */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="p-4 bg-earth-100 dark:bg-earth-700 border-b-2 border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <h3 className="font-serif font-bold text-lg">Submissions ({filteredSubmissions.length})</h3>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSubmissions.size === filteredSubmissions.length && filteredSubmissions.length > 0}
                onChange={toggleSelectAll}
                className="w-4 h-4"
              />
              <span className="text-sm font-semibold">Select All</span>
            </label>
          </div>

          <div className="divide-y-2 divide-earth-200 dark:divide-earth-700">
            {filteredSubmissions.length > 0 ? (
              filteredSubmissions.map((submission) => (
                <div key={submission.id} className="p-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors">
                  <div className="flex items-center gap-3 mb-3">
                    <input
                      type="checkbox"
                      checked={selectedSubmissions.has(submission.id)}
                      onChange={() => toggleSubmissionSelection(submission.id)}
                      className="w-4 h-4"
                    />

                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() =>
                        setExpandedSubmission(expandedSubmission === submission.id ? null : submission.id)
                      } tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() =>
                        setExpandedSubmission(expandedSubmission === submission.id ? null : submission.id))(); } }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          {submission.synced ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                          )}

                          <div className="flex-1">
                            <div className="font-semibold text-lsc-dark dark:text-lsc-cream">
                              {submission.form_type} - {submission.staff_initials}
                            </div>
                            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {new Date(submission.transaction_date).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-bold ${
                            submission.synced
                              ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300"
                              : "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300"
                          }`}
                        >
                          {submission.synced ? "SYNCED" : "pending"}
                        </span>

                        {expandedSubmission === submission.id ? (
                          <EyeOff className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 ml-3" />
                        ) : (
                          <Eye className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 ml-3" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedSubmission === submission.id && (
                    <div className="mt-4 pt-4 border-t-2 border-lsc-border dark:border-earth-700 space-y-3 ml-7">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Form Type:</label>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{submission.form_type}</p>
                        </div>

                        <div>
                          <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Staff Initials:</label>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{submission.staff_initials}</p>
                        </div>

                        {submission.patron_id && (
                          <div>
                            <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm flex items-center gap-1">
                              <User className="w-4 h-4" />
                              Patron ID:
                            </label>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{submission.patron_id}</p>
                          </div>
                        )}

                        {submission.item_barcode && (
                          <div>
                            <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm flex items-center gap-1">
                              <Barcode className="w-4 h-4" />
                              Item Barcode:
                            </label>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">{submission.item_barcode}</p>
                          </div>
                        )}

                        <div>
                          <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            Created:
                          </label>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(submission.created_at).toLocaleString()}</p>
                        </div>

                        {submission.synced && submission.synced_at && (
                          <div>
                            <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm flex items-center gap-1">
                              <CheckCircle2 className="w-4 h-4" />
                              Synced:
                            </label>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {new Date(submission.synced_at).toLocaleString()}
                            </p>
                          </div>
                        )}

                        {submission.sync_resolution && (
                          <div>
                            <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Resolution:</label>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{submission.sync_resolution}</p>
                          </div>
                        )}
                      </div>

                      {!submission.synced && (
                        <button
                          onClick={() => handleSyncSubmission(submission.id)}
                          disabled={isSyncing}
                          className="w-full mt-3 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
                        >
                          {isSyncing ? (
                            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-4 h-4" />
                          )}
                          Sync This Submission
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                <FileText className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
                <p className="font-semibold">{t('emergencyOperationsPaperBackup.noSubmissionsToDisplay')}</p>
                <p className="text-sm mt-1">{t('emergencyOperationsPaperBackup.allPaperSubmissionsHaveBeen')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-earth-50 dark:bg-earth-800/20 border-2 border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <h3 className="font-serif font-bold text-earth-900 dark:text-lsc-rose-light/80 mb-3">Paper Submission Processing</h3>
          <ol className="space-y-2 text-sm text-earth-800 dark:text-lsc-rose-light list-decimal list-inside">
            <li>{t('emergencyOperationsPaperBackup.staffSubmitsPaperFormsDuring')}</li>
            <li>{t('emergencyOperationsPaperBackup.formsAreRecordedWithTransaction')}</li>
            <li>{t('emergencyOperationsPaperBackup.onceSystemComesBackOnline')}</li>
            <li>{t('emergencyOperationsPaperBackup.selectSubmissionsAndClickSync')}</li>
            <li>{t('emergencyOperationsPaperBackup.systemAutomaticallyValidatesAndIntegrates')}</li>
            <li>{t('emergencyOperationsPaperBackup.statusUpdatesToSyncedWhen')}</li>
          </ol>

      </div>
      </div>
    </AdminShell>
  )
}
