/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Activity, BarChart3, Server, Database, HardDrive, Shield, Clock, ShieldCheck,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { SystemStatusCard } from './SystemStatusCard'
import type { SystemStatus } from './SystemStatusBadge'
import { CarbonMetricsCard } from '../CarbonMetricsCard'

export type SectionId =
  | 'system-health'
  | 'monitoring'
  | 'api-status'
  | 'cache'
  | 'storage'
  | 'security'
  | 'scheduler'
  | 'virus-scan'

interface DashboardData {
  healthStatus: SystemStatus
  healthUptime: string
  healthVersion: string
  monitoringStatus: SystemStatus
  monitoringErrorRate: string
  monitoringP50: string
  monitoringCacheHit: string
  apiStatus: SystemStatus
  apiTotal: number
  cacheStatus: SystemStatus
  cacheHitRate: string
  cacheMemory: string
  cacheConnected: boolean
  storageBackend: string
  securityTokenExpiry: number
  securityLockoutAttempts: number
  securityPasswordMin: number
  schedulerEnabled: boolean
  schedulerTimezone: string
  schedulerRetry: boolean
  virusScanEnabled: boolean
  virusScanFailOnError: boolean
  virusScanConnection: string
}

const EMPTY: DashboardData = {
  healthStatus: 'unknown',
  healthUptime: '--',
  healthVersion: '--',
  monitoringStatus: 'unknown',
  monitoringErrorRate: '--',
  monitoringP50: '--',
  monitoringCacheHit: '--',
  apiStatus: 'unknown',
  apiTotal: 0,
  cacheStatus: 'unknown',
  cacheHitRate: '--',
  cacheMemory: '--',
  cacheConnected: false,
  storageBackend: '--',
  securityTokenExpiry: 0,
  securityLockoutAttempts: 0,
  securityPasswordMin: 0,
  schedulerEnabled: false,
  schedulerTimezone: '--',
  schedulerRetry: false,
  virusScanEnabled: false,
  virusScanFailOnError: false,
  virusScanConnection: '--',
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}

async function fetchJson(path: string) {
  return fetchApi(path)
}

interface SystemDashboardProps {
  onSelectSection: (id: SectionId) => void
}

