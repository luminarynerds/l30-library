/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { SectionShell } from '../ai-settings/SectionShell'
import {
  Shield,
  Users,
  Monitor,
  Clock,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Loader2,
  Download,
  Settings,
  Activity,
  BarChart3,
  UserX,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation, getCurrentLocale } from '@/i18n'

interface CIPADashboardStats {
  active_sessions: number
  active_minor_sessions: number
  active_bypasses: number
  workstations_in_use: number
  workstations_total: number
  sessions_today: number
  minor_sessions_today: number
  policy_acceptances_today: number
  bypass_requests_today: number
  filtering_enabled_rate: number
  policy_acceptance_compliance: number
  overtime_sessions: number
  expiring_bypasses: number
}

interface FilterBypass {
  id: number
  patron_id: number
  patron_name: string
  approved_by_name: string
  reason: string
  reason_details?: string
  workstation_id: string
  status: string
  bypass_start: string
  bypass_end: string
  duration_minutes: number
  created_at: string
}

interface ComputerSession {
  id: number
  session_token: string
  patron_id?: number
  patron_name?: string
  workstation_id: string
  branch_location?: string
  status: string
  is_minor: boolean
  content_filtering_enabled: boolean
  minor_filtering_enabled: boolean
  started_at: string
  scheduled_end: string
  ended_at?: string
  duration_minutes?: number
  max_duration_minutes: number
  extension_count: number
  is_overtime: boolean
}

interface CIPASectionProps {
  onBack: () => void
}

const TABS = [{ id: 'dashboard', label: 'Dashboard', icon: Monitor }] as const

