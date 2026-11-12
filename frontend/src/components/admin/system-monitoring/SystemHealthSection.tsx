/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Activity,
  Database,
  Wifi,
  Clock,
  RefreshCw,
  AlertCircle,
  Zap,
  HardDrive,
  Radio,
  Pause,
  Play,
} from 'lucide-react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'
import { HealthChip, type HealthStatus } from '@/components/admin'
import { SectionShell } from '../ai-settings/SectionShell'

interface DependencyCheck {
  status: string
  response_time_ms?: number
  error?: string
  [key: string]: unknown
}

interface SchedulerJob {
  id: string
  name: string
  next_run_time: string | null
}

interface SchedulerCheck extends DependencyCheck {
  running?: boolean
  job_count?: number
  next_run_time?: string | null
  jobs?: SchedulerJob[]
}

interface WebSocketEndpoint {
  active_connections?: number
  unique_users?: number
  total_messages_sent?: number
  total_sessions?: number
  disconnected_sessions?: number
  total_queued_messages?: number
  running?: boolean
  channel_subscriptions?: Record<string, number>
  status?: string
  error?: string
}

interface WebSocketsCheck extends DependencyCheck {
  patron?: WebSocketEndpoint
  rfid?: WebSocketEndpoint
}

interface DashboardResponse {
  status: string
  service: string
  version: string
  environment: string
  timestamp: string
  uptime_seconds: number
  checks: {
    database: DependencyCheck
    redis: DependencyCheck
    scheduler: SchedulerCheck
    websockets: WebSocketsCheck
    cache?: DependencyCheck
  }
}

const toHealthStatus = (s: string): HealthStatus => {
  switch (s) {
    case 'healthy':
      return 'ok'
    case 'degraded':
    case 'disabled':
      return 'warn'
    case 'unhealthy':
    case 'error':
      return 'err'
    default:
      return 'unknown'
  }
}

const formatUptime = (seconds: number): string => {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}

const latencyColor = (ms: number | undefined): string => {
  if (ms === undefined) return 'text-lsc-dark/70 dark:text-lsc-cream/70'
  if (ms < 50) return 'text-status-success-600 dark:text-status-success-400'
  if (ms < 200) return 'text-status-warning-600 dark:text-status-warning-400'
  return 'text-status-danger-600 dark:text-status-danger-400'
}

function MetricRow({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
      <div className="text-right">
        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{value}</span>
        {sub && <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{sub}</span>}
      </div>
    </div>
  )
}

function DependencyCard({
  title,
  icon: Icon,
  check,
  children,
}: {
  title: string
  icon: React.ElementType
  check: DependencyCheck
  children?: React.ReactNode
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
        </div>
        <HealthChip
          status={toHealthStatus(check.status)}
          label={check.status.charAt(0).toUpperCase() + check.status.slice(1)}
        />
      </div>
      {check.response_time_ms !== undefined && (
        <MetricRow
          label="Response time"
          value={
            <span className={latencyColor(check.response_time_ms)}>
              {check.response_time_ms} ms
            </span>
          }
        />
      )}
      {check.error && (
        <div className="mt-2 p-2 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded text-xs text-status-danger-700 dark:text-status-danger-300 break-all">
          {check.error}
        </div>
      )}
      {children}
    </div>
  )
}

const TABS = [{ id: 'health', label: 'Health', icon: Activity }] as const

interface SystemHealthSectionProps {
  onBack: () => void
}

