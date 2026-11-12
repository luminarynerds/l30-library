/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import {
  Activity,
  Server,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Database,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { SectionShell } from '../ai-settings/SectionShell'

interface MonitoredEndpoint {
  name: string
  path: string
  method: string
  status: 'online' | 'offline' | 'unknown' | 'error'
  response_time_ms: number | null
  error: string | null
  last_checked: string | null
}

interface EndpointsSummary {
  total_endpoints: number
  online: number
  offline: number
  unknown: number
  database_status: string
}

interface EndpointsResponse {
  timestamp: string
  summary: EndpointsSummary
  endpoints: MonitoredEndpoint[]
}

interface APIStatusSummary {
  status: string
  database: string
  timestamp: string
  monitored_endpoints: number
}

const TABS = [{ id: 'api', label: 'API Status', icon: Server }] as const

interface ApiStatusSectionProps {
  onBack: () => void
}

export function ApiStatusSection({ onBack }: ApiStatusSectionProps) {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [endpoints, setEndpoints] = useState<MonitoredEndpoint[]>([])
  const [endpointsSummary, setEndpointsSummary] = useState<EndpointsSummary | null>(null)
  const [summary, setSummary] = useState<APIStatusSummary | null>(null)

  const fetchEndpoints = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data: EndpointsResponse = await fetchApi('/api-status/endpoints')
      setEndpoints(data.endpoints || [])
      setEndpointsSummary(data.summary || null)
    } catch (_error: unknown) {
      toast.error(t('admin.adminAPIStatus.failedToLoadApiServices'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const fetchSummary = useCallback(async () => {
    if (!token) return
    try {
      const data: APIStatusSummary = await fetchApi('/api-status/summary')
      setSummary(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchEndpoints()
      fetchSummary()
    }
  }, [token, isAuthenticated, fetchEndpoints, fetchSummary])

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online': case 'operational': return 'text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30'
      case 'degraded': return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      case 'offline': case 'error': case 'outage': return 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30'
      case 'maintenance': return 'text-lsc-rose dark:text-lsc-rose-light bg-earth-100 dark:bg-earth-800/30'
      default: return 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online': case 'operational': return <CheckCircle className="w-4 h-4 text-status-success-500" />
      case 'degraded': return <AlertTriangle className="w-4 h-4 text-status-warning-500" />
      case 'offline': case 'error': case 'outage': return <XCircle className="w-4 h-4 text-status-danger-500" />
      default: return <Clock className="w-4 h-4 text-earth-600" />
    }
  }

  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'text-status-success-700 dark:text-status-success-400 bg-status-success-50 dark:bg-status-success-900/20'
      case 'POST': return 'text-status-info-700 dark:text-status-info-400 bg-status-info-50 dark:bg-status-info-900/20'
      case 'PUT': return 'text-status-warning-700 dark:text-status-warning-400 bg-status-warning-50 dark:bg-status-warning-900/20'
      case 'DELETE': return 'text-status-danger-700 dark:text-status-danger-400 bg-status-danger-50 dark:bg-status-danger-900/20'
      default: return 'text-earth-700 dark:text-earth-400 bg-earth-50 dark:bg-earth-900/20'
    }
  }

  const overallStatus = summary?.status || (endpointsSummary
    ? (endpointsSummary.offline > 0 ? 'degraded' : 'operational')
    : 'unknown')

  return (
    <SectionShell
      title="API Status"
      description="API endpoint health checks. Shows which endpoints are responding and how fast."
      tabs={[...TABS]}
      backLabel="Back to System Dashboard"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              onClick={() => { fetchEndpoints(); fetchSummary() }}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          <div className={`p-4 rounded-xl ${
            overallStatus === 'operational' ? 'bg-status-success-100 dark:bg-status-success-900/30'
            : overallStatus === 'degraded' ? 'bg-status-warning-100 dark:bg-status-warning-900/30'
            : 'bg-status-danger-100 dark:bg-status-danger-900/30'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(overallStatus)}
                <div>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream capitalize">System Status: {overallStatus}</p>
                  {endpointsSummary && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {endpointsSummary.online} online, {endpointsSummary.offline} offline, {endpointsSummary.unknown} unknown of {endpointsSummary.total_endpoints} endpoints
                    </p>
                  )}
                </div>
              </div>
              {summary && (
                <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                  <Database className="w-4 h-4" />
                  <span>DB: {summary.database}</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center gap-2">
              <Server className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Monitored Endpoints</h2>
              {endpointsSummary && (
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 ml-auto">{endpointsSummary.total_endpoints} total</span>
              )}
            </div>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : endpoints.length === 0 ? (
              <div className="p-8 text-center">
                <Activity className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No monitored endpoints found</p>
              </div>
            ) : (
              <div className="divide-y divide-lsc-border dark:divide-earth-700">
                {endpoints.map((endpoint, index) => (
                  <div key={index} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {getStatusIcon(endpoint.status)}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">{endpoint.name}</span>
                          <span className={`px-1.5 py-0.5 text-xs font-mono font-medium rounded ${getMethodColor(endpoint.method)}`}>{endpoint.method}</span>
                        </div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 font-mono">{endpoint.path}</p>
                        {endpoint.error && (
                          <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1">{endpoint.error}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {endpoint.response_time_ms != null && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{endpoint.response_time_ms}ms</span>
                      )}
                      <span className={`px-2 py-1 text-xs font-medium rounded-lg ${getStatusColor(endpoint.status)}`}>{endpoint.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {summary && (
            <p className="text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/60">
              Last checked: {new Date(summary.timestamp).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </SectionShell>
  )
}
