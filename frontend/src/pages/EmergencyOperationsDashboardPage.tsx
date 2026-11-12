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
  AlertTriangle,
  Shield,
  WifiOff,
  Phone,
  FileText,
  Zap,
  Building2,
  Package,
  Users,
  Activity,
  RefreshCw,
  ChevronRight,
  Loader2,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation } from '@/i18n'

interface DashboardStats {
  offline_status: boolean
  pending_sync_items: number
  paper_submissions: number
  active_closures: number
  active_cascades: number
  active_hubs: number
}

export default function EmergencyOperationsDashboardPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats>({
    offline_status: false,
    pending_sync_items: 0,
    paper_submissions: 0,
    active_closures: 0,
    active_cascades: 0,
    active_hubs: 0,
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [offlineStatus, setOfflineStatus] = useState<any>(null)

  const loadDashboardData = useCallback(async () => {
    try {
      setIsLoading(true)
      const [status, syncStats, papers, closures, cascades, hubs] = await Promise.all([
        emergencyOperationsAPI.offlineMode.getOfflineModeStatus(),
        emergencyOperationsAPI.dataSync.getSyncStatistics(),
        emergencyOperationsAPI.paperBackup.getPendingSubmissions(undefined, 999),
        emergencyOperationsAPI.buildingClosure.getActiveClosures(),
        emergencyOperationsAPI.emergencyContact.getActiveCascades(),
        emergencyOperationsAPI.communityResourceHub.getActiveHubs(),
      ])

      setOfflineStatus(status)
      setStats({
        offline_status: status.is_offline,
        pending_sync_items: syncStats.pending,
        paper_submissions: papers.length,
        active_closures: closures.length,
        active_cascades: cascades.length,
        active_hubs: hubs.length,
      })
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsDashboard.failedToLoadEmergencyOperations'))
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

    loadDashboardData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  const StatCard = ({
    icon: Icon,
    title,
    value,
    color,
    onClick,
  }: {
    icon: typeof AlertTriangle
    title: string
    value: number | string
    color: string
    onClick: () => void
  }) => (
    <button
      onClick={onClick}
      className={`p-6 rounded-lg border-2 hover:shadow-lg transition-all cursor-pointer ${color}`}
    >
      <div className="flex items-center justify-between mb-4">
        <Icon className="w-6 h-6" />
        <ChevronRight className="w-5 h-5 opacity-50" />
      </div>
      <div className="text-3xl font-bold mb-1">{value}</div>
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</div>
    </button>
  )

  return (
    <AdminShell title="Emergency Operations" subtitle={t('emergencyOperationsDashboard.crisisManagementAndContinuityPlanning')}>
        {/* Header */}
        <div className="mb-8">
        </div>

        {/* Offline Status Alert */}
        {stats.offline_status && (
          <div className="mb-6 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-200 dark:border-status-danger-800 rounded-lg flex items-start gap-3">
            <WifiOff className="w-6 h-6 text-status-danger-600 mt-1 flex-shrink-0" />
            <div>
              <h3 className="font-serif font-bold text-status-danger-900 dark:text-status-danger-200">System Offline</h3>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                Offline mode is active. Paper backup procedures are in effect.
              </p>
              {offlineStatus?.estimated_restoration && (
                <p className="text-sm text-status-danger-600 mt-1">
                  Estimated restoration: {new Date(offlineStatus.estimated_restoration).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          {!stats.offline_status && (
            <button
              onClick={() => navigate("/emergency-operations/offline-mode")}
              className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-200 dark:border-status-warning-800 rounded-lg hover:bg-status-warning-100 transition-colors text-left"
            >
              <div className="flex items-center gap-3 mb-2">
                <WifiOff className="w-5 h-5 text-status-warning-700 dark:text-status-warning-300" />
                <span className="font-bold text-status-warning-900 dark:text-status-warning-200">Activate Offline Mode</span>
              </div>
              <p className="text-sm text-status-warning-700 dark:text-status-warning-300">{t('emergencyOperationsDashboard.prepareForSystemOutage')}</p>
            </button>
          )}

          {stats.offline_status && (
            <button
              onClick={() => navigate("/emergency-operations/data-sync")}
              className="p-4 bg-earth-50 dark:bg-earth-800/20 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-100 transition-colors text-left"
            >
              <div className="flex items-center gap-3 mb-2">
                <RefreshCw className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                <span className="font-bold text-earth-900 dark:text-lsc-rose-light/80">Monitor Data Sync</span>
              </div>
              <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">{stats.pending_sync_items} items pending</p>
            </button>
          )}

          <button
            onClick={() => navigate("/emergency-operations/cascades")}
            className="p-4 bg-category-50 dark:bg-category-900/20 border-2 border-category-200 dark:border-category-800 rounded-lg hover:bg-category-100 transition-colors text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Phone className="w-5 h-5 text-category-700 dark:text-category-300" />
              <span className="font-bold text-category-900 dark:text-category-200">Emergency Contacts</span>
            </div>
            <p className="text-sm text-category-700 dark:text-category-300">{stats.active_cascades} active cascades</p>
          </button>

          <button
            onClick={() => navigate("/emergency-operations/closures")}
            className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-200 dark:border-status-danger-800 rounded-lg hover:bg-status-danger-100 transition-colors text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Building2 className="w-5 h-5 text-status-danger-700 dark:text-status-danger-300" />
              <span className="font-bold text-status-danger-900 dark:text-status-danger-200">Building Closures</span>
            </div>
            <p className="text-sm text-status-danger-700 dark:text-status-danger-300">{stats.active_closures} active closures</p>
          </button>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <StatCard
            icon={FileText}
            title="Paper Submissions"
            value={stats.paper_submissions}
            color="bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800"
            onClick={() => navigate("/emergency-operations/paper-backup")}
          />

          <StatCard
            icon={Zap}
            title="Sync Items Pending"
            value={stats.pending_sync_items}
            color="bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800"
            onClick={() => navigate("/emergency-operations/data-sync")}
          />

          <StatCard
            icon={Package}
            title="Recovery Projects"
            value={stats.active_closures}
            color="bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800"
            onClick={() => navigate("/emergency-operations/recovery")}
          />

          <StatCard
            icon={Users}
            title="Active Contact Cascades"
            value={stats.active_cascades}
            color="bg-lsc-rose/10 dark:bg-lsc-rose/20 border-lsc-rose/30 dark:border-lsc-rose/30"
            onClick={() => navigate("/emergency-operations/cascades")}
          />

          <StatCard
            icon={Shield}
            title="Community Hubs Active"
            value={stats.active_hubs}
            color="bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800"
            onClick={() => navigate("/emergency-operations/community-hubs")}
          />

          <StatCard
            icon={AlertTriangle}
            title="System Status"
            value={stats.offline_status ? "OFFLINE" : "ONLINE"}
            color={stats.offline_status ? "bg-status-danger-50 border-status-danger-200" : "bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800"}
            onClick={() => navigate("/emergency-operations/status")}
          />
        </div>

        {/* Management Sections */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Critical Actions */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-xl font-bold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-status-danger-600" />
              Critical Actions
            </h2>
            <div className="space-y-3">
              <button
                onClick={() => navigate("/emergency-operations/closures")}
                className="w-full p-3 text-left bg-status-danger-50 dark:bg-status-danger-900/20 hover:bg-status-danger-100 border border-status-danger-200 dark:border-status-danger-800 rounded-lg transition-colors"
              >
                <div className="font-semibold text-status-danger-900 dark:text-status-danger-200">Announce Building Closure</div>
                <div className="text-sm text-status-danger-700 dark:text-status-danger-300">{t('emergencyOperationsDashboard.notifyAllPatronsAndStaff')}</div>
              </button>
              <button
                onClick={() => navigate("/emergency-operations/cascades")}
                className="w-full p-3 text-left bg-category-50 dark:bg-category-900/20 hover:bg-category-100 border border-category-200 dark:border-category-800 rounded-lg transition-colors"
              >
                <div className="font-semibold text-category-900 dark:text-category-200">Execute Contact Cascade</div>
                <div className="text-sm text-category-700 dark:text-category-300">Notify emergency contacts</div>
              </button>
              <button
                onClick={() => navigate("/emergency-operations/community-hubs")}
                className="w-full p-3 text-left bg-status-success-50 dark:bg-status-success-900/20 hover:bg-status-success-100 border border-status-success-200 dark:border-status-success-800 rounded-lg transition-colors"
              >
                <div className="font-semibold text-status-success-900 dark:text-status-success-200">Activate Resource Hub</div>
                <div className="text-sm text-status-success-700 dark:text-status-success-300">Provide community services</div>
              </button>
            </div>
          </div>

          {/* Recovery & Assessment */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-xl font-bold mb-4 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              Recovery & Assessment
            </h2>
            <div className="space-y-3">
              <button
                onClick={() => navigate("/emergency-operations/recovery")}
                className="w-full p-3 text-left bg-status-warning-50 dark:bg-status-warning-900/20 hover:bg-status-warning-100 border border-status-warning-200 dark:border-status-warning-800 rounded-lg transition-colors"
              >
                <div className="font-semibold text-status-warning-900 dark:text-status-warning-200">Collection Recovery Projects</div>
                <div className="text-sm text-status-warning-700 dark:text-status-warning-300">{t('emergencyOperationsDashboard.trackDamagedItemsAndRepairs')}</div>
              </button>
              <button
                onClick={() => navigate("/emergency-operations/assessment")}
                className="w-full p-3 text-left bg-cyan-50 dark:bg-cyan-900/20 hover:bg-cyan-100 border border-cyan-200 dark:border-cyan-800 rounded-lg transition-colors"
              >
                <div className="font-semibold text-cyan-900 dark:text-cyan-200">Post-Disaster Assessment</div>
                <div className="text-sm text-cyan-700 dark:text-cyan-300">{t('emergencyOperationsDashboard.documentDamageAndRecoveryNeeds')}</div>
              </button>
              <button
                onClick={() => navigate("/emergency-operations/insurance")}
                className="w-full p-3 text-left bg-lsc-rose/10 dark:bg-lsc-rose/20 hover:bg-lsc-rose/10 border border-lsc-rose/30 dark:border-lsc-rose/30 rounded-lg transition-colors"
              >
                <div className="font-semibold text-lsc-rose dark:text-lsc-rose-light">Insurance Documentation</div>
                <div className="text-sm text-lsc-rose dark:text-lsc-rose-light">{t('emergencyOperationsDashboard.manageClaimsAndRecovery')}</div>
              </button>
            </div>
          </div>
        </div>

        {/* Service Continuity Info */}
        <div className="mt-6 bg-earth-50 dark:bg-earth-800/20 border-2 border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <h3 className="font-serif font-bold text-earth-900 dark:text-lsc-rose-light/80 mb-3 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Service Continuity Status
          </h3>
          <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
            All critical services have continuity plans in place. Recovery Time Objectives (RTO) have been
            established for each service. Paper backup procedures are available for offline operations.
          </p>
        </div>

    </AdminShell>
  )
}