export function SystemDashboard({ onSelectSection }: SystemDashboardProps) {
  const { token, isAuthenticated } = useAuth()
  const [data, setData] = useState<DashboardData>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token || !isAuthenticated) return
    const load = async () => {
      const d = { ...EMPTY }
      const results = await Promise.allSettled([
        fetchJson('/health/dashboard'),
        fetchJson('/admin/monitoring/system-health'),
        fetchJson('/api-status/summary'),
        fetchJson('/admin/cache/stats'),
        fetchJson('/admin/configuration/storage'),
        fetchJson('/admin/configuration/security'),
        fetchJson('/admin/configuration/scheduler'),
        fetchJson('/admin/configuration/virus_scan'),
      ])

      if (results[0].status === 'fulfilled') {
        const r = results[0].value as Record<string, unknown>
        const status = String(r.status || 'unknown')
        d.healthStatus = status === 'healthy' ? 'healthy' : status === 'degraded' ? 'degraded' : 'down'
        d.healthUptime = typeof r.uptime_seconds === 'number' ? formatUptime(r.uptime_seconds) : '--'
        d.healthVersion = r.version ? `v${r.version}` : '--'
      }

      if (results[1].status === 'fulfilled') {
        const r = results[1].value as Record<string, unknown>
        const current = r.current as Record<string, unknown> | undefined
        if (current) {
          const status = String(current.status || 'unknown')
          d.monitoringStatus = status === 'healthy' ? 'healthy' : status === 'degraded' ? 'degraded' : 'down'
          d.monitoringErrorRate = typeof current.error_rate_percent === 'number' ? `${(current.error_rate_percent as number).toFixed(1)}%` : '--'
          d.monitoringP50 = typeof current.api_response_p50_ms === 'number' ? `${(current.api_response_p50_ms as number).toFixed(0)}ms` : '--'
          d.monitoringCacheHit = typeof current.cache_hit_rate_percent === 'number' ? `${(current.cache_hit_rate_percent as number).toFixed(0)}%` : '--'
        }
      }

      if (results[2].status === 'fulfilled') {
        const r = results[2].value as Record<string, unknown>
        const status = String(r.status || 'unknown').toLowerCase()
        d.apiStatus = status === 'operational' || status === 'online' ? 'healthy' : status === 'degraded' ? 'degraded' : 'down'
        d.apiTotal = typeof r.monitored_endpoints === 'number' ? r.monitored_endpoints : 0
      }

      if (results[3].status === 'fulfilled') {
        const r = results[3].value as Record<string, unknown>
        const redis = r.redis_stats as Record<string, unknown> | undefined
        if (redis) {
          d.cacheConnected = redis.connected === true
          const keyspace = redis.keyspace as Record<string, unknown> | undefined
          const hitRate = keyspace?.hit_rate_percent
          if (typeof hitRate === 'number') {
            d.cacheHitRate = `${hitRate.toFixed(1)}%`
            if (!d.cacheConnected) d.cacheStatus = 'down'
            else if (hitRate >= 70) d.cacheStatus = 'healthy'
            else if (hitRate >= 40) d.cacheStatus = 'degraded'
            else d.cacheStatus = 'down'
          }
          const memory = redis.memory as Record<string, unknown> | undefined
          if (memory?.used) d.cacheMemory = String(memory.used)
        }
      }

      if (results[4].status === 'fulfilled') {
        const r = results[4].value as Record<string, unknown>
        const values = r.values as Record<string, unknown> | undefined
        d.storageBackend = values?.storage_backend === 's3' ? 'S3' : 'Local'
      }

      if (results[5].status === 'fulfilled') {
        const r = results[5].value as Record<string, unknown>
        const values = r.values as Record<string, unknown> | undefined
        if (values) {
          d.securityTokenExpiry = typeof values.access_token_expire_minutes === 'number' ? values.access_token_expire_minutes : 0
          d.securityLockoutAttempts = typeof values.max_login_attempts === 'number' ? values.max_login_attempts : 0
          d.securityPasswordMin = typeof values.password_min_length === 'number' ? values.password_min_length : 0
        }
      }

      if (results[6].status === 'fulfilled') {
        const r = results[6].value as Record<string, unknown>
        const values = r.values as Record<string, unknown> | undefined
        if (values) {
          d.schedulerEnabled = values.scheduler_enabled === true
          d.schedulerTimezone = typeof values.scheduler_timezone === 'string' ? values.scheduler_timezone : '--'
          d.schedulerRetry = values.scheduler_retry_enabled === true
        }
      }

      if (results[7].status === 'fulfilled') {
        const r = results[7].value as Record<string, unknown>
        const values = r.values as Record<string, unknown> | undefined
        if (values) {
          d.virusScanEnabled = values.virus_scan_enabled === true
          d.virusScanFailOnError = values.virus_scan_fail_on_error === true
          d.virusScanConnection = values.clamav_host ? 'TCP' : 'Socket'
        }
      }

      setData(d)
      setLoading(false)
    }
    void load()
  }, [token, isAuthenticated])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true" aria-label="Loading system dashboard">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-48 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        ))}
      </div>
    )
  }

  const cards: {
    id: SectionId
    icon: React.ReactNode
    title: string
    description: string
    status: SystemStatus
    statusLabel?: string | undefined
    metrics: { label: string; value: string }[]
  }[] = [
    {
      id: 'system-health',
      icon: <Activity className="w-5 h-5 text-lsc-rose" />,
      title: 'System Health',
      description: 'Server health and dependency checks. Shows whether the database, cache, scheduler, and websockets are all responding.',
      status: data.healthStatus,
      metrics: [
        { label: 'uptime', value: data.healthUptime },
        { label: 'version', value: data.healthVersion },
      ],
    },
    {
      id: 'monitoring',
      icon: <BarChart3 className="w-5 h-5 text-lsc-rose" />,
      title: 'Performance Monitoring',
      description: 'Performance metrics, error rates, and alert tracking. Shows how the system is performing right now.',
      status: data.monitoringStatus,
      metrics: [
        { label: 'error rate', value: data.monitoringErrorRate },
        { label: 'p50', value: data.monitoringP50 },
        { label: 'cache hit', value: data.monitoringCacheHit },
      ],
    },
    {
      id: 'api-status',
      icon: <Server className="w-5 h-5 text-lsc-rose" />,
      title: 'API Status',
      description: 'API endpoint health checks. Shows which endpoints are responding and how fast.',
      status: data.apiStatus,
      metrics: [
        { label: 'endpoints', value: String(data.apiTotal) },
      ],
    },
    {
      id: 'cache',
      icon: <Database className="w-5 h-5 text-lsc-rose" />,
      title: 'Cache Metrics',
      description: 'Redis cache performance. Shows whether the cache is saving the database from extra work.',
      status: data.cacheStatus,
      statusLabel: data.cacheConnected ? undefined : 'Disconnected',
      metrics: [
        { label: 'hit rate', value: data.cacheHitRate },
        { label: 'memory', value: data.cacheMemory },
      ],
    },
    {
      id: 'storage',
      icon: <HardDrive className="w-5 h-5 text-lsc-rose" />,
      title: 'Storage',
      description: 'Where uploaded files are stored. Choose between local disk or cloud storage (S3).',
      status: 'configured' as SystemStatus,
      statusLabel: data.storageBackend,
      metrics: [
        { label: 'backend', value: data.storageBackend },
      ],
    },
    {
      id: 'security',
      icon: <Shield className="w-5 h-5 text-lsc-rose" />,
      title: 'Security',
      description: 'Authentication and password rules. Controls how long sessions last and when accounts get locked.',
      status: 'configured' as SystemStatus,
      metrics: [
        ...(data.securityTokenExpiry > 0 ? [{ label: 'token expiry', value: `${data.securityTokenExpiry}m` }] : []),
        ...(data.securityLockoutAttempts > 0 ? [{ label: 'lockout after', value: `${data.securityLockoutAttempts} attempts` }] : []),
        ...(data.securityPasswordMin > 0 ? [{ label: 'min password', value: `${data.securityPasswordMin} chars` }] : []),
      ],
    },
    {
      id: 'scheduler',
      icon: <Clock className="w-5 h-5 text-lsc-rose" />,
      title: 'Scheduler',
      description: 'Background jobs that run automatically -- overdue notices, hold expiration, data cleanup. Controls when and how often they run.',
      status: data.schedulerEnabled ? 'healthy' : 'down',
      statusLabel: data.schedulerEnabled ? 'Enabled' : 'Disabled',
      metrics: [
        { label: 'timezone', value: data.schedulerTimezone },
        { label: 'retry', value: data.schedulerRetry ? 'On' : 'Off' },
      ],
    },
    {
      id: 'virus-scan',
      icon: <ShieldCheck className="w-5 h-5 text-lsc-rose" />,
      title: 'Virus Scanning',
      description: 'Scans uploaded files for malware using ClamAV before accepting them into the system.',
      status: data.virusScanEnabled ? (data.virusScanFailOnError ? 'healthy' : 'degraded') : 'down',
      statusLabel: data.virusScanEnabled ? 'Enabled' : 'Disabled',
      metrics: [
        { label: 'fail-on-error', value: data.virusScanFailOnError ? 'On' : 'Off' },
        { label: 'connection', value: data.virusScanConnection },
      ],
    },
  ]

  return (
    <>
      <nav aria-label="System monitoring settings">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cards.map((card) => (
            <SystemStatusCard
              key={card.id}
              id={card.id}
              icon={card.icon}
              title={card.title}
              description={card.description}
              status={card.status}
              statusLabel={card.statusLabel}
              metrics={card.metrics}
              onClick={onSelectSection as (id: string) => void}
            />
          ))}
        </div>
      </nav>
      <div className="mt-6">
        <CarbonMetricsCard />
      </div>
    </>
  )
}
