/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '@/api/types';
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Server,
  Globe,
  BookOpen,
  HelpCircle,
  ArrowRight,
  Calendar,
  Info
} from 'lucide-react'
import api from '@/lib/api-client'
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

type ServiceStatus = 'operational' | 'degraded' | 'outage' | 'maintenance' | 'unknown'

interface LiveService {
  id: string
  name: string
  description: string
  status: ServiceStatus
  uptime_24h: number | null
  ping_ms: number | null
  last_checked: string | null
}

interface Incident {
  id: string
  title: string
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved'
  severity: 'minor' | 'major' | 'critical'
  startedAt: Date
  description: string
  estimatedFixTime?: string | null
  patronMessage?: string | null
}

const SERVICE_ICONS: Record<string, React.ElementType> = {
  library_site: Globe,
  digital: BookOpen,
  infrastructure: Server,
}

const STATUS_ORDER: ServiceStatus[] = ['outage', 'maintenance', 'degraded', 'operational', 'unknown']

function worstStatus(statuses: ServiceStatus[]): ServiceStatus {
  for (const level of STATUS_ORDER) {
    if (statuses.includes(level)) return level
  }
  return 'operational'
}

function getStatusColor(status: ServiceStatus): string {
  switch (status) {
    case 'operational':
      return 'text-status-success-600 dark:text-status-success-400'
    case 'degraded':
      return 'text-status-warning-600 dark:text-status-warning-400'
    case 'outage':
      return 'text-status-danger-600 dark:text-status-danger-400'
    case 'maintenance':
      return 'text-lsc-rose dark:text-lsc-rose-light'
    default:
      return 'text-lsc-dark/60 dark:text-lsc-cream/60'
  }
}

function getStatusBgColor(status: ServiceStatus): string {
  switch (status) {
    case 'operational':
      return 'bg-status-success-100 dark:bg-status-success-900/30'
    case 'degraded':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30'
    case 'outage':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30'
    case 'maintenance':
      return 'bg-earth-100 dark:bg-earth-800/30'
    default:
      return 'bg-earth-100 dark:bg-earth-800/30'
  }
}

function getStatusIcon(status: ServiceStatus): React.ElementType {
  switch (status) {
    case 'operational':
      return CheckCircle2
    case 'degraded':
      return AlertTriangle
    case 'outage':
      return XCircle
    case 'maintenance':
      return Clock
    default:
      return HelpCircle
  }
}

function getStatusLabel(status: ServiceStatus): string {
  switch (status) {
    case 'operational':
      return 'Operational'
    case 'degraded':
      return 'Degraded'
    case 'outage':
      return 'Down'
    case 'maintenance':
      return 'Under maintenance'
    default:
      return 'Not checked'
  }
}

