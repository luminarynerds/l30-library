/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { SyncStatus } from "@/constants/statuses"
import { AdminShell } from '../components/shells/AdminShell'
import {
  RefreshCw,
  ChevronLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Play,
  Eye,
  EyeOff,
  TrendingUp,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface SyncItem {
  id: number
  sync_source: string
  entity_type: string
  entity_id?: string | null
  status: string
  priority: number
  retry_count: number
  last_error?: string | null
  created_at: string
  processed_at?: string | null
}

export default function EmergencyOperationsDataSyncPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [syncItems, setSyncItems] = useState<SyncItem[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [statistics, setStatistics] = useState<any>(null)
  const [filterStatus, setFilterStatus] = useState<string | null>(null)
  const [filterEntityType, setFilterEntityType] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [expandedItem, setExpandedItem] = useState<number | null>(null)

  const loadSyncData = useCallback(async () => {
    try {
      setIsLoading(false) // After first load, just update quietly
      const [items, stats] = await Promise.all([
        emergencyOperationsAPI.dataSync.getPendingSyncItems(filterEntityType ?? undefined, 200),
        emergencyOperationsAPI.dataSync.getSyncStatistics(),
      ])

      setSyncItems(items)
      setStatistics(stats)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      if (!statistics) {
        toast.error(t('emergencyOperationsDataSync.failedToLoadSyncData'))
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterEntityType, statistics])


  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin", "manager"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    loadSyncData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      loadSyncData()
    }, 5000)

    return () => clearInterval(interval)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh])

  const handleCompleteSyncItem = async (itemId: number) => {
    try {
      setIsSyncing(true)
      await emergencyOperationsAPI.dataSync.markSyncComplete(itemId)
      toast.success(t('toast.emergencyOperationsDataSync.syncItemCompleted'))
      loadSyncData()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsDataSync.failedToCompleteSyncItem'))
    } finally {
      setIsSyncing(false)
    }
  }

  const handleManualSync = async () => {
    try {
      setIsSyncing(true)
      const pending = syncItems.filter((item) => item.status === SyncStatus.PENDING).slice(0, 10)

      for (const item of pending) {
        await emergencyOperationsAPI.dataSync.markSyncComplete(item.id)
      }

      toast.success(t('toast.emergencyOperationsDataSync.syncedLengthItems', { length: pending.length }))
      loadSyncData()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsDataSync.failedToCompleteSyncOperation'))
    } finally {
      setIsSyncing(false)
    }
  }

  if (authLoading || (isLoading && !statistics)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  const filteredItems = syncItems.filter((item) => {
    if (filterStatus && item.status !== filterStatus) return false
    if (filterEntityType && item.entity_type !== filterEntityType) return false
    return true
  })

  const entityTypes = [...new Set(syncItems.map((item) => item.entity_type))]
  const statusCounts = {
    pending: syncItems.filter((item) => item.status === SyncStatus.PENDING).length,
    synced: syncItems.filter((item) => item.status === "synced").length,
    failed: syncItems.filter((item) => item.status === SyncStatus.FAILED).length,
    processing: syncItems.filter((item) => item.status === SyncStatus.PROCESSING).length,
  }

  return (
    <AdminShell title="Data Synchronization Monitor" subtitle={t('emergencyOperationsDataSync.realTimeSyncStatusAnd')}>
      <div>
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/emergency-operations")} className="hover:text-lsc-rose">
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div></div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                autoRefresh
                  ? "bg-status-success-600 text-white hover:bg-status-success-700"
                  : "bg-earth-200 dark:bg-earth-600 text-earth-800 dark:text-earth-100 hover:bg-earth-300 dark:hover:bg-earth-500"
              }`}
            >
              {autoRefresh ? "Auto Refresh ON" : "Auto Refresh OFF"}
            </button>
            <button
              onClick={loadSyncData}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Progress Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Total Items</h3>
              <TrendingUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
            <div className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">{statistics?.total_items || 0}</div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-warning-200 dark:border-status-warning-800 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200">Pending</h3>
              <AlertCircle className="w-5 h-5 text-status-warning-600" />
            </div>
            <div className="text-3xl font-bold text-status-warning-600">{statusCounts.pending}</div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-success-200 dark:border-status-success-800 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200">Synced</h3>
              <CheckCircle2 className="w-5 h-5 text-status-success-600" />
            </div>
            <div className="text-3xl font-bold text-status-success-600">{statusCounts.synced}</div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-danger-200 dark:border-status-danger-800 p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-200">Failed</h3>
              <XCircle className="w-5 h-5 text-status-danger-600" />
            </div>
            <div className="text-3xl font-bold text-status-danger-600">{statusCounts.failed}</div>
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6 mb-8">
          <h3 className="font-serif font-bold text-lg mb-4">Overall Sync Progress</h3>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between mb-2">
                <span className="font-semibold">Completion Rate</span>
                <span className="text-sm font-bold">
                  {statistics ? ((statistics.synced / statistics.total_items) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-4 overflow-hidden">
                <div
                  className="bg-lsc-rose h-full transition-all duration-300"
                  style={{
                    width: `${
                      statistics ? ((statistics.synced / statistics.total_items) * 100).toFixed(1) : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            {statusCounts.pending > 0 && (
              <button
                onClick={handleManualSync}
                disabled={isSyncing}
                className="w-full mt-4 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSyncing ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Play className="w-4 h-4" />}
                Process Pending Items
              </button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-4 mb-6 flex gap-4 flex-wrap items-end">
          <div>
            <label className="block font-semibold mb-2 text-sm">Filter by Status</label>
            <select
              value={filterStatus || ""}
              onChange={(e) => setFilterStatus(e.target.value || null)}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="synced">Synced</option>
              <option value="failed">Failed</option>
              <option value="processing">Processing</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold mb-2 text-sm">{t('emergencyOperationsDataSync.filterByEntityType')}</label>
            <select
              value={filterEntityType || ""}
              onChange={(e) => setFilterEntityType(e.target.value || null)}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
            >
              <option value="">All Types</option>
              {entityTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              setFilterStatus(null)
              setFilterEntityType(null)
            }}
            className="px-3 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 rounded-lg transition-colors text-sm font-semibold"
          >
            Clear Filters
          </button>
        </div>

        {/* Sync Items List */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="p-4 bg-earth-100 dark:bg-earth-700 border-b-2 border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-bold text-lg">
              Sync Queue ({filteredItems.length} {filterStatus || filterEntityType ? "filtered" : "total"})
            </h3>
          </div>

          <div className="divide-y-2 divide-earth-200 dark:divide-earth-700">
            {filteredItems.length > 0 ? (
              filteredItems.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition-colors ${
                    item.status === "pending"
                      ? "border-l-4 border-status-warning-400"
                      : item.status === "synced"
                        ? "border-l-4 border-status-success-400"
                        : "border-l-4 border-status-danger-400"
                  }`}
                >
                  <div
                    className="cursor-pointer"
                    onClick={() => setExpandedItem(expandedItem === item.id ? null : item.id)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setExpandedItem(expandedItem === item.id ? null : item.id))(); } }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        {item.status === "pending" && (
                          <AlertCircle className="w-5 h-5 text-status-warning-600" />
                        )}
                        {item.status === "synced" && (
                          <CheckCircle2 className="w-5 h-5 text-status-success-600" />
                        )}
                        {item.status === "failed" && <XCircle className="w-5 h-5 text-status-danger-600" />}
                        {item.status === "processing" && (
                          <Loader2 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin" />
                        )}

                        <div className="flex-1">
                          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {item.entity_type}
                            {item.entity_id && ` - ${item.entity_id}`}
                          </div>
                          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            Source: {item.sync_source} • Priority: {item.priority}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <StatusBadge variant={
                          item.status === "pending" ? "warning"
                          : item.status === "synced" ? "success"
                          : "danger"
                        }>
                          {item.status.toUpperCase()}
                        </StatusBadge>

                        {expandedItem === item.id ? (
                          <EyeOff className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        ) : (
                          <Eye className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedItem === item.id && (
                    <div className="mt-4 pt-4 border-t-2 border-lsc-border dark:border-earth-700 space-y-3">
                      <div>
                        <label className="font-semibold text-lsc-dark dark:text-lsc-cream">Created:</label>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>

                      {item.processed_at && (
                        <div>
                          <label className="font-semibold text-lsc-dark dark:text-lsc-cream">Processed:</label>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {new Date(item.processed_at).toLocaleString()}
                          </p>
                        </div>
                      )}

                      <div>
                        <label className="font-semibold text-lsc-dark dark:text-lsc-cream">Retry Count:</label>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.retry_count}</p>
                      </div>

                      {item.last_error && (
                        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded p-3">
                          <label className="font-semibold text-status-danger-900 dark:text-status-danger-200">Last Error:</label>
                          <p className="text-sm text-status-danger-800 dark:text-status-danger-300 mt-1 font-mono break-all">
                            {item.last_error}
                          </p>
                        </div>
                      )}

                      {item.status === "pending" && (
                        <button
                          onClick={() => handleCompleteSyncItem(item.id)}
                          disabled={isSyncing}
                          className="w-full mt-3 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
                        >
                          {isSyncing ? (
                            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-4 h-4" />
                          )}
                          Process This Item
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                <RefreshCw className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
                <p className="font-semibold">{t('emergencyOperationsDataSync.noSyncItemsToDisplay')}</p>
                <p className="text-sm mt-1">{t('emergencyOperationsDataSync.allPendingItemsHaveBeen')}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminShell>
  )
}
