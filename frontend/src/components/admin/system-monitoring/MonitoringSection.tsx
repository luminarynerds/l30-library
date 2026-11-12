/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Loader2,
  Database,
  Zap,
  Clock,
  Server,
  HardDrive,
  Bell,
  Settings,
  BarChart3,
  Eye,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { SectionShell } from '../ai-settings/SectionShell'

interface SystemHealth {
  status: string
  status_reason: string
  share_events_last_hour: number
  share_events_last_24h: number
  db_connection_active: number
  db_connection_idle: number
  db_slow_queries: number
  db_query_avg_time_ms: number
  error_count_last_hour: number
  error_count_last_24h: number
  error_rate_percent: number
  api_response_p50_ms: number
  api_response_p95_ms: number
  api_response_p99_ms: number
  cache_hit_rate_percent: number
  created_at: string
}

interface PrivacyAlert {
  id: number
  severity: string
  description: string
  detected_at: string
  is_acknowledged: boolean
  user_id: number
  alert_type: string
  change_count: number
}

interface ModerationAlert {
  id: number
  severity: string
  alert_type: string
  description: string
  pending_count: number
  overdue_count: number
  detected_at: string
  is_acknowledged: boolean
}

interface AlertThreshold {
  id: number
  name: string
  category: string
  description: string
  warning_level: number
  critical_level: number
  time_window_minutes: number
  enabled: boolean
}

