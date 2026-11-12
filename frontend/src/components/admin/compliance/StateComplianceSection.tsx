/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  MapPin,
  Building2,
  FileText,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Loader2,
  Calendar,
  Clock,
  Shield,
  Scale,
  Eye,
  ChevronRight,
  AlertTriangle,
  Bell,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { SectionShell } from '../ai-settings/SectionShell'
import { parseDate } from '@/utils/format-utils'

interface StateConfig {
  state_code: string
  state_name: string
  confidentiality_strength: string
  confidentiality_statute?: string
  last_reviewed?: string
}

interface UpcomingDeadline {
  state_code: string
  state_name: string
  state_library_name?: string
  due_date: string
  days_until_due: number
  report_template?: string
}

interface ComplianceAlert {
  id: number
  regulation_monitor_id: number
  alert_type: string
  title: string
  description: string
  priority: string
  assigned_to_id?: number
  created_at: string
}

const TABS = [
  { id: 'management', label: 'Management', icon: MapPin },
] as const

interface StateComplianceSectionProps {
  onBack: () => void
}

export function StateComplianceSection({ onBack }: StateComplianceSectionProps) {
  const { t } = useTranslation()
  const { token } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [states, setStates] = useState<StateConfig[]>([])
  const [selectedState, setSelectedState] = useState<string | null>(null)
  const [stateDetails, setStateDetails] = useState<Record<string, unknown> | null>(null)
  const [deadlines, setDeadlines] = useState<UpcomingDeadline[]>([])
  const [alerts, setAlerts] = useState<ComplianceAlert[]>([])
  const [viewMode, setViewMode] = useState<'overview' | 'states' | 'deadlines' | 'alerts'>('overview')

  const fetchStates = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await fetchApi('/state-compliance/states')
      setStates(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminStateCompliance.failedToLoadStateConfigurations'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchDeadlines = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/state-compliance/deadlines?days_ahead=90')
      setDeadlines(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminStateCompliance.failedToLoadDeadlines'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchAlerts = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/state-compliance/alerts')
      setAlerts(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminStateCompliance.failedToLoadAlerts'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const fetchStateDetails = useCallback(async (stateCode: string) => {
    if (!token) return
    try {
      const data = await fetchApi(`/state-compliance/states/${stateCode}`)
      setStateDetails(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminStateCompliance.failedToLoadStateDetails'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (token) {
      fetchStates()
      fetchDeadlines()
      fetchAlerts()
    }
  }, [token, fetchStates, fetchDeadlines, fetchAlerts])

  useEffect(() => {
    if (selectedState && token) {
      fetchStateDetails(selectedState)
    }
  }, [selectedState, token, fetchStateDetails])

  const handleResolveAlert = async (alertId: number) => {
    if (!token) return
    try {
      await fetchApi(`/state-compliance/alerts/${alertId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution_notes: 'Resolved by staff' }),
      })
      toast.success(t('toast.adminLinkHealth.alertResolved'))
      fetchAlerts()
    } catch (_error: unknown) {
      toast.error(t('admin.adminStateCompliance.failedToResolveAlert'))
    }
  }

  const getConfidentialityColor = (strength: string) => {
    switch (strength.toLowerCase()) {
      case 'strong':
        return 'text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30'
      case 'moderate':
        return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      case 'weak':
        return 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30'
      default:
        return 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30'
      case 'high':
        return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      case 'medium':
        return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
      default:
        return 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700'
    }
  }

  return (
    <SectionShell
      title="State Reporting"
      description="State library reporting requirements. Tracks deadlines and submissions so nothing slips through."
      tabs={[...TABS]}
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                State Compliance Management
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Manage state-specific compliance requirements and regulations
              </p>
            </div>
            <button
              onClick={() => {
                fetchStates()
                fetchDeadlines()
                fetchAlerts()
              }}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
            {(['overview', 'states', 'deadlines', 'alerts'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors capitalize ${
                  viewMode === mode
                    ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                {mode === 'overview' && <Building2 className="w-4 h-4" />}
                {mode === 'states' && <FileText className="w-4 h-4" />}
                {mode === 'deadlines' && <Calendar className="w-4 h-4" />}
                {mode === 'alerts' && <Bell className="w-4 h-4" />}
                {mode}
              </button>
            ))}
          </div>

          {/* Stats Cards */}
          {viewMode === 'overview' && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Building2 className="w-4 h-4" />
                  <span className="text-xs uppercase">States Configured</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {states.length}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Calendar className="w-4 h-4" />
                  <span className="text-xs uppercase">Upcoming Deadlines</span>
                </div>
                <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                  {deadlines.length}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-xs uppercase">Unresolved Alerts</span>
                </div>
                <p className={`text-2xl font-bold ${alerts.length > 0 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-status-success-600 dark:text-status-success-400'}`}>
                  {alerts.length}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-xs uppercase">Status</span>
                </div>
                <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                  {alerts.length === 0 ? 'Compliant' : 'Action Required'}
                </p>
              </div>
            </div>
          )}

          {/* States List */}
          {viewMode === 'states' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    Configured States
                  </h3>
                </div>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                ) : states.length === 0 ? (
                  <div className="p-8 text-center">
                    <Building2 className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No states configured</p>
                  </div>
                ) : (
                  <div className="divide-y divide-lsc-border dark:divide-earth-700">
                    {states.map((state) => (
                      <button
                        key={state.state_code}
                        onClick={() => setSelectedState(state.state_code)}
                        className={`w-full p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors ${
                          selectedState === state.state_code ? 'bg-lsc-cream dark:bg-lsc-brown/30' : ''
                        }`}
                      >
                        <div className="text-left">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {state.state_name} ({state.state_code})
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {state.confidentiality_statute || 'No statute specified'}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getConfidentialityColor(state.confidentiality_strength)}`}>
                            {state.confidentiality_strength}
                          </span>
                          <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* State Details */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    {selectedState ? `${selectedState} Details` : 'Select a State'}
                  </h3>
                </div>
                {!selectedState ? (
                  <div className="p-8 text-center">
                    <Eye className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminStateCompliance.selectAStateToView')}</p>
                  </div>
                ) : stateDetails ? (
                  <div className="p-4 space-y-4">
                    {!!stateDetails.confidentiality && (
                      <div>
                        <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                          <Shield className="w-4 h-4" />
                          Confidentiality
                        </h4>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                          <p>Strength: {(stateDetails.confidentiality as Record<string, string>).strength || 'N/A'}</p>
                          <p>Statute: {(stateDetails.confidentiality as Record<string, string>).statute || 'N/A'}</p>
                        </div>
                      </div>
                    )}
                    {!!stateDetails.retention && (
                      <div>
                        <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          Data Retention
                        </h4>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                          <p>Checkout Records: {(stateDetails.retention as Record<string, number>).checkout_record_retention_years || 'N/A'} years</p>
                          <p>Financial Records: {(stateDetails.retention as Record<string, number>).financial_record_retention_years || 'N/A'} years</p>
                        </div>
                      </div>
                    )}
                    {!!stateDetails.law_enforcement && (
                      <div>
                        <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                          <Scale className="w-4 h-4" />
                          Law Enforcement
                        </h4>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <p>Requires court order: {(stateDetails.law_enforcement as Record<string, boolean>).requires_court_order ? 'Yes' : 'No'}</p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Deadlines */}
          {viewMode === 'deadlines' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  Upcoming Report Deadlines
                </h3>
              </div>
              {deadlines.length === 0 ? (
                <div className="p-8 text-center">
                  <Calendar className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No upcoming deadlines</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {deadlines.map((deadline, index) => (
                    <div key={index} className="p-4 flex items-center justify-between">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {deadline.state_name} ({deadline.state_code})
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {deadline.state_library_name || 'State Library Report'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className={`font-medium ${
                          deadline.days_until_due <= 7
                            ? 'text-status-danger-600 dark:text-status-danger-400'
                            : deadline.days_until_due <= 30
                            ? 'text-status-warning-600 dark:text-status-warning-400'
                            : 'text-lsc-dark dark:text-lsc-cream'
                        }`}>
                          {deadline.days_until_due} days
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          Due: {parseDate(deadline.due_date)?.toLocaleDateString() ?? '-'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Alerts */}
          {viewMode === 'alerts' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  Unresolved Compliance Alerts
                </h3>
              </div>
              {alerts.length === 0 ? (
                <div className="p-8 text-center">
                  <CheckCircle className="w-12 h-12 mx-auto text-status-success-500 mb-4" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No unresolved alerts</p>
                </div>
              ) : (
                <div className="divide-y divide-lsc-border dark:divide-earth-700">
                  {alerts.map((alert) => (
                    <div key={alert.id} className="p-4 flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className={`w-5 h-5 mt-0.5 ${
                          alert.priority === 'critical'
                            ? 'text-status-danger-500'
                            : alert.priority === 'high'
                            ? 'text-status-warning-500'
                            : 'text-status-warning-500'
                        }`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {alert.title}
                            </p>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getPriorityColor(alert.priority)}`}>
                              {alert.priority}
                            </span>
                          </div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {alert.description}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            Created: {new Date(alert.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleResolveAlert(alert.id)}
                        className="px-3 py-1.5 text-sm text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors whitespace-nowrap"
                      >
                        Resolve
                      </button>
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
