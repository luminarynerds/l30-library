/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Database,
  RefreshCw,
  Loader2,
  Trash2,
  BarChart3,
  Clock,
  Zap,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Layers,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import ConfirmDialog from '@/components/ConfirmDialog'
import { SectionShell } from '../ai-settings/SectionShell'

interface RedisMemory {
  used: string
  used_bytes: number
  max_bytes: number
  fragmentation_ratio: number
}

interface RedisKeyspace {
  hits: number
  misses: number
  hit_rate_percent: number
}

interface RedisEviction {
  policy: string
  evicted_keys: number
  expired_keys: number
}

interface RedisStats {
  connected: boolean
  version: string
  uptime_days: number
  connected_clients: number
  memory: RedisMemory
  keyspace: RedisKeyspace
  eviction: RedisEviction
}

interface PrefixMetrics {
  hits: number
  misses: number
  errors: number
  hit_rate: number
}

interface LatencyMetrics {
  avg_get_seconds: number
  avg_set_seconds: number
  total_gets: number
  total_sets: number
}

interface TtlBuckets {
  '<1min': number
  '1-5min': number
  '5-30min': number
  '30min+': number
}

interface AppMetrics {
  per_prefix: Record<string, PrefixMetrics>
  latency: LatencyMetrics
  ttl_distribution: Record<string, TtlBuckets>
}

interface CacheMetricsResponse {
  redis_stats: RedisStats
  app_metrics: AppMetrics
}

interface CacheClearResponse {
  deleted: number
  pattern: string
}

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'prefixes', label: 'Prefixes', icon: Database },
  { id: 'latency', label: 'Latency', icon: Layers },
] as const

interface CacheMetricsSectionProps {
  onBack: () => void
}

