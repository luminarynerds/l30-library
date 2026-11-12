/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { useRequireRole } from '@/hooks/useRequireRole'
import { hasRole } from '@/auth/roleMatrix'
import { AdminShell } from '../components/shells/AdminShell'
import {
  Link2,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Settings,
  Search,
  Bell,
  History,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  getLinkHealthStats,
  getBrokenLinks,
  getDegradedLinks,
  setLinkMonitoring,
  checkSingleUrl,
  getUrlHistory,
  checkAllExternalResources,
  checkAllLessonResources,
  checkAllCatalogLinks,
  checkDigitalPlatforms,
  getOpenAlerts,
  acknowledgeAlert,
  resolveAlert,
  getLinkHealthConfig,
  updateLinkHealthConfig,
  cleanupOldData,
  getSourceLabel,
  type LinkHealthStats,
  type LinkHealthSummary,
  type LinkHealthCheck,
  type LinkHealthAlert,
  type LinkHealthConfig,
  type BulkCheckResponse,
  type PlatformStatus,
  type AlertSeverity,
} from "@/api/link-health-api"
import { useTranslation, useLanguage, formatRelativeTime } from "@/i18n"
import ConfirmDialog from "@/components/ConfirmDialog"
import { OverviewView } from "../components/link-health/OverviewView"
import { BrokenLinksView } from "../components/link-health/BrokenLinksView"
import { DegradedLinksView } from "../components/link-health/DegradedLinksView"
import { AlertsView } from "../components/link-health/AlertsView"
import { HistoryView } from "../components/link-health/HistoryView"
import { ConfigView } from "../components/link-health/ConfigView"
import { UrlCheckModal } from "../components/link-health/UrlCheckModal"
import { AlertModal } from "../components/link-health/AlertModal"
import { ConfigModal } from "../components/link-health/ConfigModal"

type ViewMode = "overview" | "broken" | "degraded" | "alerts" | "history" | "config"