function formatDateTime(date: Date): string {
  return date.toLocaleString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function relativeTime(date: Date | null): string {
  if (!date) return 'just now'
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return `${hours} hr ago`
}

export default function StatusPage(): React.ReactElement {
  const { t } = useTranslation()
  const [services, setServices] = useState<LiveService[]>([])
  const [monitored, setMonitored] = useState(true)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [scheduledMaintenance, setScheduledMaintenance] = useState<any[]>([])
  const [recoveries, setRecoveries] = useState<any[]>([])
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchStatus = useCallback(async () => {
    // Live automated checks (drives the service indicators + uptime).
    try {
      const live = await api.get(`${API_BASE}/system-status/live`)
      if (live?.available && Array.isArray(live.services)) {
        setMonitored(true)
        setServices(live.services)
        setLastChecked(live.checked_at ? new Date(live.checked_at.replace(' ', 'T') + 'Z') : new Date())
      } else {
        setMonitored(false)
        setServices([])
      }
    } catch {
      setMonitored(false)
      setServices([])
    }

    // Staff-reported incidents (layered on top of the automated checks).
    try {
      const statusData = await api.get(`${API_BASE}/system-status`)
      const now = new Date()
      const activeIncidents: Incident[] = (statusData.active_issues || []).map((issue: any) => ({
        id: String(issue.id),
        title: issue.title,
        status: 'identified',
        severity: issue.status === 'major_outage' ? 'critical' : issue.status === 'partial_outage' ? 'major' : 'minor',
        startedAt: issue.started_at ? new Date(issue.started_at) : now,
        description: issue.patron_message || issue.description || '',
        estimatedFixTime: issue.estimated_fix_time || null,
        patronMessage: issue.patron_message || null,
      }))
      setIncidents(activeIncidents)
      setScheduledMaintenance(
        (statusData.active_issues || []).filter((i: any) => i.is_scheduled || statusData.status === 'maintenance')
      )
    } catch {
      setIncidents([])
      setScheduledMaintenance([])
    }

    try {
      const recoveryData = await api.get(`${API_BASE}/system-status/recent-recoveries?hours=168`)
      setRecoveries(recoveryData.recoveries || [])
    } catch {
      setRecoveries([])
    }
  }, [])

  const overallStatus = useMemo<ServiceStatus>(() => {
    const fromServices = services.length ? worstStatus(services.map(s => s.status)) : 'operational'
    const fromIncidents = incidents.length
      ? worstStatus(incidents.map(i => i.severity === 'minor' ? 'degraded' : 'outage'))
      : 'operational'
    return worstStatus([fromServices, fromIncidents])
  }, [services, incidents])

  const overallStatusIcon = useMemo(() => {
    const Icon = getStatusIcon(overallStatus)
    // eslint-disable-next-line react-hooks/static-components -- Icon is a stable lucide-react component reference
    return <Icon aria-hidden="true" className={`w-8 h-8 ${getStatusColor(overallStatus)}`} />
  }, [overallStatus])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch; setState runs after await
    fetchStatus()
  }, [fetchStatus])

  useEffect(() => {
    const interval = setInterval(() => { fetchStatus() }, 60000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchStatus()
    setIsRefreshing(false)
  }

  const operationalCount = services.filter(s => s.status === 'operational').length

  return (
    <PageContainer className="space-y-10 py-8">
      {/* Header */}
      <section className="text-center py-6">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-earth-800/30 flex items-center justify-center">
            <Activity aria-hidden="true" className="w-6 h-6 text-lsc-rose" />
          </div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Service Status
          </h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          We check our services automatically every minute and post the results here,
          along with any issues our staff are tracking.
        </p>
      </section>

      {/* Overall Status Banner (signature: live pulse + last-checked) */}
      <section
        className={`rounded-xl p-6 ${getStatusBgColor(overallStatus)} border ${
          overallStatus === 'operational' ? 'border-status-success-200 dark:border-status-success-800' :
          overallStatus === 'degraded' ? 'border-status-warning-200 dark:border-status-warning-800' :
          overallStatus === 'outage' ? 'border-status-danger-200 dark:border-status-danger-800' :
          'border-lsc-border dark:border-earth-700'
        }`}
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className={`relative w-14 h-14 rounded-full ${getStatusBgColor(overallStatus)} flex items-center justify-center`}>
              {overallStatusIcon}
              {monitored && overallStatus === 'operational' && (
                <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
                  <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-status-success-500" />
                </span>
              )}
            </div>
            <div>
              <h2 className={`text-xl font-bold ${getStatusColor(overallStatus)}`}>
                {overallStatus === 'operational' ? 'All systems operational' : getStatusLabel(overallStatus)}
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {monitored
                  ? <>Last checked {relativeTime(lastChecked)} · checks run every minute</>
                  : <>Automated checks are paused — showing staff-reported issues only</>}
              </p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream text-sm font-medium rounded-xl border border-lsc-border dark:border-earth-700 transition-colors disabled:opacity-50"
            aria-label={t('aria.status.refreshStatus')}
          >
            <RefreshCw aria-hidden="true" className={`w-4 h-4 ${isRefreshing ? 'motion-safe:animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </section>

      {/* Active Incidents (staff-reported) */}
      {incidents.length > 0 && (
        <section className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
            <h2 className="font-serif font-bold text-xl text-status-danger-800 dark:text-status-danger-200">
              Active incidents
            </h2>
          </div>
          <div className="space-y-4">
            {incidents.map((incident) => (
              <div key={incident.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{incident.title}</h3>
                  <span className="text-xs font-medium px-2 py-1 rounded-full bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/50 dark:text-status-danger-300">
                    {incident.severity.charAt(0).toUpperCase() + incident.severity.slice(1)}
                  </span>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{incident.description}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  Started {formatDateTime(incident.startedAt)}
                  {incident.estimatedFixTime && <> · expected back ~{formatDateTime(new Date(incident.estimatedFixTime))}</>}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Upcoming Maintenance */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Calendar aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">
            Upcoming maintenance
          </h2>
        </div>
        {scheduledMaintenance.length === 0 ? (
          <div className="flex items-center gap-3 p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-xl">
            <CheckCircle2 aria-hidden="true" className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0" />
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Nothing scheduled</p>
          </div>
        ) : (
          <div className="space-y-3">
            {scheduledMaintenance.map((m: any) => (
              <div key={m.id} className="p-4 bg-earth-50 dark:bg-earth-700/50 rounded-xl border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{m.title}</h3>
                    <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">{m.patron_message || m.description}</p>
                  </div>
                  {m.started_at && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-right flex-shrink-0">
                      {formatDateTime(new Date(m.started_at))}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Service Status (real, from the monitor) */}
      {monitored && services.length > 0 && (
        <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-6">
            <div className="flex items-center gap-2">
              <Server aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
              <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">Services</h2>
            </div>
            <span className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
              {operationalCount}/{services.length} operational
            </span>
          </div>
          <div className="space-y-4">
            {[...services].sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)).map((service) => {
              const StatusIcon = getStatusIcon(service.status)
              const ServiceIcon = SERVICE_ICONS[service.id] || Globe
              return (
                <div
                  key={service.id}
                  className="flex items-center justify-between gap-4 p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl border border-lsc-border dark:border-earth-700"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-lsc-white dark:bg-earth-700 flex items-center justify-center flex-shrink-0">
                      <ServiceIcon aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{service.name}</h3>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate">{service.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    {service.ping_ms != null && service.ping_ms > 0 && service.status === 'operational' && (
                      <span className="hidden sm:inline text-xs font-mono text-lsc-dark/50 dark:text-lsc-cream/50">
                        {service.ping_ms} ms
                      </span>
                    )}
                    <div className="flex items-center gap-2">
                      <StatusIcon aria-hidden="true" className={`w-5 h-5 ${getStatusColor(service.status)}`} />
                      <span className={`text-sm font-medium ${getStatusColor(service.status)}`}>
                        {getStatusLabel(service.status)}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Uptime (real, last 24h) */}
      {monitored && services.length > 0 && (
        <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Activity aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
            <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">Uptime, last 24 hours</h2>
          </div>
          <div className="space-y-3">
            {services.map((service) => {
              const uptime = service.uptime_24h
              const pct = uptime ?? 100
              return (
                <div key={service.id} className="flex items-center gap-3">
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 w-40 truncate">{service.name}</span>
                  <div className="flex-1 h-2 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct >= 99.5 ? 'bg-status-success-500' : pct >= 95 ? 'bg-status-warning-500' : 'bg-status-danger-500'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className={`text-xs font-mono font-medium w-16 text-right ${
                    pct >= 99.5 ? 'text-status-success-600 dark:text-status-success-400' : pct >= 95 ? 'text-status-warning-600 dark:text-status-warning-400' : 'text-status-danger-600 dark:text-status-danger-400'
                  }`}>
                    {uptime == null ? '—' : `${uptime.toFixed(2)}%`}
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Recent Incidents */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-6">
          <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">Recent incidents</h2>
          <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 ml-auto">Past 7 days</span>
        </div>
        {recoveries.length === 0 ? (
          <div className="flex items-center gap-3 p-4 bg-status-success-50 dark:bg-status-success-900/20 rounded-xl border border-status-success-200 dark:border-status-success-800">
            <CheckCircle2 aria-hidden="true" className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0" />
            <p className="text-sm text-status-success-700 dark:text-status-success-300">No incidents in the past 7 days</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recoveries.map((r: any) => (
              <div key={r.id} className="flex items-start justify-between p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl border border-lsc-border dark:border-earth-700">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0" />
                    <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate">{r.title}</h3>
                  </div>
                  {r.resolution_notes && (
                    <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 ml-6">{r.resolution_notes}</p>
                  )}
                </div>
                <div className="text-right ml-4 flex-shrink-0">
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{formatDateTime(new Date(r.resolved_at))}</p>
                  {r.duration_minutes != null && (
                    <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                      {r.duration_minutes < 60 ? `${r.duration_minutes}m` : `${Math.floor(r.duration_minutes / 60)}h ${r.duration_minutes % 60}m`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* About */}
      <section className="bg-lsc-cream dark:bg-earth-800/50 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-lsc-white dark:bg-earth-700 flex items-center justify-center flex-shrink-0">
            <Info aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </div>
          <div>
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">About this page</h2>
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-2">
              <p>
                An uptime monitor checks each service from outside the building every minute.
                The indicators above reflect those real checks. When staff are working a problem
                the monitor can't see, they post it under Active incidents.
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li><span className="text-status-success-600 dark:text-status-success-400 font-medium">Operational</span> — responding normally</li>
                <li><span className="text-status-warning-600 dark:text-status-warning-400 font-medium">Degraded</span> — reachable but slow or flaky</li>
                <li><span className="text-status-danger-600 dark:text-status-danger-400 font-medium">Down</span> — not responding</li>
                <li><span className="text-lsc-rose dark:text-lsc-rose-light font-medium">Under maintenance</span> — planned work in progress</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section className="bg-gradient-to-br from-lsc-cream to-lsc-cream dark:from-earth-800 dark:to-earth-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <HelpCircle aria-hidden="true" className="w-6 h-6 text-lsc-rose" />
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">Still having trouble?</h2>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl mx-auto mb-6">
          If everything here looks operational but something isn't working for you,
          tell us and we'll dig into it.
        </p>
        <Link
          to="/contact"
          className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
        >
          Contact us
          <ArrowRight aria-hidden="true" className="w-4 h-4" />
        </Link>
      </section>
    </PageContainer>
  )
}