export function CacheMetricsSection({ onBack }: CacheMetricsSectionProps) {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<CacheMetricsResponse | null>(null)
  const [clearingCache, setClearingCache] = useState<string | null>(null)
  const [resetMetrics, setResetMetrics] = useState(false)
  const [lastClearResult, setLastClearResult] = useState<CacheClearResponse | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmMessage, setConfirmMessage] = useState('')
  const [pendingClearPrefix, setPendingClearPrefix] = useState<string | undefined>(undefined)

  const fetchStats = useCallback(async () => {
    if (!isAuthenticated) return
    setIsLoading(true)
    try {
      const data = await api.get<CacheMetricsResponse>(`${API_BASE}/admin/cache/stats`)
      setStats(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminCacheMetrics.failedToLoadCacheMetrics'))
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, t])

  useEffect(() => {
    if (isAuthenticated) fetchStats()
  }, [isAuthenticated, fetchStats])

  const handleClearCache = async (prefix?: string) => {
    if (!isAuthenticated) return
    const msg = prefix
      ? `Clear ${prefix} cache? This will force data to be reloaded from the database.`
      : 'Clear ALL caches? This will temporarily increase database load.'
    setConfirmMessage(msg)
    setPendingClearPrefix(prefix)
    setConfirmOpen(true)
  }

  const executeClearCache = async (prefix?: string) => {
    if (!isAuthenticated) return
    setClearingCache(prefix || 'all')
    setLastClearResult(null)
    try {
      const params = new URLSearchParams()
      if (resetMetrics) params.append('reset_metrics', 'true')
      const url = `${API_BASE}/admin/cache/evict${params.toString() ? `?${params.toString()}` : ''}`
      const result = await api.post<CacheClearResponse>(url, { pattern: prefix || '*' })
      setLastClearResult(result)
      toast.success(`${result.deleted} key${result.deleted !== 1 ? 's' : ''} deleted (pattern: ${result.pattern})`)
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t('admin.adminCacheMetrics.failedToClearCache'))
    } finally {
      setClearingCache(null)
    }
  }

  const getHitRateColor = (rate: number): string => {
    if (rate >= 80) return 'text-status-success-600 dark:text-status-success-400'
    if (rate >= 50) return 'text-status-warning-600 dark:text-status-warning-400'
    return 'text-status-danger-600 dark:text-status-danger-400'
  }

  const getHitRateBgColor = (rate: number): string => {
    if (rate >= 80) return 'bg-status-success-500'
    if (rate >= 50) return 'bg-status-warning-500'
    return 'bg-status-danger-500'
  }

  const getTotalStats = () => {
    if (!stats) return { hits: 0, misses: 0, total: 0, hitRate: 0 }
    const hits = stats.redis_stats.keyspace.hits
    const misses = stats.redis_stats.keyspace.misses
    const total = hits + misses
    const hitRate = stats.redis_stats.keyspace.hit_rate_percent
    return { hits, misses, total, hitRate }
  }

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatSeconds = (seconds: number): string => {
    if (seconds < 0.001) return `${(seconds * 1_000_000).toFixed(0)} us`
    if (seconds < 1) return `${(seconds * 1000).toFixed(2)} ms`
    return `${seconds.toFixed(3)} s`
  }

  const totalStats = getTotalStats()

  return (
    <SectionShell
      title="Cache Metrics"
      description="Redis cache performance. Shows whether the cache is saving the database from extra work."
      tabs={[...TABS]}
      defaultTab="overview"
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={fetchStats}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'motion-safe:animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => handleClearCache()}
              disabled={clearingCache !== null}
              className="flex items-center gap-2 px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50"
            >
              {clearingCache === 'all' ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Clear All Caches
            </button>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={resetMetrics}
                onChange={(e) => setResetMetrics(e.target.checked)}
                className="w-4 h-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
              />
              <div>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">Reset metrics when clearing</span>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Also reset hit/miss counters to start fresh statistics</p>
              </div>
            </label>
          </div>

          {lastClearResult && (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-status-success-800 dark:text-status-success-200">
                    Cache cleared — pattern: <span className="font-mono">{lastClearResult.pattern}</span>
                  </p>
                  <p className="mt-1 text-sm text-status-success-700 dark:text-status-success-300">
                    {lastClearResult.deleted} Redis key{lastClearResult.deleted !== 1 ? 's' : ''} deleted
                  </p>
                </div>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : (
            <>
              {activeTab === 'overview' && stats && (
                <>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      {stats.redis_stats.connected ? <CheckCircle className="w-5 h-5 text-status-success-500" /> : <XCircle className="w-5 h-5 text-status-danger-500" />}
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">Redis {stats.redis_stats.connected ? 'Connected' : 'Disconnected'}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          v{stats.redis_stats.version} &middot; Uptime: {stats.redis_stats.uptime_days} day{stats.redis_stats.uptime_days !== 1 ? 's' : ''} &middot; {stats.redis_stats.connected_clients} client{stats.redis_stats.connected_clients !== 1 ? 's' : ''}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><Zap className="w-4 h-4" /><span className="text-xs uppercase">Hit Rate</span></div>
                      <p className={`text-2xl font-bold ${getHitRateColor(totalStats.hitRate)}`}>{totalStats.hitRate.toFixed(1)}%</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Keyspace hit rate</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><CheckCircle className="w-4 h-4 text-status-success-500" /><span className="text-xs uppercase">Keyspace Hits</span></div>
                      <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">{totalStats.hits.toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Served from cache</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><XCircle className="w-4 h-4 text-status-danger-500" /><span className="text-xs uppercase">Keyspace Misses</span></div>
                      <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">{totalStats.misses.toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Not found in cache</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><BarChart3 className="w-4 h-4" /><span className="text-xs uppercase">Total Lookups</span></div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{totalStats.total.toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Since last restart</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Memory</h3>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Used</span>
                          <span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{stats.redis_stats.memory.used}</span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Max</span>
                          <span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{formatBytes(stats.redis_stats.memory.max_bytes)}</span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Fragmentation Ratio</span>
                          <span className={`font-mono font-medium ${stats.redis_stats.memory.fragmentation_ratio > 1.5 ? 'text-status-warning-600 dark:text-status-warning-400' : 'text-status-success-600 dark:text-status-success-400'}`}>
                            {stats.redis_stats.memory.fragmentation_ratio.toFixed(2)}
                          </span>
                        </div>
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Usage</span>
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{((stats.redis_stats.memory.used_bytes / stats.redis_stats.memory.max_bytes) * 100).toFixed(1)}%</span>
                          </div>
                          <div className="bg-lsc-cream dark:bg-earth-600 rounded-full h-2">
                            <div className="h-2 rounded-full bg-lsc-rose" style={{ width: `${Math.min((stats.redis_stats.memory.used_bytes / stats.redis_stats.memory.max_bytes) * 100, 100)}%` }} />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Eviction</h3>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Policy</span>
                          <span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{stats.redis_stats.eviction.policy}</span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Evicted Keys</span>
                          <span className={`font-mono font-medium ${stats.redis_stats.eviction.evicted_keys > 0 ? 'text-status-warning-600 dark:text-status-warning-400' : 'text-status-success-600 dark:text-status-success-400'}`}>
                            {stats.redis_stats.eviction.evicted_keys.toLocaleString()}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Expired Keys</span>
                          <span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{stats.redis_stats.eviction.expired_keys.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Cache Health Analysis</h3>
                    <div className="space-y-3">
                      {totalStats.hitRate >= 70 ? (
                        <div className="flex items-start gap-3 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                          <TrendingUp className="w-5 h-5 text-status-success-600 dark:text-status-success-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-status-success-800 dark:text-status-success-300">Good cache performance</p>
                            <p className="text-sm text-status-success-700 dark:text-status-success-400">Redis is serving most requests from cache effectively.</p>
                          </div>
                        </div>
                      ) : totalStats.hitRate >= 40 ? (
                        <div className="flex items-start gap-3 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                          <TrendingDown className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-status-warning-800 dark:text-status-warning-300">Moderate cache performance</p>
                            <p className="text-sm text-status-warning-700 dark:text-status-warning-400">Consider reviewing TTL settings or cache invalidation patterns.</p>
                          </div>
                        </div>
                      ) : totalStats.total > 0 ? (
                        <div className="flex items-start gap-3 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                          <TrendingDown className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-status-danger-800 dark:text-status-danger-300">Low cache performance</p>
                            <p className="text-sm text-status-danger-700 dark:text-status-danger-400">Most requests are missing the cache. Review cache key patterns and TTL configuration.</p>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start gap-3 p-3 bg-earth-50 dark:bg-earth-900/20 rounded-lg">
                          <Database className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5" />
                          <div>
                            <p className="font-medium text-earth-800 dark:text-earth-300">No data yet</p>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Cache metrics will appear after requests are made.</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'prefixes' && stats && (
                <div className="space-y-6">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Cache Metrics by Prefix</h3>
                    {Object.keys(stats.app_metrics.per_prefix).length === 0 ? (
                      <div className="text-center py-8">
                        <Database className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminCacheMetrics.noCacheDataYet')}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Metrics will appear after cached requests are made</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {Object.entries(stats.app_metrics.per_prefix)
                          .sort((a, b) => (b[1].hits + b[1].misses) - (a[1].hits + a[1].misses))
                          .map(([prefix, data]) => {
                            const hitRatePercent = data.hit_rate * 100
                            const total = data.hits + data.misses
                            return (
                              <div key={prefix} className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                                <div className="flex items-center justify-between mb-2">
                                  <div>
                                    <p className="font-mono text-sm font-medium text-lsc-dark dark:text-lsc-cream">{prefix}</p>
                                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                                      {total.toLocaleString()} total requests
                                      {data.errors > 0 && <span className="ml-2 text-status-danger-500">({data.errors} errors)</span>}
                                    </p>
                                  </div>
                                  <div className="text-right">
                                    <p className={`text-lg font-bold ${getHitRateColor(hitRatePercent)}`}>{hitRatePercent.toFixed(1)}%</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 bg-lsc-cream dark:bg-earth-600 rounded-full h-2">
                                    <div className={`h-2 rounded-full ${getHitRateBgColor(hitRatePercent)}`} style={{ width: `${hitRatePercent}%` }} />
                                  </div>
                                </div>
                                <div className="flex items-center justify-between mt-2 text-xs">
                                  <span className="text-status-success-600 dark:text-status-success-400">{data.hits.toLocaleString()} hits</span>
                                  <span className="text-status-danger-600 dark:text-status-danger-400">{data.misses.toLocaleString()} misses</span>
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">TTL Distribution</h3>
                    {Object.keys(stats.app_metrics.ttl_distribution).length === 0 ? (
                      <div className="text-center py-8">
                        <Clock className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No TTL data available</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(stats.app_metrics.ttl_distribution).map(([prefix, buckets]) => (
                          <div key={prefix} className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                            <p className="font-mono text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">{prefix}</p>
                            <div className="grid grid-cols-4 gap-2 text-center">
                              {(['<1min', '1-5min', '5-30min', '30min+'] as const).map((bucket) => (
                                <div key={bucket} className="p-2 bg-lsc-white dark:bg-earth-600 rounded-lg">
                                  <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{buckets[bucket]}</p>
                                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{bucket}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'latency' && stats && (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><Clock className="w-4 h-4" /><span className="text-xs uppercase">Avg GET</span></div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{formatSeconds(stats.app_metrics.latency.avg_get_seconds)}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Average read latency</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><Clock className="w-4 h-4" /><span className="text-xs uppercase">Avg SET</span></div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{formatSeconds(stats.app_metrics.latency.avg_set_seconds)}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Average write latency</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><BarChart3 className="w-4 h-4" /><span className="text-xs uppercase">Total GETs</span></div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.app_metrics.latency.total_gets.toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Read operations</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"><BarChart3 className="w-4 h-4" /><span className="text-xs uppercase">Total SETs</span></div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.app_metrics.latency.total_sets.toLocaleString()}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Write operations</p>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Latency Details</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 bg-status-info-100 dark:bg-status-info-900/30 rounded-lg"><Zap className="w-5 h-5 text-status-info-600 dark:text-status-info-400" /></div>
                          <div><h4 className="font-medium text-lsc-dark dark:text-lsc-cream">Read Operations (GET)</h4><p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Cache lookups</p></div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between"><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Average Latency</span><span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{formatSeconds(stats.app_metrics.latency.avg_get_seconds)}</span></div>
                          <div className="flex items-center justify-between"><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Operations</span><span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{stats.app_metrics.latency.total_gets.toLocaleString()}</span></div>
                        </div>
                      </div>
                      <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700 rounded-lg">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 bg-category-100 dark:bg-category-900/30 rounded-lg"><Zap className="w-5 h-5 text-category-600 dark:text-category-400" /></div>
                          <div><h4 className="font-medium text-lsc-dark dark:text-lsc-cream">Write Operations (SET)</h4><p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Cache stores</p></div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between"><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Average Latency</span><span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{formatSeconds(stats.app_metrics.latency.avg_set_seconds)}</span></div>
                          <div className="flex items-center justify-between"><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Operations</span><span className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{stats.app_metrics.latency.total_sets.toLocaleString()}</span></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Latency Health</h3>
                    {stats.app_metrics.latency.avg_get_seconds < 0.005 ? (
                      <div className="flex items-start gap-3 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                        <TrendingUp className="w-5 h-5 text-status-success-600 dark:text-status-success-400 mt-0.5" />
                        <div><p className="font-medium text-status-success-800 dark:text-status-success-300">Excellent latency</p><p className="text-sm text-status-success-700 dark:text-status-success-400">Redis operations are completing in under 5ms on average.</p></div>
                      </div>
                    ) : stats.app_metrics.latency.avg_get_seconds < 0.05 ? (
                      <div className="flex items-start gap-3 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                        <TrendingDown className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 mt-0.5" />
                        <div><p className="font-medium text-status-warning-800 dark:text-status-warning-300">Acceptable latency</p><p className="text-sm text-status-warning-700 dark:text-status-warning-400">Average read latency is between 5-50ms. Monitor for increases.</p></div>
                      </div>
                    ) : (
                      <div className="flex items-start gap-3 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                        <TrendingDown className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 mt-0.5" />
                        <div><p className="font-medium text-status-danger-800 dark:text-status-danger-300">High latency</p><p className="text-sm text-status-danger-700 dark:text-status-danger-400">Average read latency exceeds 50ms. Check Redis server load and network conditions.</p></div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
          <ConfirmDialog isOpen={confirmOpen} title="Clear cache?" message={confirmMessage} confirmText="Clear" confirmVariant="warning" onConfirm={() => { executeClearCache(pendingClearPrefix); setConfirmOpen(false) }} onCancel={() => setConfirmOpen(false)} />
        </div>
      )}
    </SectionShell>
  )
}
