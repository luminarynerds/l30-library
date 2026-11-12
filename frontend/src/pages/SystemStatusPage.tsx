/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SystemStatusPage - Transparent system health dashboard
 *
 * Public page showing current system status, active issues,
 * estimated fix times, and recent recoveries.
 * Staff see additional details: health metrics, paper backups,
 * offline mode controls, and notification management.
 *
 * Philosophy: Honesty about tech problems reduces stress.
 * Don't blame staff for tech failures.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle,
  Clock,
  CloudOff,
  Database,
  FileText,
  Printer,
  Server,
  Shield,
  WifiOff,
  Users,
  Wifi,
  Zap,
} from 'lucide-react'
import {
  getSystemStatus,
  getRecentRecoveries,
  getDegradationInfo,
  getHealthMetrics,
  getStaffNotifications,
  acknowledgeNotification,
  getPaperBackups,
  getOfflineModeStatus,
  startOfflineMode,
  endOfflineMode,
  reportIssue,
  resolveIssue,
} from '@/api/system-status-api'
import type {
  SystemStatusLevel,
} from '@/api/system-status-api'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { fetchApi } from '@/api/fetchApi'

const STATUS_POLL_INTERVAL = 30_000

export default function SystemStatusPage() {
  const { user, token } = useAuth()
  const isStaff = user && ['staff', 'admin', 'super_admin'].includes(user.role)

  // Public data
  const { data: status, isLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: STATUS_POLL_INTERVAL,
  })

  const { data: recoveries } = useQuery({
    queryKey: ['system-recoveries'],
    queryFn: () => getRecentRecoveries(24),
    refetchInterval: 60_000,
  })

  const { data: degradation } = useQuery({
    queryKey: ['system-degradation'],
    queryFn: getDegradationInfo,
    refetchInterval: STATUS_POLL_INTERVAL,
  })

  const { data: offlineStatus } = useQuery({
    queryKey: ['offline-mode-status'],
    queryFn: getOfflineModeStatus,
    refetchInterval: STATUS_POLL_INTERVAL,
  })

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-8 bg-earth-200 dark:bg-earth-600 rounded w-1/3" />
          <div className="h-32 bg-earth-200 dark:bg-earth-600 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">System Status</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Transparent, real-time information about our systems.
        </p>
      </div>

      {/* Current Status Banner */}
      <StatusOverview status={status} offlineActive={offlineStatus?.offline_mode_active || false} />

      {/* Active Issues */}
      {status?.active_issues && status.active_issues.length > 0 && (
        <ActiveIssuesSection
          issues={status.active_issues}
          isStaff={!!isStaff}
          token={token || ''}
        />
      )}

      {/* Degradation Info */}
      {degradation?.degraded && (
        <DegradationSection degradation={degradation} />
      )}

      {/* Staff-only sections */}
      {isStaff && token && (
        <>
          <StaffNotificationsSection token={token} />
          <HealthMetricsSection token={token} />
          <WebSocketHealthSection />
          <OfflineModeSection token={token} offlineStatus={offlineStatus} />
          <PaperBackupsSection token={token} />
          <ReportIssueSection token={token} />
        </>
      )}

      {/* Recent Recoveries */}
      {recoveries?.recoveries && recoveries.recoveries.length > 0 && (
        <RecoveriesSection recoveries={recoveries.recoveries} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status Overview
// ---------------------------------------------------------------------------

function StatusOverview({
  status,
  offlineActive,
}: {
  status: ReturnType<typeof getSystemStatus> extends Promise<infer T> ? T | undefined : never
  offlineActive: boolean
}) {
  const config = getStatusConfig(status?.status || 'operational')

  return (
    <div className={`rounded-lg border-2 ${config.border} ${config.bg} p-6`}>
      <div className="flex items-center gap-3">
        <div className={`w-4 h-4 rounded-full ${config.dot}`} />
        <h2 className={`font-serif text-lg font-semibold ${config.text}`}>{config.label}</h2>
      </div>
      <p className={`mt-2 ${config.subtext}`}>{status?.message}</p>

      {offlineActive && (
        <div className="mt-3 flex items-center gap-2 text-status-warning-700 dark:text-status-warning-300 bg-status-warning-50 dark:bg-status-warning-900/20 rounded px-3 py-2">
          <CloudOff className="w-4 h-4" aria-hidden="true" />
          <span className="text-sm font-medium">
            Offline mode is active. Paper backup procedures are in use.
          </span>
        </div>
      )}
    </div>
  )
}

function getStatusConfig(level: SystemStatusLevel): { border: string; bg: string; dot: string; text: string; subtext: string; label: string } {
  const configs: Record<SystemStatusLevel, { border: string; bg: string; dot: string; text: string; subtext: string; label: string }> = {
    operational: { border: 'border-status-success-300 dark:border-status-success-700', bg: 'bg-status-success-50 dark:bg-status-success-900/20', dot: 'bg-status-success-500', text: 'text-status-success-800', subtext: 'text-status-success-700 dark:text-status-success-300', label: 'All Systems Operational' },
    slow: { border: 'border-status-warning-300 dark:border-status-warning-700', bg: 'bg-status-warning-50 dark:bg-status-warning-900/20', dot: 'bg-status-warning-500', text: 'text-status-warning-800', subtext: 'text-status-warning-700 dark:text-status-warning-300', label: 'Running Slow Today' },
    degraded: { border: 'border-status-warning-300 dark:border-status-warning-700', bg: 'bg-status-warning-50 dark:bg-status-warning-900/20', dot: 'bg-status-warning-500', text: 'text-status-warning-800 dark:text-status-warning-300', subtext: 'text-status-warning-700', label: 'Degraded Performance' },
    partial_outage: { border: 'border-status-warning-400', bg: 'bg-status-warning-50 dark:bg-status-warning-900/20', dot: 'bg-status-warning-600', text: 'text-status-warning-900 dark:text-status-warning-200', subtext: 'text-status-warning-700', label: 'Partial Outage' },
    major_outage: { border: 'border-status-danger-400', bg: 'bg-status-danger-50 dark:bg-status-danger-900/20', dot: 'bg-status-danger-600', text: 'text-status-danger-900', subtext: 'text-status-danger-700 dark:text-status-danger-300', label: 'Major Outage' },
    maintenance: { border: 'border-lsc-border dark:border-earth-600', bg: 'bg-earth-50 dark:bg-earth-800/20', dot: 'bg-earth-500', text: 'text-earth-800', subtext: 'text-lsc-rose dark:text-lsc-rose-light', label: 'Scheduled Maintenance' },
  }
  return configs[level] ?? configs.operational
}

// ---------------------------------------------------------------------------
// Active Issues
// ---------------------------------------------------------------------------

function ActiveIssuesSection({
  issues,
  isStaff,
  token,
}: {
  issues: Array<{
    id: number
    title: string
    component: string | null
    status: string
    description: string
    patron_message: string | null
    estimated_fix_time: string | null
    degraded_features: string[] | null
  }>
  isStaff: boolean
  token: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [resolvingId, setResolvingId] = useState<number | null>(null)
  const [notes, setNotes] = useState('')

  const resolveMutation = useMutation({
    mutationFn: async (issueId: number) =>
      resolveIssue(token, issueId, { resolution_notes: notes, send_recovery_alert: true }),
    onSuccess: () => {
      toast.success(t('systemStatus.issueResolvedRecoveryAlertSent'))
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
      queryClient.invalidateQueries({ queryKey: ['system-recoveries'] })
      setResolvingId(null)
      setNotes('')
    },
  })

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Active Issues</h2>
      <div className="space-y-3">
        {issues.map((issue) => (
          <div key={issue.id} className="border rounded-lg p-4 bg-lsc-white dark:bg-earth-800">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{issue.title}</h3>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {issue.patron_message || issue.description}
                </p>
                {issue.degraded_features && issue.degraded_features.length > 0 && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    Affected: {issue.degraded_features.join(', ')}
                  </p>
                )}
              </div>
              {issue.estimated_fix_time && (
                <div className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0">
                  <Clock className="w-4 h-4" aria-hidden="true" />
                  <span>
                    Est. fix:{' '}
                    {new Date(issue.estimated_fix_time).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              )}
            </div>

            {/* Staff: resolve button */}
            {isStaff && (
              <div className="mt-3 border-t pt-3">
                {resolvingId === issue.id ? (
                  <div className="space-y-2">
                    <textarea
                      className="w-full border rounded px-3 py-2 text-sm"
                      placeholder={t('placeholder.systemStatus.resolutionNotes')}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={2}
                    />
                    <div className="flex gap-2">
                      <button
                        className="px-3 py-1 bg-status-success-600 text-white text-sm rounded hover:bg-status-success-700"
                        onClick={() => resolveMutation.mutate(issue.id)}
                        disabled={!notes.trim()}
                      >
                        Resolve & Send "We're Back" Alert
                      </button>
                      <button
                        className="px-3 py-1 text-earth-600 text-sm hover:text-earth-800 dark:text-earth-100"
                        onClick={() => setResolvingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    className="text-sm text-status-success-600 hover:text-status-success-800 dark:text-status-success-300"
                    onClick={() => setResolvingId(issue.id)}
                  >
                    Mark as resolved
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Degradation Info
// ---------------------------------------------------------------------------

function DegradationSection({ degradation }: { degradation: { degraded_features?: string[] | null; available_features?: string[] | null; alternatives?: Record<string, string> | null } }) {
  const { t } = useTranslation();
  const availableFeatures = degradation.available_features ?? []
  const degradedFeatures = degradation.degraded_features ?? []
  const alternatives = degradation.alternatives ?? {}
  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('systemStatus.whatSWorkingWhatS')}</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {availableFeatures.length > 0 && (
          <div className="border rounded-lg p-4 bg-status-success-50 dark:bg-status-success-900/20">
            <h3 className="font-medium text-status-success-800 dark:text-status-success-300 flex items-center gap-2">
              <CheckCircle className="w-4 h-4" aria-hidden="true" /> Working
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-status-success-700 dark:text-status-success-300">
              {availableFeatures.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        )}
        {degradedFeatures.length > 0 && (
          <div className="border rounded-lg p-4 bg-status-warning-50 dark:bg-status-warning-900/20">
            <h3 className="font-medium text-status-warning-800 dark:text-status-warning-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" aria-hidden="true" /> Affected
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-status-warning-700 dark:text-status-warning-300">
              {degradedFeatures.map((f) => (
                <li key={f}>
                  {f}
                  {alternatives[f] && (
                    <span className="text-status-warning-600"> - Alternative: {alternatives[f]}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Staff Notifications
// ---------------------------------------------------------------------------

function StaffNotificationsSection({ token }: { token: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['staff-status-notifications'],
    queryFn: () => getStaffNotifications(token, false, 10),
    refetchInterval: 30_000,
  })

  const ackMutation = useMutation({
    mutationFn: async (id: number) => acknowledgeNotification(token, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['staff-status-notifications'] }),
    onError: () => toast.error(t('toast.systemStatus.failedToAcknowledgeAlert')),
  })

  if (!data?.notifications || data.notifications.length === 0) return null

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <Bell className="w-5 h-5" aria-hidden="true" /> Staff Alerts
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        You're notified first so you can help patrons proactively. Tech issues are never your fault.
      </p>
      <div className="space-y-2">
        {data.notifications.map((n) => (
          <div
            key={n.id}
            className={`border rounded-lg p-4 ${n.acknowledged ? 'bg-earth-50' : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'}`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{n.title}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{n.message}</p>
                {n.patron_talking_points && (
                  <div className="mt-2 bg-earth-50 dark:bg-earth-800/20 rounded px-3 py-2">
                    <p className="text-xs font-medium text-earth-800 dark:text-lsc-rose-light">{t('systemStatus.whatToTellPatrons')}</p>
                    <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-0.5">{n.patron_talking_points}</p>
                  </div>
                )}
                {n.workaround_instructions && (
                  <div className="mt-2 bg-status-warning-50 dark:bg-status-warning-900/20 rounded px-3 py-2">
                    <p className="text-xs font-medium text-status-warning-800 dark:text-status-warning-300">Workaround:</p>
                    <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mt-0.5">{n.workaround_instructions}</p>
                  </div>
                )}
              </div>
              {!n.acknowledged && (
                <button
                  className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light flex-shrink-0"
                  onClick={() => ackMutation.mutate(n.id)}
                >
                  Acknowledge
                </button>
              )}
            </div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              {n.created_at && new Date(n.created_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Health Metrics (Staff)
// ---------------------------------------------------------------------------

function HealthMetricsSection({ token }: { token: string }) {
  const { data } = useQuery({
    queryKey: ['system-health-metrics'],
    queryFn: () => getHealthMetrics(token, 5),
    refetchInterval: 30_000,
  })

  const latest = data?.metrics?.[0]
  if (!latest) return null

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <Activity className="w-5 h-5" aria-hidden="true" /> System Health Metrics
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Response Time (p95)"
          value={latest.response_time_p95_ms != null ? `${Math.round(latest.response_time_p95_ms)}ms` : 'N/A'}
          icon={<Zap className="w-4 h-4" />}
          status={latest.is_slow ? 'warning' : 'ok'}
        />
        <MetricCard
          label="DB Latency"
          value={latest.db_query_latency_ms != null ? `${Math.round(latest.db_query_latency_ms)}ms` : 'N/A'}
          icon={<Database className="w-4 h-4" />}
          status={latest.db_query_latency_ms && latest.db_query_latency_ms > 500 ? 'warning' : 'ok'}
        />
        <MetricCard
          label="Cache Hit Rate"
          value={latest.cache_hit_rate_percent != null ? `${Math.round(latest.cache_hit_rate_percent)}%` : 'N/A'}
          icon={<Server className="w-4 h-4" />}
          status={latest.cache_hit_rate_percent && latest.cache_hit_rate_percent < 80 ? 'warning' : 'ok'}
        />
        <MetricCard
          label="Error Rate"
          value={latest.error_rate_percent != null ? `${latest.error_rate_percent.toFixed(1)}%` : 'N/A'}
          icon={<AlertTriangle className="w-4 h-4" />}
          status={latest.error_rate_percent && latest.error_rate_percent > 5 ? 'warning' : 'ok'}
        />
      </div>
      {latest.is_slow && latest.slow_reason && (
        <p className="text-sm text-status-warning-600 mt-2">
          Slow: {latest.slow_reason}
        </p>
      )}
    </section>
  )
}

function MetricCard({
  label,
  value,
  icon,
  status,
}: {
  label: string
  value: string
  icon: React.ReactNode
  status: 'ok' | 'warning'
}) {
  return (
    <div className={`border rounded-lg p-3 ${status === 'warning' ? 'bg-status-warning-50 border-status-warning-200 dark:border-status-warning-800' : 'bg-lsc-white dark:bg-earth-800'}`}>
      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">{icon} {label}</div>
      <p className={`text-lg font-semibold mt-1 ${status === 'warning' ? 'text-status-warning-700' : 'text-lsc-dark dark:text-lsc-cream'}`}>
        {value}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// WebSocket Health (Staff)
// ---------------------------------------------------------------------------

function WebSocketHealthSection() {
  const { data } = useQuery({
    queryKey: ['ws-health'],
    queryFn: async () => {
      return fetchApi('/ws/patron/health') as Promise<{
        active_connections: number
        unique_users: number
        disconnected_sessions: number
        total_queued_messages: number
        total_messages_sent: number
        total_connections_accepted: number
        channel_subscriptions: Record<string, number>
      }>
    },
    refetchInterval: 10_000,
  })

  if (!data) return null

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <Wifi className="w-5 h-5" aria-hidden="true" /> WebSocket Connections
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Active Connections"
          value={String(data.active_connections)}
          icon={<Wifi className="w-4 h-4" />}
          status={data.active_connections > 900 ? 'warning' : 'ok'}
        />
        <MetricCard
          label="Unique Users"
          value={String(data.unique_users)}
          icon={<Users className="w-4 h-4" />}
          status="ok"
        />
        <MetricCard
          label="Disconnected Sessions"
          value={String(data.disconnected_sessions)}
          icon={<WifiOff className="w-4 h-4" />}
          status={data.disconnected_sessions > 50 ? 'warning' : 'ok'}
        />
        <MetricCard
          label="Queued Messages"
          value={String(data.total_queued_messages)}
          icon={<Bell className="w-4 h-4" />}
          status={data.total_queued_messages > 500 ? 'warning' : 'ok'}
        />
      </div>
      {Object.keys(data.channel_subscriptions).length > 0 && (
        <div className="mt-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex flex-wrap gap-2">
          {Object.entries(data.channel_subscriptions).map(([ch, count]) => (
            <span key={ch} className="rounded bg-earth-100 px-2 py-0.5 dark:bg-earth-700 dark:text-earth-300">
              {ch}: {count}
            </span>
          ))}
        </div>
      )}
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
        Total messages sent: {(data.total_messages_sent ?? 0).toLocaleString()} |
        Total connections accepted: {(data.total_connections_accepted ?? 0).toLocaleString()}
      </p>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Offline Mode (Staff)
// ---------------------------------------------------------------------------

function OfflineModeSection({
  token,
  offlineStatus,
}: {
  token: string
  offlineStatus: { offline_mode_active: boolean; session_id?: number; started_at?: string; reason?: string } | undefined
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')

  const startMutation = useMutation({
    mutationFn: async () => startOfflineMode(token, reason || undefined),
    onSuccess: () => {
      toast.success(t('systemStatus.offlineModeActivatedPaperBackup'))
      queryClient.invalidateQueries({ queryKey: ['offline-mode-status'] })
      setReason('')
    },
  })

  const endMutation = useMutation({
    mutationFn: async () => endOfflineMode(token, offlineStatus?.session_id || 0),
    onSuccess: (data) => {
      toast.success(t('toast.systemStatus.offlineModeEndedDurationminutesMinutes', { durationminutes: data.duration_minutes }))
      queryClient.invalidateQueries({ queryKey: ['offline-mode-status'] })
    },
  })

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <CloudOff className="w-5 h-5" aria-hidden="true" /> Offline Mode
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        When the system is down, activate offline mode. Staff continue serving patrons with paper forms.
        All data syncs when connectivity returns.
      </p>

      {offlineStatus?.offline_mode_active ? (
        <div className="border-2 border-status-warning-300 dark:border-status-warning-700 rounded-lg p-4 bg-status-warning-50 dark:bg-status-warning-900/20">
          <div className="flex items-center gap-2 text-status-warning-800 dark:text-status-warning-300 font-medium">
            <WifiOff className="w-4 h-4" aria-hidden="true" />
            Offline Mode Active
          </div>
          <p className="text-sm text-status-warning-700 dark:text-status-warning-300 mt-1">
            Started: {offlineStatus.started_at && new Date(offlineStatus.started_at).toLocaleString()}
            {offlineStatus.reason && ` - ${offlineStatus.reason}`}
          </p>
          <button
            className="mt-3 px-4 py-2 bg-status-success-600 text-white text-sm rounded hover:bg-status-success-700"
            onClick={() => endMutation.mutate()}
          >
            End Offline Mode - Systems Back Online
          </button>
        </div>
      ) : (
        <div className="border rounded-lg p-4 bg-lsc-white dark:bg-earth-800">
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border rounded px-3 py-2 text-sm"
              placeholder={t('systemStatus.reasonForGoingOfflineOptional')}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button
              className="px-4 py-2 bg-status-warning-600 text-white text-sm rounded hover:bg-status-warning-700"
              onClick={() => startMutation.mutate()}
            >
              Activate Offline Mode
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Paper Backups (Staff)
// ---------------------------------------------------------------------------

function PaperBackupsSection({ token }: { token: string }) {
  const { data } = useQuery({
    queryKey: ['paper-backups'],
    queryFn: () => getPaperBackups(token),
  })

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <FileText className="w-5 h-5" aria-hidden="true" /> Paper Backup Procedures
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        Ready-to-print forms and step-by-step manual procedures.
        Library service never stops, even during a complete outage.
      </p>

      {data?.procedures && data.procedures.length > 0 ? (
        <div className="grid md:grid-cols-2 gap-3">
          {data.procedures.map((proc) => (
            <div key={proc.id} className="border rounded-lg p-4 bg-lsc-white dark:bg-earth-800 hover:bg-earth-50 dark:hover:bg-earth-800">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{proc.title}</h3>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700 px-2 py-0.5 rounded">
                  {proc.backup_type.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{proc.description}</p>
              {proc.trigger_conditions && (
                <p className="text-xs text-status-warning-600 mt-1">Use when: {proc.trigger_conditions}</p>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light flex items-center gap-1"
                  onClick={() => window.print()}
                >
                  <Printer className="w-3 h-3" /> Print Form
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">
          No paper backup procedures configured yet. Admin can add them from the settings.
        </p>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Report Issue (Staff)
// ---------------------------------------------------------------------------

function ReportIssueSection({ token }: { token: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    status: 'slow' as SystemStatusLevel,
    title: '',
    description: '',
    component: '',
    estimated_fix_time: '',
  })

  const mutation = useMutation({
    mutationFn: async () =>
      reportIssue(token, {
        status: form.status,
        title: form.title,
        description: form.description,
        ...(form.component && { component: form.component }),
        ...(form.estimated_fix_time && { estimated_fix_time: form.estimated_fix_time }),
      }),
    onSuccess: () => {
      toast.success(t('systemStatus.issueReportedStaffHaveBeen'))
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
      queryClient.invalidateQueries({ queryKey: ['staff-status-notifications'] })
      setOpen(false)
      setForm({ status: 'slow', title: '', description: '', component: '', estimated_fix_time: '' })
    },
  })

  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <Shield className="w-5 h-5" aria-hidden="true" /> Report System Issue
      </h2>

      {!open ? (
        <button
          className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
          onClick={() => setOpen(true)}
        >
          Report a new issue
        </button>
      ) : (
        <div className="border rounded-lg p-4 bg-lsc-white dark:bg-earth-800 space-y-3">
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Severity</label>
              <select
                className="mt-1 w-full border rounded px-3 py-2 text-sm"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as SystemStatusLevel })}
              >
                <option value="slow">Slow Performance</option>
                <option value="degraded">Degraded</option>
                <option value="partial_outage">Partial Outage</option>
                <option value="major_outage">Major Outage</option>
                <option value="maintenance">Scheduled Maintenance</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Component</label>
              <select
                className="mt-1 w-full border rounded px-3 py-2 text-sm"
                value={form.component}
                onChange={(e) => setForm({ ...form, component: e.target.value })}
              >
                <option value="">General</option>
                <option value="database">Database</option>
                <option value="cache">Cache</option>
                <option value="search">Search</option>
                <option value="circulation">Circulation</option>
                <option value="catalog">Catalog</option>
                <option value="authentication">Authentication</option>
                <option value="printing">Printing</option>
                <option value="rfid">RFID</option>
                <option value="self_checkout">Self-Checkout</option>
                <option value="network">Network</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</label>
            <input
              type="text"
              className="mt-1 w-full border rounded px-3 py-2 text-sm"
              placeholder={t('systemStatus.briefDescriptionOfTheIssue')}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Description</label>
            <textarea
              className="mt-1 w-full border rounded px-3 py-2 text-sm"
              placeholder={t('systemStatus.whatSHappeningIncludeAny')}
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('systemStatus.estimatedFixTimeOptional')}</label>
            <input
              type="datetime-local"
              className="mt-1 w-full border rounded px-3 py-2 text-sm"
              value={form.estimated_fix_time}
              onChange={(e) => setForm({ ...form, estimated_fix_time: e.target.value })}
            />
          </div>

          <div className="flex gap-2">
            <button
              className="px-4 py-2 bg-status-danger-600 text-white text-sm rounded hover:bg-status-danger-700 disabled:opacity-50"
              onClick={() => mutation.mutate()}
              disabled={!form.title.trim() || !form.description.trim()}
            >
              Report Issue & Notify Staff
            </button>
            <button
              className="px-4 py-2 text-earth-600 text-sm hover:text-earth-800 dark:text-earth-100"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
          </div>

          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            A patron-friendly message will be automatically generated.
            Staff will receive talking points so they can help patrons without feeling blamed.
          </p>
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Recent Recoveries
// ---------------------------------------------------------------------------

function RecoveriesSection({ recoveries }: { recoveries: Array<{ id: number; title: string; component: string | null; resolved_at: string | null; resolution_notes: string | null; duration_minutes: number | null }> }) {
  return (
    <section>
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <CheckCircle className="w-5 h-5 text-status-success-600" aria-hidden="true" /> Recently Resolved
      </h2>
      <div className="space-y-2">
        {recoveries.map((r) => (
          <div key={r.id} className="border rounded-lg p-3 bg-status-success-50 dark:bg-status-success-900/20">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-status-success-800 dark:text-status-success-300">{r.title}</p>
              <p className="text-xs text-status-success-600">
                {r.duration_minutes != null && `Resolved in ${r.duration_minutes} min`}
              </p>
            </div>
            {r.resolution_notes && (
              <p className="text-xs text-status-success-700 dark:text-status-success-300 mt-1">{r.resolution_notes}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