export function SystemHealthSection({ onBack }: SystemHealthSectionProps) {
  const { t } = useTranslation()
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    try {
      const resp = await api.get<DashboardResponse>(`${API_BASE}/health/dashboard`)
      setData(resp)
      setError(null)
      setLastRefreshed(new Date())
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load health data'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    if (autoRefresh) {
      const interval = setInterval(refresh, 15000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refresh])

  const overallGradient: Record<string, string> = {
    healthy: 'from-green-500 to-emerald-600',
    degraded: 'from-status-warning-500 to-status-warning-600',
    unhealthy: 'from-red-500 to-rose-600',
  }

  return (
    <SectionShell
      title="System Health"
      description="Server health and dependency checks. Shows whether the database, cache, scheduler, and websockets are all responding."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-8">
          <div
            className={`bg-gradient-to-r ${
              data ? overallGradient[data.status] || overallGradient.degraded : 'from-gray-500 to-gray-600'
            } text-white rounded-xl`}
          >
            <div className="px-4 sm:px-6 py-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-serif text-xl font-bold flex items-center gap-3">
                    <Activity className="w-6 h-6" aria-hidden="true" />
                    Dependency Health
                  </h3>
                  {data && (
                    <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-white/80">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" aria-hidden="true" />
                        Uptime: {formatUptime(data.uptime_seconds)}
                      </span>
                      <span>v{data.version}</span>
                      <span className="capitalize">{data.environment}</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {autoRefresh && (
                    <span className="text-xs text-white/70 hidden sm:block">
                      Auto-refreshes every 15s
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => setAutoRefresh(!autoRefresh)}
                    aria-label={autoRefresh ? 'Pause auto-refresh' : 'Resume auto-refresh'}
                    aria-pressed={autoRefresh}
                    className={`p-2 rounded-lg text-sm font-medium transition-colors ${
                      autoRefresh ? 'bg-lsc-white/90 text-lsc-dark dark:bg-earth-800/40 dark:text-lsc-cream hover:bg-lsc-white' : 'bg-lsc-white/20 hover:bg-lsc-white/30 text-white'
                    }`}
                  >
                    {autoRefresh
                      ? <Pause className="w-4 h-4" aria-hidden="true" />
                      : <Play className="w-4 h-4" aria-hidden="true" />
                    }
                  </button>
                  <button
                    type="button"
                    onClick={refresh}
                    disabled={loading}
                    aria-label="Refresh health data now"
                    className="p-2 rounded-lg bg-lsc-white/90 dark:bg-earth-800/40 hover:bg-lsc-white transition-colors disabled:opacity-50 text-lsc-dark dark:text-lsc-cream"
                  >
                    <RefreshCw className={`w-5 h-5 ${loading ? 'motion-safe:animate-spin' : ''}`} aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold text-status-danger-900 dark:text-status-danger-100">
                  {t('admin.adminSystemHealth.failedToLoadHealthData')}
                </p>
                <p className="text-sm text-status-danger-800 dark:text-status-danger-200 mt-1">{error}</p>
              </div>
            </div>
          )}

          {data && (
            <>
              <div className="flex items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <HealthChip status={toHealthStatus(data.status)} label={data.status} />
                <span>
                  Overall: <strong className="text-lsc-dark dark:text-lsc-cream">{data.status}</strong>
                </span>
                {lastRefreshed && (
                  <span className="ml-auto">
                    Last refreshed: {lastRefreshed.toLocaleTimeString()}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <DependencyCard title="PostgreSQL" icon={Database} check={data.checks.database}>
                  {!!data.checks.database.version && (
                    <MetricRow label="Version" value={String(data.checks.database.version)} />
                  )}
                  {data.checks.database.pool_size !== undefined && (
                    <>
                      <MetricRow label="Pool size" value={String(data.checks.database.pool_size)} />
                      <MetricRow
                        label="Checked out"
                        value={String(data.checks.database.checked_out)}
                        sub={`of ${Number(data.checks.database.pool_size) + Number(data.checks.database.overflow || 0)} max`}
                      />
                      <MetricRow label="Checked in" value={String(data.checks.database.checked_in)} />
                    </>
                  )}
                  {data.checks.database.active_connections !== undefined && (
                    <MetricRow label="Active connections (server)" value={String(data.checks.database.active_connections)} />
                  )}
                </DependencyCard>

                <DependencyCard title="Redis" icon={Zap} check={data.checks.redis}>
                  {!!data.checks.redis.version && (
                    <MetricRow label="Version" value={String(data.checks.redis.version)} />
                  )}
                  {data.checks.redis.connected_clients !== undefined && (
                    <MetricRow label="Connected clients" value={String(data.checks.redis.connected_clients)} />
                  )}
                  {!!data.checks.redis.used_memory_human && (
                    <MetricRow label="Memory usage" value={String(data.checks.redis.used_memory_human)} />
                  )}
                  {data.checks.redis.uptime_days !== undefined && (
                    <MetricRow label="Uptime" value={`${data.checks.redis.uptime_days} days`} />
                  )}
                </DependencyCard>

                <DependencyCard title="APScheduler" icon={Clock} check={data.checks.scheduler}>
                  {data.checks.scheduler.running !== undefined && (
                    <MetricRow label="Running" value={data.checks.scheduler.running ? 'Yes' : 'No'} />
                  )}
                  {data.checks.scheduler.job_count !== undefined && (
                    <MetricRow label="Registered jobs" value={String(data.checks.scheduler.job_count)} />
                  )}
                  {data.checks.scheduler.next_run_time && (
                    <MetricRow label="Next run" value={new Date(data.checks.scheduler.next_run_time).toLocaleString()} />
                  )}
                </DependencyCard>

                <DependencyCard title="WebSocket Managers" icon={Radio} check={data.checks.websockets}>
                  {data.checks.websockets.patron && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-1">Patron WS</p>
                      <MetricRow label="Active connections" value={String(data.checks.websockets.patron.active_connections ?? 0)} />
                      <MetricRow label="Unique users" value={String(data.checks.websockets.patron.unique_users ?? 0)} />
                      <MetricRow label="Messages sent" value={String(data.checks.websockets.patron.total_messages_sent ?? 0)} />
                    </div>
                  )}
                  {data.checks.websockets.rfid && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-1">RFID WS</p>
                      <MetricRow label="Active connections" value={String(data.checks.websockets.rfid.active_connections ?? 0)} />
                      <MetricRow label="Sessions" value={String(data.checks.websockets.rfid.total_sessions ?? 0)} />
                      <MetricRow label="Queued messages" value={String(data.checks.websockets.rfid.total_queued_messages ?? 0)} />
                    </div>
                  )}
                </DependencyCard>
              </div>

              {data.checks.cache && (
                <div>
                  <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <HardDrive className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                    Cache Status
                  </h2>
                  <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 shadow-sm">
                    <div className="flex items-center gap-2 mb-3">
                      <HealthChip
                        status={toHealthStatus(data.checks.cache.status)}
                        label={data.checks.cache.status.charAt(0).toUpperCase() + data.checks.cache.status.slice(1)}
                      />
                    </div>
                    {data.checks.cache.error && (
                      <div className="p-2 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded text-xs text-status-danger-700 dark:text-status-danger-300">
                        {data.checks.cache.error}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {data.checks.scheduler.jobs && data.checks.scheduler.jobs.length > 0 && (
                <div>
                  <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                    Scheduled Jobs ({data.checks.scheduler.jobs.length})
                  </h2>
                  <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm" aria-label={t('aria.adminSystemHealth.scheduledJobs')}>
                        <thead>
                          <tr className="border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-700/30">
                            <th scope="col" className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Job ID</th>
                            <th scope="col" className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Name</th>
                            <th scope="col" className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Next Run</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.checks.scheduler.jobs.map((job) => (
                            <tr key={job.id} className="border-b border-lsc-border dark:border-earth-700 last:border-0 hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20 transition-colors">
                              <td className="px-4 py-2 font-mono text-xs text-lsc-dark dark:text-lsc-cream">{job.id}</td>
                              <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{job.name}</td>
                              <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                                {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'Paused'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {data.checks.websockets.patron?.channel_subscriptions &&
                Object.keys(data.checks.websockets.patron.channel_subscriptions).length > 0 && (
                  <div>
                    <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                      <Wifi className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                      WebSocket Channel Subscriptions
                    </h2>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {Object.entries(data.checks.websockets.patron.channel_subscriptions).map(([ch, count]) => (
                        <div key={ch} className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-3 text-center">
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">{ch}</p>
                          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{count}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </>
          )}

          {loading && !data && (
            <div className="flex items-center justify-center h-64">
              <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
            </div>
          )}
        </div>
      )}
    </SectionShell>
  )
}