const TABS = [
  { id: 'health', label: 'Health', icon: Activity },
  { id: 'privacy', label: 'Privacy', icon: Eye },
  { id: 'moderation', label: 'Moderation', icon: Bell },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const

interface MonitoringSectionProps {
  onBack: () => void
}

export function MonitoringSection({ onBack }: MonitoringSectionProps) {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [privacyAlerts, setPrivacyAlerts] = useState<PrivacyAlert[]>([])
  const [moderationAlerts, setModerationAlerts] = useState<ModerationAlert[]>([])
  const [thresholds, setThresholds] = useState<AlertThreshold[]>([])

  const fetchSystemHealth = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await fetchApi('/admin/monitoring/system-health')
      setSystemHealth(data.current)
    } catch (_error: unknown) {
      toast.error(t('admin.adminMonitoring.failedToLoadSystemHealth'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchPrivacyAlerts = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/admin/monitoring/privacy-alerts?hours=24')
      setPrivacyAlerts(data.alerts || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminMonitoring.failedToLoadPrivacyAlerts'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchModerationStatus = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/admin/monitoring/moderation-queue-status')
      setModerationAlerts(data.alerts || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminMonitoring.failedToLoadModerationStatus'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchThresholds = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/admin/monitoring/thresholds')
      setThresholds(data.thresholds || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminMonitoring.failedToLoadThresholds'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchSystemHealth()
      fetchPrivacyAlerts()
      fetchModerationStatus()
      fetchThresholds()
    }
  }, [token, isAuthenticated, fetchSystemHealth, fetchPrivacyAlerts, fetchModerationStatus, fetchThresholds])

  const handleAcknowledgePrivacyAlert = async (alertId: number) => {
    if (!token) return
    try {
      await fetchApi(`/admin/monitoring/privacy-alerts/${alertId}/acknowledge`, {
        method: 'POST',
        body: JSON.stringify({ notes: 'Acknowledged by admin' }),
      })
      toast.success(t('toast.adminLinkHealth.alertAcknowledged'))
      fetchPrivacyAlerts()
    } catch (_error: unknown) {
      toast.error(t('admin.adminMonitoring.failedToAcknowledgeAlert'))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return 'text-status-success-600 dark:text-status-success-400'
      case 'degraded': return 'text-status-warning-600 dark:text-status-warning-400'
      case 'unhealthy': return 'text-status-danger-600 dark:text-status-danger-400'
      default: return 'text-lsc-dark/70 dark:text-lsc-cream/70'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30'
      case 'high': return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      case 'medium': return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      default: return 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700'
    }
  }

  return (
    <SectionShell
      title="Performance Monitoring"
      description="Performance metrics, error rates, and alert tracking. Shows how the system is performing right now."
      tabs={[...TABS]}
      defaultTab="health"
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {(activeTab) => (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => { fetchSystemHealth(); fetchPrivacyAlerts(); fetchModerationStatus() }}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {activeTab === 'health' && (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : systemHealth ? (
                <>
                  <div className={`p-4 rounded-xl ${
                    systemHealth.status === 'healthy' ? 'bg-status-success-100 dark:bg-status-success-900/30'
                    : systemHealth.status === 'degraded' ? 'bg-status-warning-100 dark:bg-status-warning-900/30'
                    : 'bg-status-danger-100 dark:bg-status-danger-900/30'
                  }`}>
                    <div className="flex items-center gap-3">
                      {systemHealth.status === 'healthy' ? (
                        <CheckCircle className="w-6 h-6 text-status-success-600 dark:text-status-success-400" />
                      ) : (
                        <AlertTriangle className={`w-6 h-6 ${getStatusColor(systemHealth.status)}`} />
                      )}
                      <div>
                        <p className={`font-semibold ${getStatusColor(systemHealth.status)}`}>
                          System Status: {systemHealth.status.charAt(0).toUpperCase() + systemHealth.status.slice(1)}
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{systemHealth.status_reason}</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <Database className="w-4 h-4" /><span className="text-xs uppercase">DB Connections</span>
                      </div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{systemHealth.db_connection_active}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{systemHealth.db_connection_idle} idle</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <Zap className="w-4 h-4" /><span className="text-xs uppercase">API Response (p50)</span>
                      </div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{systemHealth.api_response_p50_ms.toFixed(0)}ms</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">p95: {systemHealth.api_response_p95_ms.toFixed(0)}ms</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <HardDrive className="w-4 h-4" /><span className="text-xs uppercase">Cache Hit Rate</span>
                      </div>
                      <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">{systemHealth.cache_hit_rate_percent.toFixed(1)}%</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <AlertTriangle className="w-4 h-4" /><span className="text-xs uppercase">Error Rate</span>
                      </div>
                      <p className={`text-2xl font-bold ${systemHealth.error_rate_percent > 1 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-status-success-600 dark:text-status-success-400'}`}>
                        {systemHealth.error_rate_percent.toFixed(2)}%
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{systemHealth.error_count_last_hour} errors/hour</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <Clock className="w-4 h-4" /><span className="text-xs uppercase">DB Query Avg</span>
                      </div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{systemHealth.db_query_avg_time_ms.toFixed(1)}ms</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{systemHealth.db_slow_queries} slow queries</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <Activity className="w-4 h-4" /><span className="text-xs uppercase">Share Events</span>
                      </div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{systemHealth.share_events_last_hour}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{systemHealth.share_events_last_24h} last 24h</p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <BarChart3 className="w-4 h-4" /><span className="text-xs uppercase">Errors (24h)</span>
                      </div>
                      <p className={`text-2xl font-bold ${systemHealth.error_count_last_24h > 100 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                        {systemHealth.error_count_last_24h}
                      </p>
                    </div>
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        <Server className="w-4 h-4" /><span className="text-xs uppercase">API p99</span>
                      </div>
                      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{systemHealth.api_response_p99_ms.toFixed(0)}ms</p>
                    </div>
                  </div>
                </>
              ) : null}
            </>
          )}

          {activeTab === 'privacy' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Privacy Alerts (Last 24 Hours)</h3>
              </div>
              {privacyAlerts.length === 0 ? (
                <div className="p-8 text-center">
                  <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No privacy alerts</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {privacyAlerts.map((alert) => (
                    <div key={alert.id} className="p-4 flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className={`w-5 h-5 mt-0.5 ${
                          alert.severity === 'critical' ? 'text-status-danger-500' : alert.severity === 'high' ? 'text-status-warning-500' : 'text-status-warning-500'
                        }`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>{alert.severity}</span>
                            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{alert.alert_type}</span>
                          </div>
                          <p className="text-sm text-lsc-dark dark:text-lsc-cream mt-1">{alert.description}</p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {alert.change_count} changes detected - {new Date(alert.detected_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      {!alert.is_acknowledged && (
                        <button
                          onClick={() => handleAcknowledgePrivacyAlert(alert.id)}
                          className="px-3 py-1.5 text-sm text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors whitespace-nowrap"
                        >
                          Acknowledge
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'moderation' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Moderation Queue Alerts</h3>
              </div>
              {moderationAlerts.length === 0 ? (
                <div className="p-8 text-center">
                  <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No moderation alerts</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {moderationAlerts.map((alert) => (
                    <div key={alert.id} className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>{alert.severity}</span>
                        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{alert.alert_type}</span>
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{alert.description}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span>{alert.pending_count} pending</span>
                        <span>{alert.overdue_count} overdue</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Alert Thresholds</h3>
              </div>
              {thresholds.length === 0 ? (
                <div className="p-8 text-center">
                  <Settings className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No thresholds configured</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {thresholds.map((threshold) => (
                    <div key={threshold.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{threshold.name}</p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{threshold.description}</p>
                        </div>
                        <div className={`px-2 py-1 text-xs font-medium rounded-full ${
                          threshold.enabled
                            ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
                            : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                        }`}>
                          {threshold.enabled ? 'Enabled' : 'Disabled'}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span>Warning: {threshold.warning_level}</span>
                        <span>Critical: {threshold.critical_level}</span>
                        <span>Window: {threshold.time_window_minutes} min</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </SectionShell>
  )
}
