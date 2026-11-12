/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells/AdminShell'
import {
  FileText,
  RefreshCw,
  Loader2,
  Plus,
  Save,
  Edit2,
  Trash2,
  AlertTriangle,
  TestTube2,
  BarChart3,
  Download,
  X,
  Server,
  Clock} from "lucide-react"
import toast from "react-hot-toast"
import ConfirmDialog from "../components/ConfirmDialog"
import * as ediApi from "../api/edi-api"
import { getVendors, type Vendor } from "@/api/acquisition-api"
import { useTranslation, getCurrentLocale } from '@/i18n'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { StatusVariant } from '@/components/ui/StatusBadge'

export default function AdminEDISettingsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()
  const { authLoading, isAuthorized } = useRequireRole('systemAdmin')
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [profiles, setProfiles] = useState<ediApi.VendorEDIProfile[]>([])
  const [stats, setStats] = useState<ediApi.EDIStatistics | null>(null)
  const [transactions, setTransactions] = useState<ediApi.EDITransaction[]>([])
  const [viewMode, setViewMode] = useState<"profiles" | "transactions" | "stats">("profiles")
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [editingProfile, setEditingProfile] = useState<ediApi.VendorEDIProfile | null>(null)
  const [isTesting, setIsTesting] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [vendorsList, setVendorsList] = useState<Vendor[]>([])

  const [profileForm, setProfileForm] = useState<ediApi.VendorEDIProfileCreate>({
    vendor_id: 0,
    is_enabled: true,
    edi_standard: "edifact",
    transport_protocol: "sftp",
    supports_orders: true,
    supports_ordrsp: true,
    supports_desadv: true,
    supports_invoic: true,
    max_retries: 3,
    retry_interval_minutes: 60,
    auto_send_orders: false,
    auto_process_responses: true,
    auto_approve_invoices: false,
    invoice_tolerance_percent: 5,
    is_test_mode: true,
  })

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthorized, navigate, t])

  const fetchProfiles = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await ediApi.getEDIProfiles()
      setProfiles(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminEDISettings.failedToLoadEdiProfiles'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const data = await ediApi.getEDIStatistics()
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  const fetchTransactions = useCallback(async () => {
    try {
      const data = await ediApi.getEDITransactions({ per_page: 20 })
      setTransactions(data.items)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  const fetchVendors = useCallback(async () => {
    try {
      const data = await getVendors({ per_page: 100, status: 'active' })
      setVendorsList(data.items)
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchVendors()
      fetchProfiles()
      fetchStats()
      fetchTransactions()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isAuthenticated, fetchProfiles, fetchStats, fetchTransactions])

  const handleSaveProfile = async () => {
    if (!profileForm.vendor_id) {
      toast.error(t('admin.adminEDISettings.vendorIdIsRequired'))
      return
    }
    try {
      if (editingProfile) {
        await ediApi.updateEDIProfile(editingProfile.id, profileForm)
        toast.success(t('toast.adminEDISettings.profileUpdated'))
      } else {
        await ediApi.createEDIProfile(profileForm)
        toast.success(t('toast.adminEDISettings.profileCreated'))
      }
      setShowProfileModal(false)
      setEditingProfile(null)
      setProfileForm({
        vendor_id: 0,
        is_enabled: true,
        edi_standard: "edifact",
        transport_protocol: "sftp",
        supports_orders: true,
        supports_ordrsp: true,
        supports_desadv: true,
        supports_invoic: true,
        max_retries: 3,
        retry_interval_minutes: 60,
        auto_send_orders: false,
        auto_process_responses: true,
        auto_approve_invoices: false,
        invoice_tolerance_percent: 5,
        is_test_mode: true,
      })
      fetchProfiles()
    } catch (_error: unknown) {
      toast.error(t('admin.adminEDISettings.failedToSaveProfile'))
    }
  }

  const handleDeleteProfile = async (profileId: number) => {
    setIsDeleting(true)
    try {
      await ediApi.deleteEDIProfile(profileId)
      toast.success(t('toast.adminEDISettings.profileDeleted'))
      fetchProfiles()
    } catch (_error: unknown) {
      toast.error(t('admin.adminEDISettings.failedToDeleteProfile'))
    } finally {
      setIsDeleting(false)
      setDeleteConfirm(null)
    }
  }

  const handleTestConnection = async (vendorId: number) => {
    setIsTesting(vendorId)
    try {
      const result = await ediApi.testEDIConnection(vendorId)
      if (result.success) {
        toast.success(result.message)
      } else {
        toast.error(result.message)
      }
    } catch (_error: unknown) {
      toast.error(t('toast.adminEDISettings.connectionTestFailed'))
    } finally {
      setIsTesting(null)
    }
  }

  const handleProcessInbound = async () => {
    try {
      const result = await ediApi.processInboundMessages()
      toast.success(t('toast.adminEDISettings.processedFilesprocessedFilesCreatedTransactionscreated', { filesprocessed: result.files_processed, transactionscreated: result.transactions_created }))
      fetchTransactions()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t('admin.adminEDISettings.failedToProcessInboundMessages'))
    }
  }

  const handleRetryTransaction = async (transactionId: number) => {
    try {
      const result = await ediApi.retryEDITransaction(transactionId)
      if (result.success) {
        toast.success(result.message)
        fetchTransactions()
      } else {
        toast.error(result.message)
      }
    } catch (_error: unknown) {
      toast.error(t('admin.adminEDISettings.failedToRetryTransaction'))
    }
  }

  const getTxStatusVariant = (status: string): StatusVariant => {
    switch (status.toLowerCase()) {
      case "processed":
      case "acknowledged":
        return "success"
      case "pending":
      case "sent":
        return "neutral"
      case "failed":
        return "danger"
      case "retry":
        return "warning"
      default:
        return "neutral"
    }
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "N/A"
    return new Date(dateStr).toLocaleString(getCurrentLocale(), {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthorized) {
    return <></>
  }

  return (
    <AdminShell title="EDI Settings">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                EDI Settings
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Configure Electronic Data Interchange with vendors
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  fetchProfiles()
                  fetchStats()
                  fetchTransactions()
                }}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button
                onClick={handleProcessInbound}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
              >
                <Download className="w-4 h-4" />
                Process Inbound
              </button>
            </div>
          </div>

          {/* Stats Summary */}
          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-xs uppercase">Total Transactions</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {stats.total_transactions}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-xs uppercase">Pending</span>
                </div>
                <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                  {stats.pending_transactions}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-xs uppercase">Failed</span>
                </div>
                <p className={`text-2xl font-bold ${stats.failed_transactions > 0 ? "text-status-danger-600 dark:text-status-danger-400" : "text-status-success-600 dark:text-status-success-400"}`}>
                  {stats.failed_transactions}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-xs uppercase">Last 24h</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {stats.last_24h_transactions}
                </p>
              </div>
            </div>
          )}

          {/* View Toggle */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
              {(["profiles", "transactions", "stats"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors capitalize ${
                    viewMode === mode
                      ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                      : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  }`}
                >
                  {mode === "profiles" && <Server className="w-4 h-4" />}
                  {mode === "transactions" && <FileText className="w-4 h-4" />}
                  {mode === "stats" && <BarChart3 className="w-4 h-4" />}
                  {mode}
                </button>
              ))}
            </div>
            {viewMode === "profiles" && (
              <button
                onClick={() => {
                  setEditingProfile(null)
                  setShowProfileModal(true)
                }}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
              >
                <Plus className="w-4 h-4" />
                Add Profile
              </button>
            )}
          </div>

          {/* Profiles */}
          {viewMode === "profiles" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : profiles.length === 0 ? (
                <div className="p-8 text-center">
                  <Server className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminEDISettings.noEdiProfilesConfigured')}</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {profiles.map((profile) => (
                    <div key={profile.id} className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {profile.vendor_name || `Vendor #${profile.vendor_id}`}
                            </span>
                            <StatusBadge variant={profile.is_enabled ? 'success' : 'neutral'}>
                              {profile.is_enabled ? "Enabled" : "Disabled"}
                            </StatusBadge>
                            {profile.is_test_mode && (
                              <StatusBadge variant="warning">Test Mode</StatusBadge>
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            <span>{profile.edi_standard.toUpperCase()}</span>
                            <span>{profile.transport_protocol.toUpperCase()}</span>
                            <span>{profile.transport_host || "No host"}</span>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            {profile.supports_orders && (
                              <span className="px-2 py-0.5 text-xs bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                                Orders
                              </span>
                            )}
                            {profile.supports_invoic && (
                              <span className="px-2 py-0.5 text-xs bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                                Invoices
                              </span>
                            )}
                            {profile.supports_desadv && (
                              <span className="px-2 py-0.5 text-xs bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                                Shipments
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleTestConnection(profile.vendor_id)}
                            disabled={isTesting === profile.vendor_id}
                            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg disabled:opacity-50"
                            title="Test Connection"
                          >
                            {isTesting === profile.vendor_id ? (
                              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                            ) : (
                              <TestTube2 className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => {
                              setEditingProfile(profile)
                              setProfileForm({
                                vendor_id: profile.vendor_id,
                                is_enabled: profile.is_enabled,
                                edi_standard: profile.edi_standard,
                                transport_protocol: profile.transport_protocol,
                                ...(profile.transport_host ? { transport_host: profile.transport_host } : {}),
                                ...(profile.transport_port ? { transport_port: profile.transport_port } : {}),
                                ...(profile.transport_username ? { transport_username: profile.transport_username } : {}),
                                supports_orders: profile.supports_orders,
                                supports_ordrsp: profile.supports_ordrsp,
                                supports_desadv: profile.supports_desadv,
                                supports_invoic: profile.supports_invoic,
                                max_retries: profile.max_retries,
                                retry_interval_minutes: profile.retry_interval_minutes,
                                auto_send_orders: profile.auto_send_orders,
                                auto_process_responses: profile.auto_process_responses,
                                auto_approve_invoices: profile.auto_approve_invoices,
                                invoice_tolerance_percent: profile.invoice_tolerance_percent,
                                is_test_mode: profile.is_test_mode,
                              })
                              setShowProfileModal(true)
                            }}
                            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(profile.id)}
                            className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg"
                            title="Delete profile"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Transactions */}
          {viewMode === "transactions" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              {transactions.length === 0 ? (
                <div className="p-8 text-center">
                  <FileText className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No transactions yet</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {transactions.map((tx) => (
                    <div key={tx.id} className="p-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {tx.message_type.toUpperCase()}
                          </span>
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {tx.direction === "outbound" ? "→" : "←"} {tx.vendor_name || "Unknown"}
                          </span>
                          <StatusBadge variant={getTxStatusVariant(tx.status)}>
                            {tx.status}
                          </StatusBadge>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          {tx.po_number && <span>PO: {tx.po_number}</span>}
                          <span>Created: {formatDate(tx.created_at)}</span>
                          {tx.sent_at && <span>Sent: {formatDate(tx.sent_at)}</span>}
                        </div>
                        {tx.last_error && (
                          <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1">{tx.last_error}</p>
                        )}
                      </div>
                      {tx.status === "failed" && (
                        <button
                          onClick={() => handleRetryTransaction(tx.id)}
                          className="px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          {viewMode === "stats" && stats && (
            <div className="space-y-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Transactions by Message Type
                </h3>
                <div className="space-y-2">
                  {Object.entries(stats.by_message_type).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-lsc-dark dark:text-lsc-cream uppercase">{type}</span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Transactions by Vendor
                </h3>
                <div className="space-y-2">
                  {Object.entries(stats.by_vendor).map(([vendor, count]) => (
                    <div key={vendor} className="flex items-center justify-between">
                      <span className="text-lsc-dark dark:text-lsc-cream">{vendor}</span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

      {/* Profile Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onKeyDown={(e) => { if (e.key === 'Escape') setShowProfileModal(false); }}>
          <div role="dialog" aria-modal="true" aria-labelledby="edi-modal-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-auto">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h3 id="edi-modal-title" className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editingProfile ? "Edit EDI Profile" : "Add EDI Profile"}
              </h3>
              <button onClick={() => setShowProfileModal(false)} aria-label={t('aria.adminEdiSettings.close', 'Close')} className="p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label htmlFor="edi-vendor" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Vendor <span className="text-status-danger-600" aria-hidden="true">*</span>
                </label>
                <select
                  id="edi-vendor"
                  value={profileForm.vendor_id || 0}
                  onChange={(e) => setProfileForm({ ...profileForm, vendor_id: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value={0}>Select vendor...</option>
                  {vendorsList.map(v => (
                    <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edi-standard" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    EDI Standard
                  </label>
                  <select
                    id="edi-standard"
                    value={profileForm.edi_standard}
                    onChange={(e) => setProfileForm({ ...profileForm, edi_standard: e.target.value as "edifact" | "x12" })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="edifact">EDIFACT</option>
                    <option value="x12">X12</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="edi-protocol" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Protocol
                  </label>
                  <select
                    id="edi-protocol"
                    value={profileForm.transport_protocol}
                    onChange={(e) => setProfileForm({ ...profileForm, transport_protocol: e.target.value as ediApi.TransportProtocol })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="sftp">SFTP</option>
                    <option value="ftp">FTP</option>
                    <option value="ftps">FTPS</option>
                    <option value="as2">AS2</option>
                    <option value="email">Email</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edi-host" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Host
                  </label>
                  <input
                    id="edi-host"
                    type="text"
                    value={profileForm.transport_host || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, transport_host: e.target.value })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="edi-port" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Port
                  </label>
                  <input
                    id="edi-port"
                    type="number"
                    value={profileForm.transport_port || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, ...(parseInt(e.target.value) ? { transport_port: parseInt(e.target.value) } : {}) })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={profileForm.is_enabled}
                    onChange={(e) => setProfileForm({ ...profileForm, is_enabled: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream">Enabled</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={profileForm.is_test_mode}
                    onChange={(e) => setProfileForm({ ...profileForm, is_test_mode: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream">Test Mode</span>
                </label>
              </div>
            </div>
            <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
              <button onClick={() => setShowProfileModal(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                Cancel
              </button>
              <button onClick={handleSaveProfile} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg">
                <Save className="w-4 h-4" />
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm !== null}
        title={t('admin.adminEDISettings.deleteThisEdiProfile')}
        message="This will permanently remove this EDI profile and its configuration. This action cannot be undone."
        confirmText="Yes, delete it"
        cancelText="Keep it"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirm !== null) handleDeleteProfile(deleteConfirm) }}
        onCancel={() => setDeleteConfirm(null)}
        loading={isDeleting}
      />
    </AdminShell>
  )
}