export default function AdminLinkHealthPage(): React.ReactElement {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { token, isAuthenticated } = useAuth()
  const { user, authLoading, isAuthorized } = useRequireRole('adminOrStaff')
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [isRunningCheck, setIsRunningCheck] = useState(false)

  // Per-slice error flags (Enhancement 1)
  const [statsError, setStatsError] = useState(false)
  const [brokenLinksError, setBrokenLinksError] = useState(false)
  const [degradedLinksError, setDegradedLinksError] = useState(false)
  const [alertsError, setAlertsError] = useState(false)
  const [configError, setConfigError] = useState(false)

  const [stats, setStats] = useState<LinkHealthStats | null>(null)
  const [brokenLinks, setBrokenLinks] = useState<LinkHealthSummary[]>([])
  const [degradedLinks, setDegradedLinks] = useState<LinkHealthSummary[]>([])
  const [alerts, setAlerts] = useState<LinkHealthAlert[]>([])
  const [config, setConfig] = useState<LinkHealthConfig | null>(null)
  const [urlHistory, setUrlHistory] = useState<LinkHealthCheck[]>([])
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>("overview")
  const [sourceFilter, setSourceFilter] = useState<string>("")
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | "">("")
  const [searchUrl, setSearchUrl] = useState("")
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null)

  const [showUnmonitoredBroken, setShowUnmonitoredBroken] = useState(false)
  const [showUnmonitoredDegraded, setShowUnmonitoredDegraded] = useState(false)

  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showUrlCheckModal, setShowUrlCheckModal] = useState(false)
  const [showAlertModal, setShowAlertModal] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<LinkHealthAlert | null>(null)
  const [alertNotes, setAlertNotes] = useState("")

  const [configForm, setConfigForm] = useState<Partial<LinkHealthConfig>>({})

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const [urlToCheck, setUrlToCheck] = useState("")
  const [checkResult, setCheckResult] = useState<LinkHealthCheck | null>(null)

  const tabListRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthorized, navigate, t])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const data = await getLinkHealthStats(token)
      setStats(data)
      setStatsError(false)
    } catch (error: unknown) {
      setStatsError(true)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  const fetchBrokenLinks = useCallback(async () => {
    if (!token) return
    try {
      const data = await getBrokenLinks(token, {
        ...(sourceFilter ? { source: sourceFilter } : {}),
        limit: 100,
        includeUnmonitored: showUnmonitoredBroken,
      })
      setBrokenLinks(data)
      setBrokenLinksError(false)
    } catch (error: unknown) {
      setBrokenLinksError(true)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token, sourceFilter, showUnmonitoredBroken])

  const fetchDegradedLinks = useCallback(async () => {
    if (!token) return
    try {
      const data = await getDegradedLinks(token, {
        limit: 100,
        includeUnmonitored: showUnmonitoredDegraded,
      })
      setDegradedLinks(data)
      setDegradedLinksError(false)
    } catch (error: unknown) {
      setDegradedLinksError(true)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token, showUnmonitoredDegraded])

  const fetchAlerts = useCallback(async () => {
    if (!token) return
    try {
      const data = await getOpenAlerts(token, {
        ...(severityFilter ? { severity: severityFilter } : {}),
        limit: 100,
      })
      setAlerts(data)
      setAlertsError(false)
    } catch (error: unknown) {
      setAlertsError(true)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token, severityFilter])

  const fetchConfig = useCallback(async () => {
    if (!token) return
    try {
      const data = await getLinkHealthConfig(token)
      setConfig(data)
      setConfigForm(data)
      setConfigError(false)
    } catch (error: unknown) {
      setConfigError(true)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  const fetchUrlHistory = useCallback(async (url: string) => {
    if (!token) return
    try {
      const data = await getUrlHistory(token, url, { days: 30, limit: 50 })
      setUrlHistory(data)
      setSelectedUrl(url)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('admin.adminLinkHealth.failedToFetchUrlHistory'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchAllData = useCallback(async () => {
    setIsLoading(true)
    await Promise.all([
      fetchStats(),
      fetchBrokenLinks(),
      fetchDegradedLinks(),
      fetchAlerts(),
    ])
    setIsLoading(false)
  }, [fetchStats, fetchBrokenLinks, fetchDegradedLinks, fetchAlerts])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchAllData()
    }
  }, [token, isAuthenticated, fetchAllData])

  useEffect(() => {
    if (token && viewMode === "config" && !config) {
      fetchConfig()
    }
  }, [token, viewMode, config, fetchConfig])

  useEffect(() => {
    if (token && sourceFilter !== undefined) {
      fetchBrokenLinks()
    }
  }, [token, sourceFilter, fetchBrokenLinks])

  useEffect(() => {
    if (token && severityFilter !== undefined) {
      fetchAlerts()
    }
  }, [token, severityFilter, fetchAlerts])

  const handleMonitoringChange = useCallback(async (id: number, isMonitored: boolean) => {
    if (!token) return
    try {
      await setLinkMonitoring(id, !isMonitored, token)
      toast.success(isMonitored
        ? t('admin.adminLinkHealth.monitoringStoppedSuccess')
        : t('admin.adminLinkHealth.monitoringResumedSuccess')
      )
      await Promise.all([fetchBrokenLinks(), fetchDegradedLinks(), fetchStats()])
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('admin.adminLinkHealth.monitoringUpdateError'))
    }
  }, [token, t, fetchBrokenLinks, fetchDegradedLinks, fetchStats])

  const handleCheckUrl = async () => {
    if (!token || !urlToCheck) return
    setIsRunningCheck(true)
    try {
      const result = await checkSingleUrl(token, { url: urlToCheck })
      setCheckResult(result)
      toast.success(t('toast.adminLinkHealth.urlCheckCompleted'))
    } catch (_error: unknown) {
      toast.error(t('admin.adminLinkHealth.failedToCheckUrl'))
    } finally {
      setIsRunningCheck(false)
    }
  }

  const handleBulkCheck = async (type: "external" | "lesson" | "platforms" | "catalog") => {
    if (!token) return
    setIsRunningCheck(true)
    try {
      let result: BulkCheckResponse | PlatformStatus
      switch (type) {
        case "external":
          result = await checkAllExternalResources(token)
          toast.success(t('toast.adminLinkHealth.checkedTotalExternalResources', { total: (result as BulkCheckResponse).total }))
          break
        case "lesson":
          result = await checkAllLessonResources(token)
          toast.success(t('toast.adminLinkHealth.checkedTotalLessonResources', { total: (result as BulkCheckResponse).total }))
          break
        case "catalog":
          result = await checkAllCatalogLinks(token)
          toast.success(t('toast.adminLinkHealth.checkedTotalCatalogLinks', { total: (result as BulkCheckResponse).total }))
          break
        case "platforms":
          result = await checkDigitalPlatforms(token)
          setPlatformStatus(result as PlatformStatus)
          toast.success(t('admin.adminLinkHealth.digitalPlatformsCheckCompleted'))
          break
      }
      fetchAllData()
    } catch (_error: unknown) {
      toast.error(t('admin.adminLinkHealth.failedToRunBulkCheck'))
    } finally {
      setIsRunningCheck(false)
    }
  }

  const handleAcknowledgeAlert = async () => {
    if (!token || !selectedAlert) return
    try {
      await acknowledgeAlert(token, selectedAlert.id, alertNotes || undefined)
      toast.success(t('toast.adminLinkHealth.alertAcknowledged'))
      setShowAlertModal(false)
      setSelectedAlert(null)
      setAlertNotes("")
      fetchAlerts()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t('admin.adminLinkHealth.failedToAcknowledgeAlert'))
    }
  }

  const handleResolveAlert = async () => {
    if (!token || !selectedAlert) return
    try {
      await resolveAlert(token, selectedAlert.id, alertNotes || undefined)
      toast.success(t('toast.adminLinkHealth.alertResolved'))
      setShowAlertModal(false)
      setSelectedAlert(null)
      setAlertNotes("")
      fetchAlerts()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t('admin.adminLinkHealth.failedToResolveAlert'))
    }
  }

  const handleSaveConfig = async () => {
    if (!token) return
    try {
      const result = await updateLinkHealthConfig(token, configForm)
      setConfig(result.config)
      toast.success(t('toast.adminLinkHealth.configurationUpdated'))
      setShowConfigModal(false)
    } catch (_error: unknown) {
      toast.error(t('admin.adminLinkHealth.failedToUpdateConfiguration'))
    }
  }

  const handleCleanup = () => {
    if (!token) return
    setPendingAction(() => async () => {
      try {
        const result = await cleanupOldData(token)
        toast.success(t('toast.adminLinkHealth.cleanedUpDeletedchecksChecksAnd', { deletedchecks: result.deleted_checks, deletedsummaries: result.deleted_summaries }))
      } catch (_error: unknown) {
        toast.error(t('admin.adminLinkHealth.failedToCleanupOldData'))
      }
    })
    setConfirmOpen(true)
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "healthy":
        return <CheckCircle className="w-4 h-4 text-status-success-500" aria-label={status} />
      case "degraded":
        return <AlertTriangle className="w-4 h-4 text-status-warning-500" aria-label={status} />
      case "broken":
        return <XCircle className="w-4 h-4 text-status-danger-500" aria-label={status} />
      default:
        return <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-label={status} />
    }
  }

  /** Format last_checked_at from stats or a summary row — null-safe (Enhancement 4) */
  const formatLastChecked = (iso: string | null | undefined): string => {
    if (!iso) return t('admin.adminLinkHealth.neverChecked')
    return formatRelativeTime(iso, language)
  }

  const isAdmin = !authLoading && isAuthorized && hasRole(user, 'systemAdmin')

  const handleTabKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, currentIdx: number) => {
    const tabs = tabListRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
    if (!tabs) return
    let nextIdx: number | null = null
    if (e.key === "ArrowRight") nextIdx = (currentIdx + 1) % tabs.length
    else if (e.key === "ArrowLeft") nextIdx = (currentIdx - 1 + tabs.length) % tabs.length
    else if (e.key === "Home") nextIdx = 0
    else if (e.key === "End") nextIdx = tabs.length - 1
    if (nextIdx !== null) {
      const nextTab = tabs[nextIdx]
      if (nextTab) {
        e.preventDefault()
        nextTab.focus()
        nextTab.click()
      }
    }
  }

  if (authLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label={t("admin.adminLinkHealth.loadingLinks")}
        className="flex items-center justify-center min-h-[400px]"
      >
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
      </div>
    )
  }

  if (!isAuthorized) {
    return <></>
  }

  const tabItems = [
    { id: "overview" as const, label: "Overview", icon: Link2 },
    { id: "broken" as const, label: "Broken Links", icon: XCircle },
    { id: "degraded" as const, label: "Degraded", icon: AlertTriangle },
    { id: "alerts" as const, label: "Alerts", icon: Bell },
    { id: "history" as const, label: "History", icon: History },
    ...(isAdmin ? [{ id: "config" as const, label: "Config", icon: Settings }] : []),
  ]

  return (
    <AdminShell title="Link Health Monitoring">
      <div>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Link Health Monitoring
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Monitor and validate external links across the system
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowUrlCheckModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Search className="w-4 h-4" />
              Check URL
            </button>
            <button
              onClick={fetchAllData}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "motion-safe:animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Summary */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <Link2 className="w-4 h-4 text-earth-600" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Monitored</span>
              </div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {stats.total_monitored.toLocaleString()}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <XCircle className="w-4 h-4 text-status-danger-500" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Broken</span>
              </div>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                {stats.by_status["broken"] || 0}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4 text-status-warning-500" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Degraded</span>
              </div>
              <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                {stats.by_status["degraded"] || 0}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <Bell className="w-4 h-4 text-status-warning-500" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Open Alerts</span>
              </div>
              <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                {stats.open_alerts}
              </p>
            </div>
          </div>
        )}

        {/* Uptime and Status by Source */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Average Uptime</h3>
              <div className="flex items-center gap-4">
                <div className="relative w-20 h-20">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-earth-200 dark:text-earth-700"
                      stroke="currentColor"
                      strokeWidth="3"
                      fill="none"
                      d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className={stats.avg_uptime_percentage >= 95 ? "text-status-success-500" : stats.avg_uptime_percentage >= 80 ? "text-status-warning-500" : "text-status-danger-500"}
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeDasharray={`${stats.avg_uptime_percentage}, 100`}
                      strokeLinecap="round"
                      fill="none"
                      d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.avg_uptime_percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {stats.avg_uptime_percentage >= 95 ? "All systems operating normally" :
                     stats.avg_uptime_percentage >= 80 ? "Some links have issues" :
                     "Multiple links require attention"}
                  </p>
                  {/* Enhancement 4: last checked freshness on overview stats */}
                  <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">
                    <Clock className="w-3 h-3 inline mr-1" aria-hidden="true" />
                    {t('admin.adminLinkHealth.lastCheckedLabel', { time: formatLastChecked(stats.last_checked_at) })}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Links by Source</h3>
              <div className="space-y-2">
                {Object.entries(stats.by_source).map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between">
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {getSourceLabel(source)}
                    </span>
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* View Toggle — accessible tablist */}
        <div
          role="tablist"
          ref={tabListRef}
          className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit overflow-x-auto"
        >
          {tabItems.map((item, idx) => (
            <button
              key={item.id}
              role="tab"
              id={`tab-${item.id}`}
              aria-selected={viewMode === item.id}
              aria-controls={`tabpanel-${item.id}`}
              tabIndex={viewMode === item.id ? 0 : -1}
              onClick={() => setViewMode(item.id)}
              onKeyDown={(e) => handleTabKeyDown(e, idx)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${
                viewMode === item.id
                  ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div
            role="status"
            aria-live="polite"
            aria-label={t("admin.adminLinkHealth.loadingLinks")}
            className="flex items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        ) : (
          <>
            <div
              role="tabpanel"
              id="tabpanel-overview"
              aria-labelledby="tab-overview"
              hidden={viewMode !== "overview"}
            >
              {viewMode === "overview" && (
                <OverviewView
                  isAdmin={isAdmin}
                  isRunningCheck={isRunningCheck}
                  brokenLinks={brokenLinks}
                  alerts={alerts}
                  platformStatus={platformStatus}
                  hasError={brokenLinksError || alertsError || statsError}
                  onBulkCheck={handleBulkCheck}
                  onViewBroken={() => setViewMode("broken")}
                  onViewAlerts={() => setViewMode("alerts")}
                  onViewHistory={(url) => { fetchUrlHistory(url); setViewMode("history") }}
                  onManageAlert={(alert) => { setSelectedAlert(alert); setShowAlertModal(true) }}
                  onRetry={fetchAllData}
                  getStatusIcon={getStatusIcon}
                />
              )}
            </div>
            <div
              role="tabpanel"
              id="tabpanel-broken"
              aria-labelledby="tab-broken"
              hidden={viewMode !== "broken"}
            >
              {viewMode === "broken" && (
                <BrokenLinksView
                  brokenLinks={brokenLinks}
                  sourceFilter={sourceFilter}
                  hasError={brokenLinksError}
                  onSourceFilter={setSourceFilter}
                  onViewHistory={(url) => { fetchUrlHistory(url); setViewMode("history") }}
                  onRetry={fetchBrokenLinks}
                  onMonitoringChange={handleMonitoringChange}
                  showUnmonitored={showUnmonitoredBroken}
                  onShowUnmonitoredChange={setShowUnmonitoredBroken}
                  getStatusIcon={getStatusIcon}
                  formatLastChecked={formatLastChecked}
                />
              )}
            </div>
            <div
              role="tabpanel"
              id="tabpanel-degraded"
              aria-labelledby="tab-degraded"
              hidden={viewMode !== "degraded"}
            >
              {viewMode === "degraded" && (
                <DegradedLinksView
                  degradedLinks={degradedLinks}
                  hasError={degradedLinksError}
                  onViewHistory={(url) => { fetchUrlHistory(url); setViewMode("history") }}
                  onRetry={fetchDegradedLinks}
                  onMonitoringChange={handleMonitoringChange}
                  showUnmonitored={showUnmonitoredDegraded}
                  onShowUnmonitoredChange={setShowUnmonitoredDegraded}
                  getStatusIcon={getStatusIcon}
                />
              )}
            </div>
            <div
              role="tabpanel"
              id="tabpanel-alerts"
              aria-labelledby="tab-alerts"
              hidden={viewMode !== "alerts"}
            >
              {viewMode === "alerts" && (
                <AlertsView
                  alerts={alerts}
                  severityFilter={severityFilter}
                  hasError={alertsError}
                  onSeverityFilter={setSeverityFilter}
                  onManageAlert={(alert) => { setSelectedAlert(alert); setAlertNotes(""); setShowAlertModal(true) }}
                  onRetry={fetchAlerts}
                />
              )}
            </div>
            <div
              role="tabpanel"
              id="tabpanel-history"
              aria-labelledby="tab-history"
              hidden={viewMode !== "history"}
            >
              {viewMode === "history" && (
                <HistoryView
                  searchUrl={searchUrl}
                  selectedUrl={selectedUrl}
                  urlHistory={urlHistory}
                  onSearchChange={setSearchUrl}
                  onSearch={() => { if (searchUrl) fetchUrlHistory(searchUrl) }}
                  getStatusIcon={getStatusIcon}
                />
              )}
            </div>
            {isAdmin && (
              <div
                role="tabpanel"
                id="tabpanel-config"
                aria-labelledby="tab-config"
                hidden={viewMode !== "config"}
              >
                {viewMode === "config" && (
                  <ConfigView
                    config={config}
                    hasError={configError}
                    onEditConfig={() => setShowConfigModal(true)}
                    onCleanup={handleCleanup}
                    onRetry={fetchConfig}
                  />
                )}
              </div>
            )}
          </>
        )}

        {showUrlCheckModal && (
          <UrlCheckModal
            urlToCheck={urlToCheck}
            checkResult={checkResult}
            isRunningCheck={isRunningCheck}
            onUrlChange={setUrlToCheck}
            onCheck={handleCheckUrl}
            onClose={() => { setShowUrlCheckModal(false); setCheckResult(null); setUrlToCheck("") }}
            getStatusIcon={getStatusIcon}
          />
        )}

        {showAlertModal && selectedAlert && (
          <AlertModal
            alert={selectedAlert}
            alertNotes={alertNotes}
            onNotesChange={setAlertNotes}
            onAcknowledge={handleAcknowledgeAlert}
            onResolve={handleResolveAlert}
            onClose={() => { setShowAlertModal(false); setSelectedAlert(null) }}
          />
        )}

        {showConfigModal && config && (
          <ConfigModal
            config={config}
            configForm={configForm}
            onFormChange={setConfigForm}
            onSave={handleSaveConfig}
            onClose={() => setShowConfigModal(false)}
          />
        )}
      </div>
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Clean up old data?"
        message="This will delete old check history records."
        confirmText="Continue"
        confirmVariant="warning"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </AdminShell>
  )
}