export function CIPASection({ onBack }: CIPASectionProps) {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<CIPADashboardStats | null>(null)
  const [sessions, setSessions] = useState<ComputerSession[]>([])
  const [bypasses, setBypasses] = useState<FilterBypass[]>([])
  const [viewMode, setViewMode] = useState<'dashboard' | 'sessions' | 'bypasses' | 'reports'>('dashboard')
  const [reportPeriod, setReportPeriod] = useState({ start: '', end: '' })

  const fetchDashboard = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await fetchApi('/cipa/dashboard')
      setStats(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminCIPACompliance.failedToLoadCipaDashboard'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchSessions = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/cipa/sessions/active')
      setSessions(data.sessions || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminCIPACompliance.failedToLoadActiveSessions'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchBypasses = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/cipa/bypass?active_only=true')
      setBypasses(data.bypasses || [])
    } catch (_error: unknown) {
      toast.error(t('admin.adminCIPACompliance.failedToLoadBypassRequests'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchDashboard()
      fetchSessions()
      fetchBypasses()
    }
  }, [token, isAuthenticated, fetchDashboard, fetchSessions, fetchBypasses])

  const handleRevokeBypass = async (bypassId: number) => {
    if (!token) return
    try {
      await fetchApi(`/cipa/bypass/${bypassId}/revoke`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Revoked by staff' }),
      })
      toast.success(t('toast.adminCIPACompliance.bypassRevokedSuccessfully'))
      fetchBypasses()
      fetchDashboard()
    } catch (_error: unknown) {
      toast.error(t('admin.adminCIPACompliance.failedToRevokeBypass'))
    }
  }

  const handleGenerateReport = async () => {
    if (!token || !reportPeriod.start || !reportPeriod.end) {
      toast.error(t('admin.adminCIPACompliance.pleaseSelectADateRange'))
      return
    }
    try {
      const data = await fetchApi('/cipa/report/generate', {
        method: 'POST',
        body: JSON.stringify({
          start_date: reportPeriod.start,
          end_date: reportPeriod.end,
        }),
      })
      toast.success(data.message || t('toast.adminCIPACompliance.reportGeneratedSuccessfully'))
    } catch (_error: unknown) {
      toast.error(t('admin.adminCIPACompliance.failedToGenerateReport'))
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  return (
    <SectionShell
      title="Internet Filtering (CIPA)"
      description="Internet filtering for children's safety. Required for E-Rate funding."
      tabs={[...TABS]}
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                CIPA Compliance Dashboard
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {"Children's Internet Protection Act monitoring and management"}
              </p>
            </div>
            <button
              onClick={() => {
                fetchDashboard()
                fetchSessions()
                fetchBypasses()
              }}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
            {(['dashboard', 'sessions', 'bypasses', 'reports'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors capitalize ${
                  viewMode === mode
                    ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                {mode === 'dashboard' && <BarChart3 className="w-4 h-4" />}
                {mode === 'sessions' && <Monitor className="w-4 h-4" />}
                {mode === 'bypasses' && <Shield className="w-4 h-4" />}
                {mode === 'reports' && <Download className="w-4 h-4" />}
                {mode}
              </button>
            ))}
          </div>

          {viewMode === 'dashboard' && (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : stats ? (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Monitor className="w-4 h-4" />
                      <span className="text-xs font-semibold">Active sessions</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.active_sessions}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {stats.workstations_in_use} / {stats.workstations_total} workstations
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Users className="w-4 h-4" />
                      <span className="text-xs font-semibold">Minor sessions</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                      {stats.active_minor_sessions}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {stats.minor_sessions_today} today
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Shield className="w-4 h-4" />
                      <span className="text-xs font-semibold">Active bypasses</span>
                    </div>
                    <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                      {stats.active_bypasses}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {stats.expiring_bypasses} expiring soon
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-xs font-semibold">Filtering rate</span>
                    </div>
                    <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                      {(stats.filtering_enabled_rate * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Policy compliance: {(stats.policy_acceptance_compliance * 100).toFixed(1)}%
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Activity className="w-4 h-4" />
                      <span className="text-xs font-semibold">Sessions today</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.sessions_today}
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Clock className="w-4 h-4" />
                      <span className="text-xs font-semibold">Policy acceptances</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.policy_acceptances_today}
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <Settings className="w-4 h-4" />
                      <span className="text-xs font-semibold">Bypass requests</span>
                    </div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {stats.bypass_requests_today}
                    </p>
                  </div>

                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="text-xs font-semibold">Overtime sessions</span>
                    </div>
                    <p className={`text-2xl font-bold ${stats.overtime_sessions > 0 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                      {stats.overtime_sessions}
                    </p>
                  </div>
                </div>
              ) : null}
            </>
          )}

          {viewMode === 'sessions' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  Active Computer Sessions
                </h3>
              </div>
              {sessions.length === 0 ? (
                <div className="p-8 text-center">
                  <Monitor className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No active sessions</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {sessions.map((session) => (
                    <div key={session.id} className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${
                          session.is_minor
                            ? 'bg-earth-100 dark:bg-earth-800/30'
                            : 'bg-earth-100 dark:bg-earth-700'
                        }`}>
                          {session.is_minor ? (
                            <UserX className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                          ) : (
                            <Monitor className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {session.workstation_id}
                            </span>
                            {session.is_minor && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                                Minor
                              </span>
                            )}
                            {session.is_overtime && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400">
                                Overtime
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {session.patron_name || 'Guest'} - Started {formatDate(session.started_at)}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            Filtering: {session.content_filtering_enabled ? 'Enabled' : 'Disabled'}
                            {session.minor_filtering_enabled && ' (Enhanced for minors)'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          Ends: {formatDate(session.scheduled_end)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {viewMode === 'bypasses' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  Active Filter Bypasses
                </h3>
              </div>
              {bypasses.length === 0 ? (
                <div className="p-8 text-center">
                  <Shield className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No active bypasses</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {bypasses.map((bypass) => (
                    <div key={bypass.id} className="p-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {bypass.patron_name}
                          </span>
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400">
                            {bypass.reason}
                          </span>
                        </div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          Workstation: {bypass.workstation_id} - Approved by {bypass.approved_by_name}
                        </p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          {bypass.duration_minutes} min - Ends {formatDate(bypass.bypass_end)}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRevokeBypass(bypass.id)}
                        className="px-3 py-1.5 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
                      >
                        Revoke
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {viewMode === 'reports' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                Generate CIPA Compliance Report
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Generate a report for E-rate documentation and CIPA compliance certification.
              </p>
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={reportPeriod.start}
                    onChange={(e) => setReportPeriod({ ...reportPeriod, start: e.target.value })}
                    className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={reportPeriod.end}
                    onChange={(e) => setReportPeriod({ ...reportPeriod, end: e.target.value })}
                    className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <button
                  onClick={handleGenerateReport}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Generate Report
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </SectionShell>
  )
}
